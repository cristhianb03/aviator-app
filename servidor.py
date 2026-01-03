from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score
import os
import threading

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float
    jugadores: int = 0

FILE_DB = 'database_qrp_audit.csv'
csv_lock = threading.Lock()

# MEMORIA MAESTRA UNIFICADA - NO CAMBIAR NOMBRES
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO PROTOCOLO",
    "estabilidad_contexto": "0%",
    "ventaja_azar": "+0.0%",
    "riesgo_ponderado": "ANALIZANDO",
    "tp_conservador": "--",
    "tp_agresivo": "--",
    "fase": "MONITOREO",
    "rondas_evitadas": 0,
    "exposicion_hoy": "0%",
    "rondas_totales": 0,
    "wins_conservador": 0,
    "trades_conservador": 0,
    "wins_agresivo": 0,
    "trades_agresivo": 0,
    "contador_fallos": 0,
    "bloqueo_rondas": 0,
    "historial_visual": []
}

def motor_sentinel_qrp(hist_data):
    if len(hist_data) < 100: return None
    try:
        df = pd.DataFrame(hist_data, columns=['valor', 'jugadores'])
        df['target_exit'] = (df['valor'].shift(-1) >= 1.30).astype(int)
        df['std_5'] = df['valor'].rolling(5).std()
        df['ema_5'] = df['valor'].ewm(span=5).mean()
        df['vol_change'] = df['jugadores'].diff()
        df = df.dropna()
        features = ['valor', 'jugadores', 'std_5', 'ema_5', 'vol_change']
        split = int(len(df) * 0.75)
        train, test = df.iloc[:split], df.iloc[split:]
        model = RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42)
        model.fit(train[features], train['target_exit'])
        preds = model.predict(test[features])
        prec_val = precision_score(test['target_exit'], preds, zero_division=0) * 100
        baseline = test['target_exit'].mean() * 100
        current_x = df.tail(1)[features]
        ind_est = model.predict_proba(current_x)[0][1] * 100
        return round(ind_est, 2), round(prec_val, 2), round(baseline, 2), df['std_5'].iloc[-1]
    except: return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v, j = res.valor, res.jugadores
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    # Auditoría de resultados anteriores
    if memoria["tp_conservador"] != "--":
        memoria["trades_conservador"] += 1
        if v >= 1.20: memoria["wins_conservador"] += 1
    if memoria["tp_agresivo"] != "--":
        memoria["trades_agresivo"] += 1
        if v >= 1.70: memoria["wins_agresivo"] += 1

    memoria["ultimo_valor"] = v
    memoria["rondas_totales"] += 1
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    if memoria["bloqueo_rondas"] > 0: memoria["bloqueo_rondas"] -= 1
    
    with csv_lock:
        with open(FILE_DB, 'a') as f: f.write(f"{v},{j}\n")

    try:
        db = pd.read_csv(FILE_DB, names=['valor', 'jugadores'])
        total_hist = db.tail(350).values.tolist()
    except: total_hist = []

    res_ia = motor_sentinel_qrp(total_hist)
    
    if res_ia:
        ind_est, prec_val, baseline, std_act = res_ia
        ventaja_ponderada = (prec_val - baseline) * (ind_est / 100)
        ventaja_real = round(prec_val - baseline, 2)
        memoria["estabilidad_contexto"] = f"{round(ind_est)}%"
        memoria["ventaja_azar"] = f"+{ventaja_real}%" if ventaja_real > 0 else f"{ventaja_real}%"

        if memoria["bloqueo_rondas"] > 0:
            memoria["sugerencia"] = "🛑 PAUSA DE SEGURIDAD"
            memoria["tp_conservador"] = "--"; memoria["tp_agresivo"] = "--"
            memoria["rondas_evitadas"] += 1
        elif ind_est < 45 or std_act > 5.0:
            memoria["sugerencia"] = "🛑 ABSTENCIÓN TÉCNICA"
            memoria["tp_conservador"] = "--"; memoria["tp_agresivo"] = "--"
            memoria["rondas_evitadas"] += 1
        elif ind_est > 62 and ventaja_ponderada > 1.0:
            memoria["sugerencia"] = "✅ CONTEXTO FAVORABLE"
            memoria["tp_conservador"] = "1.35x"
            memoria["tp_agresivo"] = "1.80x"
        elif 50 <= ind_est <= 62:
            memoria["sugerencia"] = "⚠️ VENTANA TÁCTICA"
            memoria["tp_conservador"] = "1.20x"
            memoria["tp_agresivo"] = "--"
        else:
            memoria["sugerencia"] = "⏳ MONITOREO DE VARIANZA"
            memoria["tp_conservador"] = "--"; memoria["tp_agresivo"] = "--"
            memoria["rondas_evitadas"] += 1

        memoria["exposicion_hoy"] = f"{round(((memoria['rondas_totales'] - memoria['rondas_evitadas']) / memoria['rondas_totales']) * 100)}%"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
