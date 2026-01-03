from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import os
import threading
import statistics
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float
    jugadores: int = 0

FILE_DB = 'database_sentinel_v76.csv'
csv_lock = threading.Lock()

# Memoria Maestra V76
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO",
    "fase": "MONITOREO",
    "tp_seguro": "--",
    "tp_crecimiento": "--",
    "trades_hoy": 0,
    "max_trades": 30,
    "wins_hoy": 0,
    "fecha_actual": datetime.now().strftime("%Y-%m-%d"),
    "historial_visual": []
}

def motor_ia_sentinel(hist):
    if len(hist) < 80: return None
    try:
        df = pd.DataFrame(hist[::-1], columns=['valor'])
        df['target'] = (df['valor'].shift(-1) >= 1.25).astype(int)
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

    # --- RESET DIARIO ---
    hoy = datetime.now().strftime("%Y-%m-%d")
    if hoy != memoria["fecha_actual"]:
        memoria.update({"trades_hoy": 0, "wins_hoy": 0, "fecha_actual": hoy})

    # --- AUDITORÍA DE ACIERTOS ---
    if memoria["tp_seguro"] != "--":
        memoria["trades_hoy"] += 1
        # Se cuenta como éxito si supera el mínimo conservador (1.20x)
        if v >= 1.20: memoria["wins_hoy"] += 1

    memoria["ultimo_valor"] = v
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    with csv_lock:
        with open(FILE_DB, 'a') as f: f.write(f"{v},{res.jugadores}\n")

    try:
        db = pd.read_csv(FILE_DB, names=['valor', 'jugadores'])
        total_vals = db.tail(250)['valor'].tolist()
    except: total_hist = []

    res_ia = motor_ia_sentinel(total_vals)
    
    if res_ia:
        prob, std = res_ia
        if memoria["trades_hoy"] >= memoria["max_trades"]:
            memoria["sugerencia"] = "🛑 SESIÓN FINALIZADA"
            memoria["tp_seguro"] = "--"; memoria["tp_crecimiento"] = "--"
        elif (prob >= 53 and std < 3.2):
            memoria["sugerencia"] = "✅ CONTEXTO ESTABLE"
            memoria["tp_seguro"] = "1.20x"
            memoria["tp_crecimiento"] = "1.60x" if (std < 2.2 and prob >= 56) else "1.50x"
            memoria["fase"] = "OPTIMIZACIÓN ACTIVA"
        else:
            memoria["sugerencia"] = "📡 ESCANEANDO RIESGO"
            memoria["tp_seguro"] = "--"; memoria["tp_crecimiento"] = "--"
            memoria["fase"] = "MONITOREO"
            
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
