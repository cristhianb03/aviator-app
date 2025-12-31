from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import statistics
import os
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

# --- RUTA ABSOLUTA PARA EL ARCHIVO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_DB = os.path.join(BASE_DIR, 'base_datos_ia_v100.csv')

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "🧠 IA SINCRONIZANDO",
    "confianza": "0%",
    "radar_rosa": "0%",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "APRENDIENDO",
    "historial_visual": []
}

def motor_ia_avanzado(hist_completo):
    if len(hist_completo) < 50: return None
    try:
        df = pd.DataFrame(hist_completo[::-1], columns=['valor'])
        df['target_150'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['target_val'] = df['valor'].shift(-1)
        for i in range(1, 4): df[f'lag_{i}'] = df['valor'].shift(i)
        
        # EMA y RSI (Indicadores de presión)
        df['ema'] = df['valor'].ewm(span=5).mean()
        delta = df['valor'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(10).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(10).mean()
        df['rsi'] = 100 - (100 / (1 + (gain/loss)))
        
        df = df.dropna()
        features = ['lag_1', 'lag_2', 'ema', 'rsi']
        X = df[features]
        
        clf = RandomForestClassifier(n_estimators=100, max_depth=10).fit(X, df['target_150'])
        reg = RandomForestRegressor(n_estimators=100, max_depth=10).fit(X, df['target_val'])
        
        last = X.tail(1)
        prob = clf.predict_proba(last)[0][1] * 100
        val_pred = reg.predict(last)[0]
        return round(prob, 2), round(val_pred, 2), df['rsi'].iloc[-1]
    except: return None

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    if valor == memoria["ultimo_valor"]: return {"status": "skip"}

    memoria["ultimo_valor"] = valor
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    # FORZAR CREACIÓN DE ARCHIVO
    try:
        with open(FILE_DB, 'a') as f:
            f.write(f"{valor}\n")
        print(f"💾 Guardado: {valor} en {FILE_DB}")
    except Exception as e:
        print(f"❌ Error disco: {e}")

    try:
        with open(FILE_DB, 'r') as f:
            total_hist = [float(line.strip()) for line in f.readlines() if line.strip()][-150:]
    except: total_hist = []

    count = len(total_hist)
    ia_res = motor_ia_avanzado(total_hist)
    
    if ia_res:
        prob, val_esp, rsi_act = ia_res
        # LA IA DEFINE LA CONFIANZA SOLA
        memoria["confianza"] = f"{round(prob)}%"
        t_s = max(1.50, round(val_esp * 0.85, 2))
        t_e = max(t_s + 0.5, round(val_esp * 1.4, 2))

        if prob >= 85 and rsi_act < 60:
            memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
            memoria["tp_s"] = f"{t_s}x"; memoria["tp_e"] = f"{t_e}x"
            memoria["fase"] = "🚀 ALTA PRECISIÓN"
        elif prob >= 60:
            memoria["sugerencia"] = "⚠️ SEÑAL MODERADA"
            memoria["tp_s"] = "1.50x"; memoria["tp_e"] = "--"
            memoria["fase"] = "⚖️ ESTABLE"
        else:
            memoria["sugerencia"] = "🛑 NO ENTRAR"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
            memoria["fase"] = "📊 RECAUDACIÓN"
    else:
        memoria["sugerencia"] = f"🧠 IA RECOLECTANDO ({count}/100)"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
