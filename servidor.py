from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import statistics
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

FILE_DB = 'database_v72.csv'

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO",
    "confianza": "0%",
    "tp_conservador": "--",
    "tp_agresivo": "--",
    "fase": "MONITOREO",
    "contador_agresivo": 0,
    # 📊 MÉTRICAS DE RENDIMIENTO (NUEVO)
    "trades_conservador": 0,
    "wins_conservador": 0,
    "trades_agresivo": 0,
    "wins_agresivo": 0,
    "historial_visual": []
}

def motor_ia_v72(hist):
    if len(hist) < 60: return None
    try:
        df = pd.DataFrame(hist[::-1], columns=['valor'])
        df['target'] = (df['valor'].shift(-1) >= 1.25).astype(int) # Alineado a 1.25x
        df['v1'] = df['valor'].shift(1)
        df['v2'] = df['valor'].shift(2)
        df['std'] = df['valor'].rolling(5).std()
        df = df.dropna()
        
        X = df[['v1', 'v2', 'std']]
        model = RandomForestClassifier(n_estimators=80, max_depth=4, random_state=42).fit(X, df['target'])
        
        std_act = statistics.stdev(hist[:5])
        prob = model.predict_proba(np.array([[hist[0], hist[1], std_act]]))[0][1]
        return round(prob * 100, 2), std_act
    except: return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v = res.valor
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    # --- 📊 AUDITORÍA DE RESULTADOS (NUEVO) ---
    # Verificamos si la sugerencia de la ronda anterior fue exitosa
    if memoria["tp_conservador"] != "--":
        memoria["trades_conservador"] += 1
        if v >= 1.20: memoria["wins_conservador"] += 1

    if memoria["tp_agresivo"] != "--":
        memoria["trades_agresivo"] += 1
        if v >= 1.70: memoria["wins_agresivo"] += 1

    # Guardar estado previo de la agresiva para lógica de castigo
    agresivo_activo_anterior = memoria["tp_agresivo"] != "--"

    # Actualizar estado básico
    memoria["ultimo_valor"] = v
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 20: memoria["historial_visual"].pop()
    if memoria["contador_agresivo"] > 0: memoria["contador_agresivo"] -= 1
    
    with open(FILE_DB, 'a') as f: f.write(f"{v}\n")
    try:
        with open(FILE_DB, 'r') as f:
            total_hist = [float(l.strip()) for l in f.readlines() if l.strip()][-150:]
    except: total_hist = []

    res_ia = motor_ia_v72(total_hist)
    
    if res_ia:
        prob, std_act = res_ia
        memoria["confianza"] = f"{round(prob)}%"
        
        # 1️⃣ CAPA CONSERVADORA: Ahora con filtro de Volatilidad (std < 2.5)
        if prob >= 56 and std_act < 2.5:
            memoria["tp_conservador"] = "1.20x"
            memoria["sugerencia"] = "🛡️ RIESGO CONTROLADO"
            memoria["fase"] = "ZONA ESTABLE"
        else:
            memoria["tp_conservador"] = "--"
            memoria["sugerencia"] = "⏳ ABSTENCIÓN"
            memoria["fase"] = "VARIANZA ALTA" if std_act >= 2.5 else "SIN EDGE"

        # 2️⃣ CAPA AGRESIVA: Ventana de 5 para detectar micro-secuencia
        azules = len([x for x in total_hist[:5] if x < 1.80])
        if (3 <= azules <= 5) and (std_act < 2.0) and (55 <= prob <= 65) and (memoria["contador_agresivo"] == 0):
            memoria["tp_agresivo"] = "1.70x"
            memoria["sugerencia"] = "🚀 VENTANA TÁCTICA"
            memoria["contador_agresivo"] = 12 
        else:
            memoria["tp_agresivo"] = "--"

        # 3️⃣ FILTRO DE CASTIGO AGRESIVO
        if agresivo_activo_anterior and v < 1.70:
             memoria["contador_agresivo"] = 18
             memoria["tp_agresivo"] = "--"
    
    else:
        memoria["sugerencia"] = f"🧠 ENTRENANDO ({len(total_hist)}/100)"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
