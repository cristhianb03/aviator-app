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

FILE_DB = 'base_datos_ia_final.csv'

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "🧠 IA CALCULANDO",
    "confianza": "0%",
    "radar_rosa": "0%",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "ESCANEO",
    "historial_visual": []
}

def preparar_ia_maestra():
    try:
        if not os.path.exists(FILE_DB): return None
        df = pd.read_csv(FILE_DB, names=['valor'])
        if len(df) < 100: return None 

        # --- INGENIERÍA DE ATRIBUTOS AVANZADA ---
        df['target'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        
        # 1. Lags (Pasado inmediato)
        df['v1'] = df['valor'].shift(1)
        df['v2'] = df['valor'].shift(2)
        
        # 2. EMA (Tendencia Exponencial)
        df['ema'] = df['valor'].ewm(span=5, adjust=False).mean()
        
        # 3. RSI (Fuerza Relativa - ¿Casino lleno o vacío?)
        delta = df['valor'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=10).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=10).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 4. Patrón Binario (0=Azul, 1=Verde)
        df['bin'] = (df['valor'] >= 2.0).astype(int)
        df['pattern'] = df['bin'].shift(1).astype(str) + df['bin'].shift(2).astype(str)
        
        df = df.dropna()
        if len(df) < 60: return None

        # Variables que la IA va a estudiar
        features = ['v1', 'v2', 'ema', 'rsi']
        X = df[features]
        y = df['target']
        
        # Modelo de Bosque Aleatorio Robusto
        model = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)
        model.fit(X, y)
        return model, features, df['rsi'].iloc[-1]
    except Exception as e:
        print(f"Error IA: {e}")
        return None

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 20: memoria["historial_visual"].pop()

    # Guardar para el entrenamiento perpetuo
    with open(FILE_DB, 'a') as f:
        f.write(f"{valor}\n")

    # Obtener total de datos para el contador
    try:
        with open(FILE_DB, 'r') as f:
            total_data = sum(1 for line in f)
    except: total_data = 0

    ia_engine = preparar_ia_maestra()
    
    if ia_engine and len(memoria["historial_visual"]) >= 10:
        model, feat_names, current_rsi = ia_engine
        try:
            hist = memoria["historial_visual"]
            # Preparar datos actuales
            ema_act = statistics.mean(hist[:5])
            # Simulación de RSI actual
            current_x = pd.DataFrame([[hist[0], hist[1], ema_act, current_rsi]], columns=feat_names)
            
            # PREDICCIÓN DE PROBABILIDAD PARA 1.50x
            prob = model.predict_proba(current_x)[0][1] * 100
            
            # FILTROS DE SEGURIDAD (ANTI-SUCCIÓN)
            if valor < 1.10: prob += 15 # Bono rebote
            if all(v < 1.25 for v in hist[:2]): prob *= 0.4 # Protección contra racha negra
            
            conf_f = min(round(prob), 99)
            memoria["confianza"] = f"{conf_f}%"

            # CÁLCULO DE TARGETS (SUELO 1.50x)
            mediana = statistics.median(hist[:25])
            # El seguro se ajusta según la confianza de la IA
            val_s = round(max(1.50, mediana * 0.94 if conf_f > 80 else 1.50), 2)
            val_e = round(max(val_s * 2.2, 5.0 if current_rsi < 40 else 3.0), 2)

            # ESTADOS DE LA IA
            if conf_f >= 85:
                memoria["sugerencia"] = "🔥 ENTRADA CUÁNTICA"
                memoria["tp_s"] = f"{val_s}x"
                memoria["tp_e"] = f"{val_e}x"
                memoria["fase"] = "🚀 ALTA PRECISIÓN"
            elif conf_f >= 65:
                memoria["sugerencia"] = "⚠️ SEÑAL MODERADA"
                memoria["tp_s"] = "1.50x"
                memoria["tp_e"] = "--"
                memoria["fase"] = "⚖️ MERCADO ESTABLE"
            else:
                memoria["sugerencia"] = "🛑 NO ENTRAR"
                memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
                memoria["fase"] = "📊 RECAUDACIÓN"

        except Exception as e:
            print(f"Error Predicción: {e}")
    else:
        memoria["sugerencia"] = f"🧠 ENTRENANDO IA ({total_data}/100)"
        memoria["fase"] = "APRENDIENDO"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
