from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import statistics
import collections
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

FILE_DB = 'base_datos_ensamble_v80.csv'

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "🧠 IA RECOLECTANDO",
    "confianza": "0%",
    "radar_rosa": "0%",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "APRENDIENDO",
    "historial_visual": []
}

# --- MOTOR 1: GRAFOS (TRANSICIONES) ---
grafo = collections.defaultdict(lambda: collections.Counter())
def cat_150(v): return "OK" if v >= 1.50 else "FAIL"

def motor_inferencia_ensamble(total_hist):
    if len(total_hist) < 100: return None
    try:
        df = pd.DataFrame(total_hist[::-1], columns=['valor'])
        
        # 1. ATRIBUTOS BASE (Lo que ya teníamos)
        df['target'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['v1'] = df['valor'].shift(1)
        df['v2'] = df['valor'].shift(2)
        
        # 2. ATRIBUTOS RSI/EMA
        df['ema'] = df['valor'].ewm(span=5).mean()
        delta = df['valor'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(10).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(10).mean()
        rs = gain / loss if loss.iloc[-1] > 0 else 1
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. ATRIBUTO DE GRAFOS (Señal combinada)
        # Entrenamos un sub-grafo interno para darle una puntuación a la IA
        graph_scores = []
        for i in range(len(df)-4):
            nodo = tuple(cat_150(x) for x in df['valor'].iloc[i+1:i+4])
            res_sig = cat_150(df['valor'].iloc[i])
            grafo[nodo][res_sig] += 1
        
        df = df.dropna()
        X = df[['v1', 'v2', 'ema', 'rsi']]
        y = df['target']
        
        # ENTRENAMIENTO DEL BOSQUE ALEATORIO
        model = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=42)
        model.fit(X, y)
        
        # Predicción actual
        current_node = tuple(cat_150(x) for x in total_hist[:3])
        prob_graph = (grafo[current_node]["OK"] / sum(grafo[current_node].values())) if sum(grafo[current_node].values()) > 0 else 0.5
        
        input_now = pd.DataFrame([[total_hist[0], total_hist[1], df['ema'].iloc[-1], df['rsi'].iloc[-1]]], 
                                 columns=['v1', 'v2', 'ema', 'rsi'])
        
        prob_ia = model.predict_proba(input_now)[0][1]
        
        # Fusión Final: 50% ML + 50% Grafos
        prob_final = (prob_ia * 0.5) + (prob_graph * 0.5)
        
        return round(prob_final * 100, 2), df['rsi'].iloc[-1], statistics.median(total_hist[:20])
    except Exception as e:
        print(f"Error IA: {e}")
        return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v = res.valor
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    memoria["ultimo_valor"] = v
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    with open(FILE_DB, 'a') as f: f.write(f"{v}\n")

    try:
        with open(FILE_DB, 'r') as f:
            total_hist = [float(line.strip()) for line in f.readlines() if line.strip()][-250:]
    except: total_hist = []

    count = len(total_hist)
    res_ia = motor_inferencia_ensamble(total_hist)
    
    if count >= 100 and res_ia:
        prob, rsi_act, mediana = res_ia
        
        # --- FILTROS DE SEGURIDAD EXTREMA ---
        succion = all(x < 1.30 for x in total_hist[-2:])
        if succion: prob *= 0.2 # Hundimos la confianza si hay succión
        
        memoria["confianza"] = f"{round(prob)}%"
        
        # CÁLCULO DE TARGETS (SUELO ESTRICTO 1.50x)
        # Aplicamos un buffer de seguridad del 10% (0.90) para asertividad
        val_s = round(max(1.50, mediana * 0.90), 2)
        val_e = round(max(val_s * 2.2, mediana * 2.0), 2)

        # Lógica de Recomendación
        if prob >= 88 and not succion:
            memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
            memoria["tp_s"], memoria["tp_e"] = f"{val_s}x", f"{val_e}x"
            memoria["fase"] = "🚀 ALTA PRECISIÓN"
        elif prob >= 65 and not succion:
            memoria["sugerencia"] = "⚠️ SEÑAL MODERADA"
            memoria["tp_s"] = "1.50x"
            memoria["tp_e"] = "--"
            memoria["fase"] = "⚖️ ESTABLE"
        else:
            memoria["sugerencia"] = "🛑 NO ENTRAR (RIESGO)"
            memoria["tp_s"], memoria["tp_e"] = "--", "--"
            memoria["fase"] = "📊 RECAUDACIÓN"
    else:
        memoria["sugerencia"] = f"🧠 IA APRENDIENDO ({count}/100)"

    # Radar Rosa por Déficit
    dist_r = 0
    for x in total_hist[::-1]:
        if x >= 10.0: break
        dist_r += 1
    memoria["radar_rosa"] = f"{min(99, dist_r * 2)}%"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
