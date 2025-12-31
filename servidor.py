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

# --- CORRECCIÓN DE RUTA ABSOLUTA ---
# Esto obliga a Python a crear el archivo en la carpeta del bot, sin importar desde dónde se ejecute
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_DB = os.path.join(BASE_DIR, 'base_datos_quantum_v100.csv')

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

def motor_inferencia_ia(historial_completo):
    if len(historial_completo) < 100:
        return None
    try:
        df = pd.DataFrame(historial_completo[::-1], columns=['valor'])
        df['target_150'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['target_val'] = df['valor'].shift(-1)
        for i in range(1, 6):
            df[f'lag_{i}'] = df['valor'].shift(i)
        df['ema_short'] = df['valor'].ewm(span=3).mean()
        df['std_dev'] = df['valor'].rolling(window=5).std()
        
        delta = df['valor'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=10).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=10).mean()
        rs = gain / loss if loss > 0 else 1
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df = df.dropna()
        if len(df) < 30: return None

        features = ['lag_1', 'lag_2', 'lag_3', 'ema_short', 'std_dev', 'rsi']
        X = df[features]
        
        clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42).fit(X, df['target_150'])
        reg = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42).fit(X, df['target_val'])
        
        last_data = X.tail(1)
        return round(clf.predict_proba(last_data)[0][1] * 100, 2), round(reg.predict(last_data)[0], 2), df['rsi'].iloc[-1]
    except:
        return None

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    
    # Filtro de duplicados
    if valor == memoria["ultimo_valor"]:
        return {"status": "ignorado"}

    memoria["ultimo_valor"] = valor
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    # --- PROCESO DE GUARDADO SEGURO ---
    try:
        with open(FILE_DB, 'a') as f: 
            f.write(f"{valor}\n")
        print(f"💾 DATO GUARDADO EN: {FILE_DB}")
    except Exception as e:
        print(f"❌ ERROR AL ESCRIBIR ARCHIVO: {e}")

    # Leer para contar
    try:
        with open(FILE_DB, 'r') as f:
            total_hist = [float(line.strip()) for line in f.readlines() if line.strip()]
    except: total_hist = []

    res_ia = motor_inferencia_ia(total_hist[-150:])
    
    if res_ia:
        prob, val_esp, rsi_act = res_ia
        memoria["confianza"] = f"{round(prob)}%"
        
        dist_rosa = 0
        for v in total_hist[::-1]:
            if v >= 10.0: break
            dist_rosa += 1
        memoria["radar_rosa"] = f"{min(99, dist_rosa * 2)}%"

        t_s = max(1.50, round(val_esp * 0.82, 2))
        t_e = max(t_s + 0.5, round(val_esp * 1.4, 2))

        if prob >= 85 and rsi_act < 60:
            memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
            memoria["fase"] = "🚀 ALTA PRECISIÓN"
            memoria["tp_s"] = f"{t_seguro}x"; memoria["tp_e"] = f"{t_explosivo}x"
        elif prob >= 60:
            memoria["sugerencia"] = "⚠️ SEÑAL MODERADA"
            memoria["fase"] = "⚖️ ESTABLE"
            memoria["tp_s"] = "1.50x"
        else:
            memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
            memoria["fase"] = "📊 RECAUDACIÓN"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
    else:
        memoria["sugerencia"] = f"🧠 IA APRENDIENDO ({len(total_hist)}/100)"
        memoria["fase"] = "APRENDIENDO"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
