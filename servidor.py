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

FILE_DB = 'database_qrp_v800.csv'
csv_lock = threading.Lock()

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO PROTOCOLO",
    "estabilidad_contexto": "0%",
    "nivel_riesgo": "ANALIZANDO",
    "tp_s": "--",
    "fase": "MONITOREO",
    "rondas_evitadas": 0,
    "rondas_totales": 0,
    "contador_fallos": 0,
    "bloqueo_rondas": 0,
    "selectividad": "MEDIA",
    "historial_visual": []
}

def motor_except_qrp(hist_data):
    if len(hist_data) < 100: return None
    try:
        df = pd.DataFrame(hist_data, columns=['valor', 'jugadores'])
        # Target base de entrenamiento: 1.50x
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
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    # Gestión de Bloqueos
    if memoria["bloqueo_rondas"] > 0: memoria["bloqueo_rondas"] -= 1
    if memoria["tp_s"] != "--":
        if v < float(memoria["tp_s"].split('x')[0].split('-')[0]):
            memoria["contador_fallos"] += 1
            if memoria["contador_fallos"] >= 2: memoria["bloqueo_rondas"] = 3
        else: memoria["contador_fallos"] = 0 
    
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

        # --- LÓGICA DE TP ESCALONADO POR CONTEXTO ---

        # 1. BLOQUEO / PAUSA
        if memoria["bloqueo_rondas"] > 0:
            memoria["sugerencia"] = "🛑 PAUSA DE SEGURIDAD"
            memoria["tp_s"] = "--"; memoria["nivel_riesgo"] = "MÁXIMO"; memoria["rondas_evitadas"] += 1

        # 2. CONTEXTO EXCEPCIONAL (EL "UNICORNIO")
        elif ind_est >= 72 and ventaja_ponderada > 2.5 and std_act < 1.2:
            memoria["sugerencia"] = "💎 CONTEXTO EXCEPCIONAL"
            memoria["tp_s"] = "1.80x - 2.00x"
            memoria["nivel_riesgo"] = "MÍNIMO (ESTADÍSTICO)"
            memoria["fase"] = "ALTA SELECTIVIDAD"; memoria["selectividad"] = "EXTREMA"

        # 3. CONTEXTO FAVORABLE
        elif ind_est > 62 and ventaja_ponderada > 1.2:
            # Enfriamiento post-éxito
            if "VENTAJA VALIDADA" in memoria["fase"] and ind_est < 68:
                memoria["sugerencia"] = "⚠️ VENTANA TÁCTICA"
                memoria["tp_s"] = "1.25x - 1.35x"
                memoria["fase"] = "CONTROL DE EUFORIA"
            else:
                memoria["sugerencia"] = "✅ CONTEXTO FAVORABLE"
                memoria["tp_s"] = "1.45x - 1.55x"
                memoria["nivel_riesgo"] = "BAJO"
                memoria["fase"] = "VENTAJA VALIDADA"; memoria["selectividad"] = "ALTA"

        # 4. VENTANA TÁCTICA
        elif 55 <= ind_est <= 62 and ventaja_ponderada > 0.2:
            memoria["sugerencia"] = "⚠️ VENTANA TÁCTICA"
            memoria["tp_s"] = "1.20x - 1.30x"
            memoria["nivel_riesgo"] = "MODERADO"
            memoria["fase"] = "ZONA DISCRECIONAL"; memoria["selectividad"] = "MEDIA"

        # 5. ABSTENCIÓN
        else:
            memoria["sugerencia"] = "⏳ ESPERANDO ESTABILIDAD"
            memoria["tp_s"] = "--"; memoria["nivel_riesgo"] = "ELEVADO"
            memoria["fase"] = "MONITOREO"; memoria["rondas_evitadas"] += 1

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
