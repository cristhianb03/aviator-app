from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import statistics
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

FILE_DB = 'base_datos_ia_v100.csv'

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ IA SINCRONIZANDO",
    "confianza": "0%",
    "radar_rosa": "0%",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "ANALIZANDO",
    "historial_visual": []
}

def motor_inferencia_ia(hist):
    if len(hist) < 100: return None
    try:
        df = pd.DataFrame(hist[::-1], columns=['valor'])
        df['target_150'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['target_val'] = df['valor'].shift(-1)
        for i in range(1, 5): df[f'lag_{i}'] = df['valor'].shift(i)
        df['std'] = df['valor'].rolling(window=5).std()
        
        delta = df['valor'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=10).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=10).mean()
        rs = gain / loss if loss > 0 else 1
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df = df.dropna()
        features = ['lag_1', 'lag_2', 'lag_3', 'std', 'rsi']
        X = df[features]
        
        clf = RandomForestClassifier(n_estimators=100, max_depth=8).fit(X, df['target_150'])
        reg = RandomForestRegressor(n_estimators=100, max_depth=8).fit(X, df['target_val'])
        
        last = X.tail(1)
        return round(clf.predict_proba(last)[0][1] * 100, 2), round(reg.predict(last)[0], 2), df['rsi'].iloc[-1]
    except: return None

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    if valor == memoria["ultimo_valor"]: return {"status": "skipped"}

    memoria["ultimo_valor"] = valor
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    with open(FILE_DB, 'a') as f: f.write(f"{valor}\n")

    try:
        with open(FILE_DB, 'r') as f:
            total_hist = [float(l.strip()) for l in f.readlines() if l.strip()][-200:]
    except: total_hist = []

    registros = len(total_hist)
    res_ia = motor_inferencia_ia(total_hist)
    
    if res_ia:
        prob, val_esp, rsi_act = res_ia
        memoria["confianza"] = f"{round(prob)}%"
        dist_r = 0
        for v in total_hist[::-1]:
            if v >= 10.0: break
            dist_r += 1
        memoria["radar_rosa"] = f"{min(99, dist_r * 2)}%"

        # TARGETS CON SUELO 1.50
        t_s = max(1.50, round(val_esp * 0.85, 2))
        t_e = max(t_s + 0.5, round(val_esp * 1.5, 2))

        if prob >= 85 and rsi_act < 65:
            memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
            memoria["tp_s"], memoria["tp_e"] = f"{t_s}x", f"{t_e}x"
            memoria["fase"] = "🚀 ALTA PRECISIÓN"
        elif prob >= 60:
            memoria["sugerencia"] = "⚠️ SEÑAL MODERADA"
            memoria["tp_s"], memoria["tp_e"] = "1.50x", "--"
            memoria["fase"] = "⚖️ ESTABLE"
        else:
            memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
            memoria["tp_s"], memoria["tp_e"] = "--", "--"
            memoria["fase"] = "📊 RECAUDACIÓN"
    else:
        memoria["sugerencia"] = f"🧠 IA APRENDIENDO ({registros}/100)"
        memoria["fase"] = "APRENDIENDO"

    print(f"🎯 RECIBIDO: {valor}x | Progreso: {registros}/100")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
