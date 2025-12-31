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

FILE_DB = 'base_datos_ia_pro.csv'

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "🧠 IA INICIANDO",
    "confianza": "0%",
    "radar_rosa": "0%",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "CALIBRANDO",
    "historial_visual": []
}

def preparar_ia_robusta():
    try:
        if not os.path.exists(FILE_DB): return None
        df = pd.read_csv(FILE_DB, names=['valor'])
        if len(df) < 100: return None # Subimos a 100 para que sea más "madura"

        # --- INGENIERÍA DE ATRIBUTOS (FEATURE ENGINEERING) ---
        df['target'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        
        # Atributos de Retraso (Lags)
        for i in range(1, 6):
            df[f'v{i}'] = df['valor'].shift(i)
        
        # Volatilidad y Tendencia (EMA)
        df['ema5'] = df['valor'].ewm(span=5, adjust=False).mean()
        df['std5'] = df['valor'].rolling(5).std()
        
        # Indicador de "Hambre" del casino (RSI simple)
        df['ganancias_recientes'] = (df['valor'] >= 2.0).rolling(10).sum()
        
        df = df.dropna()
        if len(df) < 50: return None

        # Selección de columnas para el aprendizaje
        features = ['v1', 'v2', 'v3', 'ema5', 'std5', 'ganancias_recientes']
        X = df[features]
        y = df['target']
        
        # Bosque Aleatorio más profundo para mayor precisión
        model = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=42)
        model.fit(X, y)
        return model, features
    except Exception as e:
        print(f"Error entrenamiento: {e}")
        return None

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    
    # Actualizar burbujas visuales
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()

    # Guardar dato para aprendizaje perpetuo
    with open(FILE_DB, 'a') as f:
        f.write(f"{valor}\n")

    # Contar registros reales del archivo
    try:
        total_data = pd.read_csv(FILE_DB).shape[0]
    except:
        total_data = 0

    ia_data = preparar_ia_robusta()
    
    if ia_data and len(memoria["historial_visual"]) >= 10:
        model, feat_names = ia_data
        try:
            hist = memoria["historial_visual"]
            # Preparar vector de datos actuales para la predicción
            ema5_act = statistics.mean(hist[:5]) # Aproximación rápida
            std5_act = statistics.stdev(hist[:5])
            gan_act = len([v for v in hist[:10] if v >= 2.0])
            
            current_x = pd.DataFrame([[hist[0], hist[1], hist[2], ema5_act, std5_act, gan_act]], 
                                     columns=feat_names)
            
            # Predicción de probabilidad
            prob = model.predict_proba(current_x)[0][1] * 100
            
            # FILTRO DE SEGURIDAD (Si el último fue 1.0x, la IA se pone en alerta)
            if valor < 1.10: prob += 15
            if all(v < 1.25 for v in hist[:2]): prob *= 0.5 # Protección succión
            
            conf_f = min(round(prob), 99)
            memoria["confianza"] = f"{conf_f}%"

            # CÁLCULO DE TARGETS (Suelo estricto 1.50x)
            mediana = statistics.median(hist[:20])
            val_s = round(max(1.50, mediana * 0.96), 2)
            val_e = round(max(val_s * 2.2, 4.8), 2)

            if conf_f >= 85:
                memoria["sugerencia"] = "🔥 ENTRADA TITANIUM"
                memoria["tp_s"] = f"{val_s}x"
                memoria["tp_e"] = f"{val_e}x"
                memoria["fase"] = "🚀 ALTA PRECISIÓN"
            elif conf_f >= 60:
                memoria["sugerencia"] = "⚠️ SEÑAL MODERADA"
                memoria["tp_s"] = "1.50x"
                memoria["tp_e"] = "--"
                memoria["fase"] = "⚖️ ESTABLE"
            else:
                memoria["sugerencia"] = "🛑 NO ENTRAR"
                memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
                memoria["fase"] = "📊 RECAUDACIÓN"

        except Exception as e:
            print(f"Error predicción: {e}")
    else:
        memoria["sugerencia"] = f"🧠 ENTRENANDO IA ({total_data}/100)"
        memoria["fase"] = "APRENDIENDO"

    # Radar Rosa por Déficit
    dist_r = 0
    for v in memoria["historial_visual"]:
        if v >= 10.0: break
        dist_r += 1
    memoria["radar_rosa"] = f"{min(99, dist_r * 4)}%"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
