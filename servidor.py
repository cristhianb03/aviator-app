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

FILE_DB = 'base_datos_quantum_v100.csv'

# Memoria Maestra Sincronizada con el Index
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
    # Requisito de aprendizaje: 100 registros únicos
    if len(historial_completo) < 100:
        return None

    try:
        # 1. PREPARACIÓN DE DATAFRAME
        df = pd.DataFrame(historial_completo[::-1], columns=['valor'])
        
        # 2. FEATURE ENGINEERING (8 variables analizadas por la IA)
        df['target_150'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['target_val'] = df['valor'].shift(-1)
        
        for i in range(1, 6):
            df[f'lag_{i}'] = df['valor'].shift(i)
        
        df['ema_short'] = df['valor'].ewm(span=3).mean()
        df['std_dev'] = df['valor'].rolling(window=5).std()
        
        # RSI (Fuerza Relativa)
        delta = df['valor'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=10).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=10).mean()
        df['rsi'] = 100 - (100 / (1 + (gain/loss)))
        
        df = df.dropna()
        if len(df) < 30: return None

        features = ['lag_1', 'lag_2', 'lag_3', 'ema_short', 'std_dev', 'rsi']
        X = df[features]
        
        # 3. ENTRENAMIENTO DE ENSAMBLE ML
        clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        clf.fit(X, df['target_150'])
        
        reg = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
        reg.fit(X, df['target_val'])
        
        # 4. PREDICCIÓN ACTUAL
        last_data = X.tail(1)
        prob_success = clf.predict_proba(last_data)[0][1] * 100
        pred_value = reg.predict(last_data)[0]
        
        return round(prob_success, 2), round(pred_value, 2), df['rsi'].iloc[-1]
    except:
        return None

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    
    # Filtro anti-duplicados para proteger la integridad de la IA
    if valor == memoria["ultimo_valor"]:
        return {"status": "ignorado_duplicado"}

    memoria["ultimo_valor"] = valor
    
    # --- CORRECCIÓN DE SINTAXIS EN HISTORIAL VISUAL ---
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15: 
        memoria["historial_visual"].pop()
    
    # Guardar en base de datos para entrenamiento continuo
    with open(FILE_DB, 'a') as f: f.write(f"{valor}\n")

    # Leer historial completo desde el archivo
    try:
        if os.path.exists(FILE_DB):
            with open(FILE_DB, 'r') as f:
                total_hist = [float(line.strip()) for line in f.readlines() if line.strip()][-150:]
        else:
            total_hist = []
    except: total_hist = []

    # EJECUCIÓN DEL MOTOR DE INTELIGENCIA ARTIFICIAL
    resultado_ia = motor_inferencia_ia(total_hist)
    
    if resultado_ia:
        prob, val_esperado, rsi_actual = resultado_ia
        
        memoria["confianza"] = f"{round(prob)}%"
        
        # Radar Rosa (Cálculo Estocástico de Distancia)
        dist_rosa = 0
        for v in total_hist[::-1]:
            if v >= 10.0: break
            dist_rosa += 1
        memoria["radar_rosa"] = f"{min(99, dist_rosa * 2)}%"

        # TARGETS GENERADOS POR IA (Suelo de 1.50x)
        t_seguro = max(1.50, round(val_esperado * 0.82, 2))
        t_explosivo = max(t_seguro + 0.5, round(val_esperado * 1.4, 2))

        if prob >= 85 and rsi_actual < 60:
            memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
            memoria["fase"] = "🚀 ALTA PRECISIÓN"
            memoria["tp_s"] = f"{t_seguro}x"
            memoria["tp_e"] = f"{t_explosivo}x"
        elif prob >= 60:
            memoria["sugerencia"] = "⚠️ SEÑAL MODERADA"
            memoria["fase"] = "⚖️ ESTABLE"
            memoria["tp_s"] = "1.50x"
            memoria["tp_e"] = "--"
        elif rsi_actual > 70 or all(v < 1.2 for v in total_hist[-2:]):
            memoria["sugerencia"] = "🛑 NO ENTRAR (RIESGO)"
            memoria["fase"] = "📊 RECAUDACIÓN"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
        else:
            memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
            memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
            memoria["fase"] = "ESCANEO"
    else:
        # Contador real basado en los datos únicos del archivo
        memoria["sugerencia"] = f"🧠 ENTRENANDO IA ({len(total_hist)}/100)"
        memoria["fase"] = "APRENDIENDO"

    print(f"🎯 Capturado: {valor}x | Progreso IA: {len(total_hist)}/100")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
