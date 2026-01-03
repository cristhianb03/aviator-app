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

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float
    jugadores: int = 0

FILE_DB = 'database_v75_master.csv'
csv_lock = threading.Lock()

# MEMORIA MAESTRA SINCRONIZADA
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO",
    "confianza": "0%",
    "tp_s": "--", # Base 1.20x
    "tp_e": "--", # Optimización 1.50x
    "fase": "INICIO",
    "wins_hoy": 0,
    "trades_hoy": 0,
    "bloqueo_rondas": 0,
    "historial_visual": []
}

def motor_ia_flow(hist):
    if len(hist) < 80: return None
    try:
        df = pd.DataFrame(hist[::-1], columns=['valor'])
        # Target estratégico 1.30x para validar ambas salidas
        df['target'] = (df['valor'].shift(-1) >= 1.30).astype(int)
        df['v1'] = df['valor'].shift(1)
        df['v2'] = df['valor'].shift(2)
        df['std'] = df['valor'].rolling(5).std()
        df = df.dropna()
        
        X = df[['v1', 'v2', 'std']]
        model = RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42).fit(X, df['target'])
        
        std_act = statistics.stdev(hist[:5])
        prob = model.predict_proba(np.array([[hist[0], hist[1], std_act]]))[0][1]
        
        baseline = df['target'].mean() * 100
        return round(prob * 100, 2), round(std_act, 2), round(baseline, 2)
    except: return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v = res.valor
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    # --- 📊 AUDITORÍA Y CASTIGO CORTO ---
    if memoria["tp_s"] != "--":
        memoria["trades_hoy"] += 1
        if v >= 1.20:
            memoria["wins_hoy"] += 1
        else:
            memoria["bloqueo_rondas"] = 4 # BLOQUEO RELÁMPAGO DE 4 RONDAS

    memoria["ultimo_valor"] = v
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    if memoria["bloqueo_rondas"] > 0: memoria["bloqueo_rondas"] -= 1
    
    with csv_lock:
        with open(FILE_DB, 'a') as f: f.write(f"{v},{res.jugadores}\n")

    try:
        db = pd.read_csv(FILE_DB, names=['valor', 'jugadores'])
        total_vals = db.tail(250)['valor'].tolist()
    except: total_vals = []

    res_ia = motor_ia_flow(total_vals)
    
    if res_ia:
        prob, std, baseline = res_ia
        memoria["confianza"] = f"{round(prob)}%"

        # --- 🎯 LÓGICA DE SEÑALES (RECOMENDACIÓN FINAL) ---
        
        if memoria["bloqueo_rondas"] > 0:
            memoria["sugerencia"] = f"🛑 PAUSA ({memoria['bloqueo_rondas']} R.)"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
            memoria["fase"] = "PROTECCIÓN"
        
        # 🟢 CAPA BASE (1.20x): Probabilidad >= 52%
        elif prob >= 52:
            memoria["sugerencia"] = "✅ CONTEXTO RENTABLE"
            memoria["tp_s"] = "1.20x"
            
            # 🔴 CAPA OPTIMIZACIÓN (1.50x): Probabilidad >= 55% + Estabilidad
            if prob >= 55 and std < 2.8:
                memoria["tp_e"] = "1.50x"
                memoria["fase"] = "DIFERENCIAL ACTIVO"
            else:
                memoria["tp_e"] = "--"
                memoria["fase"] = "FLUJO SEGURO"
        else:
            memoria["sugerencia"] = "⏳ ESCANEANDO"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
            memoria["fase"] = "ANÁLISIS"
            
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
