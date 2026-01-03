from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import os
import threading
import statistics

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float
    jugadores: int = 0

FILE_DB = 'database_flow_v75.csv'
csv_lock = threading.Lock()

# MEMORIA MAESTRA - NOMBRES EXACTOS PARA EL HTML
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO",
    "confianza": "0%",       # Sincronizado
    "tp_s": "--",            # Sincronizado
    "tp_e": "--",            # Sincronizado
    "fase": "MONITOREO",
    "trades_hoy": 0,
    "wins_hoy": 0,
    "bloqueo_rondas": 0,
    "historial_visual": []
}

def motor_ia_flow(hist):
    if len(hist) < 80: return None
    try:
        df = pd.DataFrame(hist[::-1], columns=['valor'])
        df['target'] = (df['valor'].shift(-1) >= 1.30).astype(int)
        df['v1'] = df['valor'].shift(1)
        df['v2'] = df['valor'].shift(2)
        df['std'] = df['valor'].rolling(5).std()
        df = df.dropna()
        X = df[['v1', 'v2', 'std']]
        model = RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42).fit(X, df['target'])
        std_act = statistics.stdev(hist[:5])
        prob = model.predict_proba(np.array([[hist[0], hist[1], std_act]]))[0][1]
        return round(prob * 100, 2), round(std_act, 2)
    except: return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v = res.valor
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    if memoria["tp_s"] != "--":
        memoria["trades_hoy"] += 1
        if v >= 1.20: memoria["wins_hoy"] += 1
        else: memoria["bloqueo_rondas"] = 4 

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
        prob, std = res_ia
        memoria["confianza"] = f"{round(prob)}%" # Actualizar siempre la confianza

        if memoria["bloqueo_rondas"] > 0:
            memoria["sugerencia"] = f"🛑 PAUSA ({memoria['bloqueo_rondas']} R.)"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
        elif prob >= 52:
            memoria["sugerencia"] = "✅ CONTEXTO ESTABLE"
            memoria["tp_s"] = "1.20x"
            if prob >= 55 and std < 2.8:
                memoria["tp_e"] = "1.50x"
                memoria["fase"] = "OPTIMIZACIÓN FLUJO"
            else:
                memoria["tp_e"] = "--"
                memoria["fase"] = "ZONA SEGURA"
        else:
            memoria["sugerencia"] = "⏳ ESCANEANDO"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
            memoria["fase"] = "ANÁLISIS"
    else:
        memoria["sugerencia"] = f"🧠 ENTRENANDO ({len(total_vals)}/80)"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
