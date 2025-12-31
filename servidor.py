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

FILE_DB = 'base_datos_ia_v60.csv'

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

def motor_ia(historial_completo):
    # La IA requiere 100 datos únicos
    if len(historial_completo) < 100: return None
    try:
        df = pd.DataFrame(historial_completo[::-1], columns=['valor'])
        
        # Etiquetado para IA (¿El siguiente fue >= 1.50?)
        df['target_150'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['target_val'] = df['valor'].shift(-1)
        
        # Variables de análisis (EMA y Desviación)
        for i in range(1, 4): df[f'lag_{i}'] = df['valor'].shift(i)
        df['std'] = df['valor'].rolling(window=5).std()
        
        # RSI (Fuerza del mercado)
        delta = df['valor'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=10).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=10).mean()
        rs = gain / loss if loss.iloc[-1] > 0 else 1
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df = df.dropna()
        if len(df) < 20: return None # Seguridad de datos

        features = ['lag_1', 'lag_2', 'std', 'rsi']
        X = df[features]
        
        # Entrenamos el Ensamble IA
        clf = RandomForestClassifier(n_estimators=100, max_depth=7).fit(X, df['target_150'])
        reg = RandomForestRegressor(n_estimators=100, max_depth=7).fit(X, df['target_val'])
        
        last = X.tail(1)
        prob = clf.predict_proba(last)[0][1] * 100
        val_esp = reg.predict(last)[0]
        
        return round(prob, 2), round(val_esp, 2), df['rsi'].iloc[-1]
    except Exception as e:
        print(f"Error en motor_ia: {e}")
        return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v = res.valor
    if v == memoria["ultimo_valor"]: return {"status": "skipped"}

    memoria["ultimo_valor"] = v
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    with open(FILE_DB, 'a') as f: f.write(f"{v}\n")

    try:
        with open(FILE_DB, 'r') as f:
            total_hist = [float(l.strip()) for l in f.readlines() if l.strip()][-200:]
    except: total_hist = []

    registros = len(total_hist)
    res_ia = motor_ia(total_hist)
    
    if registros >= 100 and res_ia:
        prob, val_esp, rsi_act = res_ia
        memoria["fase"] = "🚀 IA TITANIUM ACTIVA"
        
        # Filtro de succión (Protección extra)
        if all(x < 1.30 for x in total_hist[-2:]): prob *= 0.3

        memoria["confianza"] = f"{round(prob)}%"
        
        # CÁLCULO DE TARGETS (SUELO ESTRICTO 1.50)
        # Solo calculamos si la probabilidad es aceptable
        if prob >= 40:
            t_s = max(1.50, round(val_esp * 0.88, 2))
            t_e = max(t_s + 0.5, round(val_esp * 1.5, 2))
            
            # Definir sugerencia basada en probabilidad de la IA
            if prob >= 80:
                memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
                memoria["tp_s"], memoria["tp_e"] = f"{t_s}x", f"{t_e}x"
            elif prob >= 50:
                memoria["sugerencia"] = "⚠️ SEÑAL EN ANÁLISIS"
                memoria["tp_s"], memoria["tp_e"] = "1.50x", "--"
            else:
                memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
                memoria["tp_s"], memoria["tp_e"] = "--", "--"
        else:
            memoria["sugerencia"] = "🛑 NO ENTRAR (RIESGO)"
            memoria["tp_s"], memoria["tp_e"] = "--", "--"
    else:
        # Modo aprendizaje activo
        memoria["sugerencia"] = f"🧠 IA APRENDIENDO ({registros}/100)"
        memoria["fase"] = "APRENDIENDO"

    # Radar Rosa
    dist_r = 0
    for x in total_hist[::-1]:
        if x >= 10.0: break
        dist_r += 1
    memoria["radar_rosa"] = f"{min(99, dist_r * 3)}%"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
