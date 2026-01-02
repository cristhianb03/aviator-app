from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score
import os
import threading
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float
    jugadores: int = 0

FILE_DB = 'database_qrp_v801.csv'
csv_lock = threading.Lock()

# MEMORIA MAESTRA V801 - NOMBRES SINCRONIZADOS
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO PROTOCOLO",
    "estabilidad_contexto": "0%",
    "nivel_riesgo": "ANALIZANDO",
    "tp_s": "--",
    "fase": "MONITOREO",
    "rondas_evitadas": 0,
    "rondas_totales": 0,
    "selectivity": "MEDIA", # Sincronizado con JS
    "historial_visual": []
}

def motor_except_qrp(hist_data):
    if len(hist_data) < 100: return None
    try:
        df = pd.DataFrame(hist_data, columns=['valor', 'jugadores'])
        df['target_exit'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['std_5'] = df['valor'].rolling(5).std()
        df['ema_5'] = df['valor'].ewm(span=5).mean()
        df = df.dropna()
        
        features = ['valor', 'jugadores', 'std_5', 'ema_5']
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

    memoria["ultimo_valor"] = v
    memoria["rondas_totales"] += 1
    
    # CORREGIDO: Sintaxis de inserción
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    with csv_lock:
        with open(FILE_DB, 'a') as f: f.write(f"{v},{j}\n")

    try:
        db = pd.read_csv(FILE_DB, names=['valor', 'jugadores'])
        total_hist = db.tail(350).values.tolist()
    except: total_hist = []

    res_ia = motor_except_qrp(total_hist)
    
    if res_ia:
        ind_est, prec_val, baseline, std_act = res_ia
        ventaja_ponderada = (prec_val - baseline) * (ind_est / 100)
        memoria["estabilidad_contexto"] = f"{round(ind_est)}%"

        # --- LÓGICA DE ESTADOS V801 ---
        if ind_est >= 72 and ventaja_ponderada > 2.5 and std_act < 1.2:
            memoria["sugerencia"] = "💎 CONTEXTO EXCEPCIONAL"
            memoria["tp_s"] = "1.80x - 2.00x"
            memoria["nivel_riesgo"] = "MÍNIMO"
            memoria["fase"] = "ALTA SELECTIVIDAD"
            memoria["selectivity"] = "EXTREMA"
        elif ind_est > 62 and ventaja_ponderada > 1.2:
            memoria["sugerencia"] = "✅ CONTEXTO FAVORABLE"
            memoria["tp_s"] = "1.45x - 1.55x"
            memoria["nivel_riesgo"] = "BAJO"
            memoria["fase"] = "VENTAJA VALIDADA"
            memoria["selectivity"] = "ALTA"
        elif 55 <= ind_est <= 62:
            memoria["sugerencia"] = "⚠️ VENTANA TÁCTICA"
            memoria["tp_s"] = "1.20x - 1.30x"
            memoria["nivel_riesgo"] = "MODERADO"
            memoria["fase"] = "ZONA DISCRECIONAL"
            memoria["selectivity"] = "MEDIA"
        else:
            memoria["sugerencia"] = "🛑 ABSTENCIÓN TÉCNICA"
            memoria["tp_s"] = "--"
            memoria["nivel_riesgo"] = "ELEVADO"
            memoria["fase"] = "ALTA VARIANZA"
            memoria["selectivity"] = "BAJA"
            memoria["rondas_evitadas"] += 1
    else:
        memoria["sugerencia"] = f"🧠 CALIBRANDO ({len(total_hist)}/100)"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
