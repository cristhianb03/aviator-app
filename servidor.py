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

# Memoria de la IA
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "🧠 IA ENTRENANDO",
    "confianza": "0%",
    "radar_rosa": "0%",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "APRENDIENDO",
    "historial_visual": []
}

FILE_DB = 'base_datos_ia.csv'

def preparar_modelo():
    if not os.path.exists(FILE_DB): return None
    
    df = pd.read_csv(FILE_DB, names=['valor'])
    if len(df) < 50: return None # Necesitamos al menos 50 juegos para que la IA sea lista

    # Creamos "Features" (lo que la IA analiza)
    df['target'] = (df['valor'].shift(-1) >= 1.50).astype(int) # ¿El siguiente fue >= 1.50?
    df['prev1'] = df['valor'].shift(1)
    df['prev2'] = df['valor'].shift(2)
    df['prev3'] = df['valor'].shift(3)
    df['media5'] = df['valor'].rolling(5).mean()
    
    df = df.dropna()
    
    if len(df) < 20: return None

    # Entrenamos a la IA
    X = df[['prev1', 'prev2', 'prev3', 'media5']]
    y = df['target']
    
    model = RandomForestClassifier(n_estimators=50, max_depth=5)
    model.fit(X, y)
    return model

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    memoria["historial_visual.insert(0, valor)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()

    # Guardar para entrenamiento
    with open(FILE_DB, 'a') as f:
        f.write(f"{valor}\n")

    hist = memoria["historial_visual"]
    
    # 1. Intentar predecir con IA
    model = preparar_modelo()
    
    if model and len(hist) >= 5:
        # Preparar datos actuales para la IA
        media_act = statistics.mean(hist[:5])
        current_features = np.array([[hist[0], hist[1], hist[2], media_act]])
        
        # Probabilidad de que el siguiente sea >= 1.50
        prob_ia = model.predict_proba(current_features)[0][1] * 100
        
        # 2. Lógica de Seguridad (Filtro Anti-Succión)
        # Si la IA detecta una racha de crashes muy bajos, baja la confianza
        if all(v < 1.20 for v in hist[:2]): prob_ia = prob_ia * 0.3

        memoria["confianza"] = f"{round(prob_ia)}%"
        
        # 3. Decisiones Basadas en IA
        if prob_ia >= 85: # Solo si la IA está muy segura
            mediana = statistics.median(hist)
            # Retiro seguro NUNCA menor a 1.50
            val_s = round(max(1.50, mediana * 0.95), 2)
            val_e = round(max(val_s * 2.5, 5.0), 2) # Buscamos el premio alto que mencionaste
            
            memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
            memoria["tp_s"] = f"{val_s}x"
            memoria["tp_e"] = f"{val_e}x"
            memoria["fase"] = "🚀 MOMENTUM IA"
        elif prob_ia >= 60:
            memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
            memoria["tp_s"] = "1.50x"
            memoria["tp_e"] = "--"
            memoria["fase"] = "⚖️ ESTABLE"
        else:
            memoria["sugerencia"] = "⏳ IA ANALIZANDO"
            memoria["tp_s"] = "--"
            memoria["tp_e"] = "--"
            memoria["fase"] = "📊 RECAUDACIÓN"
    else:
        memoria["sugerencia"] = f"⏳ IA RECOLECTANDO ({len(hist)}/50)"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
