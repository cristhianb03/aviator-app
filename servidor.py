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

FILE_DB = 'database_qrp_v605.csv'
csv_lock = threading.Lock()

# Memoria Maestra V605 con Métricas de Protección
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO SENTINEL",
    "estabilidad_contexto": "0%",
    "nivel_riesgo": "ANALIZANDO",
    "tp_s": "--",
    "fase": "MONITOREO",
    "rondas_evitadas": 0,       # Mejora 2: Contador de protección
    "exposicion_hoy": "0%",     # Mejora 2: Métrica de selectividad
    "rondas_totales": 0,
    "contador_fallos": 0,
    "bloqueo_rondas": 0,
    "historial_visual": []
}

def motor_sentinel_qrp(hist_data):
    if len(hist_data) < 100: return None
    try:
        df = pd.DataFrame(hist_data, columns=['valor', 'jugadores'])
        df['target_exit'] = (df['valor'].shift(-1) >= 1.50).astype(int)
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

    # Actualización de contadores globales
    memoria["ultimo_valor"] = v
    memoria["rondas_totales"] += 1
    memoria["historial_visual.insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    # Gestión de Bloqueos por fallo
    if memoria["bloqueo_rondas"] > 0: memoria["bloqueo_rondas"] -= 1
    if memoria["tp_s"] != "--":
        if v < 1.50:
            memoria["contador_fallos"] += 1
            if memoria["contador_fallos"] >= 2: memoria["bloqueo_rondas"] = 3
        else: memoria["contador_fallos"] = 0 
    
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
        
        memoria["estabilidad_contexto"] = f"{round(ind_est)}%"

        # --- LÓGICA DE ESTADOS V605 ---

        # 1. ESTADO: PAUSA/BLOQUEO
        if memoria["bloqueo_rondas"] > 0:
            memoria["sugerencia"] = "🛑 PAUSA DE SEGURIDAD"
            memoria["nivel_riesgo"] = "CRÍTICO"
            memoria["tp_s"] = "--"; memoria["fase"] = "DRAWDOWN CONTROL"
            memoria["rondas_evitadas"] += 1

        # 2. ESTADO: TÓXICO
        elif ind_est < 45 or std_act > 5.0:
            memoria["sugerencia"] = "❌ CONTEXTO TÓXICO"
            memoria["nivel_riesgo"] = "EXTREMO"
            memoria["tp_s"] = "--"; memoria["fase"] = "EVITAR EXPOSICIÓN"
            memoria["rondas_evitadas"] += 1

        # 3. ESTADO: FAVORABLE (VERDE) + MEJORA 1: ENFRIAMIENTO
        elif ind_est > 62 and ventaja_ponderada > 1.0 and prec_val > baseline:
            # Si el anterior fue éxito o estamos en racha verde, pero la estabilidad no es absoluta, enfriamos
            if memoria["fase"] == "VENTAJA VALIDADA" and ind_est < 68:
                memoria["sugerencia"] = "⚠️ VENTANA TÁCTICA CORTA"
                memoria["nivel_riesgo"] = "MEDIO (ENFRIAMIENTO)"
                memoria["tp_s"] = "1.25x"
                memoria["fase"] = "CONTROL DE EUFORIA"
            else:
                memoria["sugerencia"] = "✅ CONTEXTO FAVORABLE"
                memoria["nivel_riesgo"] = "BAJO"
                memoria["tp_s"] = "1.50x"
                memoria["fase"] = "VENTAJA VALIDADA"

        # 4. ESTADO: ZONA TÁCTICA
        elif 50 <= ind_est <= 62:
            memoria["sugerencia"] = "⚠️ VENTANA TÁCTICA CORTA"
            memoria["nivel_riesgo"] = "MODERADO"
            memoria["tp_s"] = "1.20x - 1.30x"
            memoria["fase"] = "DISCRECIONAL"

        # 5. ESTADO: NEUTRAL
        else:
            memoria["sugerencia"] = "⏳ ESPERANDO ESTABILIDAD"
            memoria["nivel_riesgo"] = "ELEVADO"
            memoria["tp_s"] = "--"; memoria["fase"] = "MONITOREO"
            memoria["rondas_evitadas"] += 1

        # MEJORA 2: Cálculo de Exposición Recomendada
        # Cuanto más evitamos, menor es la exposición del día
        r_totales = max(1, memoria["rondas_totales"])
        calc_expo = ((r_totales - memoria["rondas_evitadas"]) / r_totales) * 100
        memoria["exposicion_hoy"] = f"{round(calc_expo)}%"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
