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
    jugadores: int = 0

# Base de datos final para producción
FILE_DB = 'database_prod_v98.csv'

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO 1.50x",
    "fase": "ESCANEO",
    "estado": "🔴 BLOQUEADO",
    "confianza": "0%",
    "intentos_sesion": 0,    
    "bloqueo_por_perdida": False,
    "contador_recuperacion": 0,
    "historial_visual": []
}

cache_ia = {"prob": 0, "std": 0, "rel": 1.0}

def motor_ia_target_150(hist_data):
    if len(hist_data) < 80: return None
    try:
        df = pd.DataFrame(hist_data, columns=['valor'])
        
        # Objetivo de la IA: Éxito únicamente si llega a 1.50x
        df['target'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        
        # Atributos de contexto real
        df['relativo'] = df['valor'] / df['valor'].rolling(10).mean()
        df['volatilidad'] = df['valor'].rolling(5).std()
        df['ratio_crashes'] = (df['valor'] < 1.20).rolling(10).mean()
        
        df = df.dropna()
        features = ['relativo', 'volatilidad', 'ratio_crashes']
        X = df[features]
        y = df['target']
        
        model = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
        model.fit(X, y)
        
        current_x = X.tail(1)
        prob_safe = model.predict_proba(current_x)[0][1] * 100
        return round(prob_safe), df['volatilidad'].iloc[-1], df['relativo'].iloc[-1]
    except:
        return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v = res.valor
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    # Limpiar fase de reset visual
    if memoria["fase"] == "EVENTO MAYOR": memoria["fase"] = "ESCANEO"

    # Reset por Salida Alta (>= 10x)
    if v >= 10.0:
        memoria.update({"bloqueo_por_perdida": False, "intentos_sesion": 0, "contador_recuperacion": 0, "fase": "EVENTO MAYOR"})

    # Caducidad de succión (8 rondas)
    if memoria["fase"] == "SUCCIÓN DETECTADA":
        memoria["contador_recuperacion"] += 1
        if memoria["contador_recuperacion"] >= 8:
            memoria.update({"bloqueo_por_perdida": False, "fase": "ESCANEO", "contador_recuperacion": 0})

    # Auditoría de Sesión (Meta 1.50x)
    if memoria["estado"] == "🟢 OK":
        memoria["intentos_sesion"] += 1
        if v < 1.50:
            memoria.update({"bloqueo_por_perdida": True, "fase": "DRAWDOWN 1.50x"})

    # Bloqueo por Crash Crítico
    if v < 1.05:
        memoria.update({"bloqueo_por_perdida": True, "fase": "CRASH EXTREMO"})

    memoria["ultimo_valor"] = v
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    with open(FILE_DB, 'a') as f: f.write(f"{v}\n")

    try:
        db = pd.read_csv(FILE_DB, names=['valor'])
        total_hist = db.tail(250).values.tolist()
        num_registros = len(db)
    except: 
        total_hist = []
        num_registros = 0

    global cache_ia
    # Re-entrenamiento rápido cada 3 rondas
    if len(total_hist) % 3 == 0 or cache_ia["prob"] == 0:
        res_ia = motor_ia_target_150(total_hist)
        if res_ia: cache_ia["prob"], cache_ia["std"], cache_ia["rel"] = res_ia

    # --- TOMA DE DECISIÓN OPERATIVA ---
    prob, std, rel = cache_ia["prob"], cache_ia["std"], cache_ia["rel"]
    
    # Ajuste de umbrales por madurez de base de datos
    if num_registros < 150:
        prob_min = 68
        std_max = 4.2
    else:
        prob_min = 70
        std_max = 3.8

    # 5 INTENTOS POR SESIÓN (Mejora solicitada)
    if not memoria["bloqueo_por_perdida"] and memoria["intentos_sesion"] < 5:
        if rel < 0.92:
            memoria.update({"estado": "🔴 BLOQUEADO", "sugerencia": "NO JUGAR", "fase": "SUCCIÓN DETECTADA", "confianza": f"{max(prob-20,5)}%"})
        elif prob >= prob_min and std < std_max:
            memoria.update({"estado": "🟢 OK", "sugerencia": "ENTRADA: 1.50x", "fase": "CONTEXTO VALIDADO", "confianza": f"{prob}%"})
        else:
            memoria.update({"estado": "🔴 BLOQUEADO", "sugerencia": "NO JUGAR", "fase": "VENTAJA INSUFICIENTE", "confianza": f"{max(prob-10,5)}%"})
    else:
        memoria.update({"estado": "🔴 BLOQUEADO", "sugerencia": "🛑 STOP", "confianza": f"{max(prob-30,5)}%"})
        if not any(x in memoria["fase"] for x in ["CRASH", "DRAWDOWN"]):
            memoria["fase"] = "LÍMITE DE SESIÓN"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
