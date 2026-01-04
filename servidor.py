
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score
import os
import threading
import statistics
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float
    jugadores: int = 0

FILE_DB = 'database_v80_tactical.csv'
csv_lock = threading.Lock()

# MEMORIA MAESTRA V80.1 - NOMBRES SINCRONIZADOS CON EL INDEX
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO",
    "fase": "MONITOREO",
    "tp_s": "--", 
    "tp_e": "--", 
    "rondas_sin_entrar": 0,
    "bloqueo_rondas": 0,
    "trades_hoy": 0,
    "wins_hoy": 0,
    "estabilidad_contexto": "0%",
    "historial_visual": []
}

def motor_ia_adaptive(hist):
    if len(hist) < 80: return None
    try:
        df = pd.DataFrame(hist, columns=['valor'])
        df['target'] = (df['valor'].shift(-1) >= 1.25).astype(int)
        df['v1'] = df['valor'].shift(1)
        df['v2'] = df['valor'].shift(2)
        df['std'] = df['valor'].rolling(5).std()
        df = df.dropna()
        
        X = df[['v1', 'v2', 'std']]
        model = RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42).fit(X, df['target'])
        
        std_act = statistics.stdev(hist[-5:])
        prob = model.predict_proba(np.array([[hist[-1], hist[-2], std_act]]))[0][1]
        
        baseline = max(48, df['target'].mean() * 100)
        return round(prob * 100, 2), round(std_act, 2), round(baseline, 2)
    except: return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v = res.valor
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    if memoria["bloqueo_rondas"] > 0:
        memoria["bloqueo_rondas"] -= 1

    hubo_senal_previa = memoria["tp_s"] != "--" or memoria["tp_e"] != "--"
    if hubo_senal_previa:
        memoria["trades_hoy"] += 1
        if v >= 1.20: 
            memoria["wins_hoy"] += 1
            memoria["rondas_sin_entrar"] = 10 
        else:
            memoria["bloqueo_rondas"] = 4 
            memoria["rondas_sin_entrar"] = 0

    memoria["ultimo_valor"] = v
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    with csv_lock:
        with open(FILE_DB, 'a') as f: f.write(f"{v},{res.jugadores}\n")

    try:
        db = pd.read_csv(FILE_DB, names=['valor', 'jugadores'])
        total_vals = db.tail(250)['valor'].tolist()
    except: total_vals = []

    res_ia = motor_ia_adaptive(total_vals)
    
    if res_ia:
        prob, std, baseline = res_ia
        memoria["estabilidad_contexto"] = f"{round(prob)}%"
        bajos_recientes = len([x for x in total_vals[-5:] if x < 1.40])
        
        # --- LÓGICA DE ESTADOS (MANTIENE LA VERSIÓN 80) ---
        if memoria["bloqueo_rondas"] > 0:
            memoria["sugerencia"] = f"🛑 PAUSA ({memoria['bloqueo_rondas']} R.)"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
            memoria["fase"] = "ENFRIAMIENTO"
        elif memoria["rondas_sin_entrar"] < 2:
            memoria["sugerencia"] = "⏳ REARMANDO CONTEXTO"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
            memoria["fase"] = "ESTABILIZANDO"
            memoria["rondas_sin_entrar"] += 1
        elif prob >= 52 and std < 3.2:
            memoria["sugerencia"] = "✅ CONTEXTO ESTABLE"
            memoria["tp_s"] = "1.20x"
            memoria["tp_e"] = "1.50x" if (std < 2.8 and prob >= 55) else "--"
            memoria["fase"] = "ZONA VALIDADA"
            memoria["rondas_sin_entrar"] = 5
        elif bajos_recientes >= 4 and prob >= (baseline - 5):
            memoria["sugerencia"] = "🟡 PREPARACIÓN ACTIVA"
            memoria["tp_s"] = "1.20x"
            memoria["tp_e"] = "--"
            memoria["fase"] = "RECUPERACIÓN"
            memoria["rondas_sin_entrar"] = 5
        elif memoria["rondas_sin_entrar"] >= 6 and prob >= 50:
            memoria["sugerencia"] = "🟢 ENTRADA TÁCTICA"
            memoria["tp_s"] = "1.20x"
            memoria["tp_e"] = "--"
            memoria["fase"] = "PERSISTENCIA"
            memoria["rondas_sin_entrar"] = 3 
        else:
            memoria["sugerencia"] = "📡 ESCANEANDO"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
            memoria["fase"] = "MONITOREO"
            memoria["rondas_sin_entrar"] += 1
            
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
