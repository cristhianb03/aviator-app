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
    
    # Leemos la base de datos acumulada
    try:
        df = pd.read_csv(FILE_DB, names=['valor'])
        if len(df) < 60: return None # Esperamos 60 juegos para tener base sólida

        # CREACIÓN DE ATRIBUTOS (Lo que la IA analiza)
        # Objetivo: 1 si el siguiente es >= 1.50, 0 si falla
        df['target'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['v1'] = df['valor'].shift(1) # Juego anterior
        df['v2'] = df['valor'].shift(2) # Hace 2 juegos
        df['v3'] = df['valor'].shift(3) # Hace 3 juegos
        # Volatilidad reciente
        df['std5'] = df['valor'].rolling(5).std()
        
        df = df.dropna()
        if len(df) < 30: return None

        X = df[['v1', 'v2', 'v3', 'std5']]
        y = df['target']
        
        # Entrenamos un Bosque Aleatorio (IA de Clasificación)
        model = RandomForestClassifier(n_estimators=100, max_depth=7, random_state=42)
        model.fit(X, y)
        return model
    except:
        return None

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    
    # CORRECCIÓN DE LA LÍNEA 63 (Sintaxis arreglada)
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15:
        memoria["historial_visual"].pop()

    # Guardar en archivo para que la IA aprenda
    with open(FILE_DB, 'a') as f:
        f.write(f"{valor}\n")

    hist = memoria["historial_visual"]
    model = preparar_modelo()
    
    if model and len(hist) >= 5:
        # Preparar los datos actuales para que la IA prediga
        try:
            std_act = statistics.stdev(hist[:5])
            features = np.array([[hist[0], hist[1], hist[2], std_act]])
            
            # Probabilidad de éxito para 1.50x
            prob_ia = model.predict_proba(features)[0][1] * 100
            
            # FILTRO DE SEGURIDAD (Si el casino succiona, bajamos confianza)
            if all(v < 1.30 for v in hist[:2]): prob_ia *= 0.4
            
            conf_final = round(prob_ia)
            memoria["confianza"] = f"{conf_final}%"

            # --- LÓGICA DE SALIDA SEGURA 1.50x ---
            if conf_final >= 82: # ALTA CERTEZA
                mediana = statistics.median(hist)
                # El retiro seguro NUNCA será menor a 1.50x
                val_s = round(max(1.50, mediana * 0.95), 2)
                val_e = round(max(val_s * 2.5, 4.0), 2)
                
                memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
                memoria["tp_s"] = f"{val_s}x"
                memoria["tp_e"] = f"{val_e}x"
                memoria["fase"] = "🚀 MOMENTUM ALTO"
            elif conf_final >= 60:
                memoria["sugerencia"] = "⚠️ SEÑAL EN ANÁLISIS"
                memoria["tp_s"] = "1.50x" # Mínimo estricto
                memoria["tp_e"] = "--"
                memoria["fase"] = "⚖️ ESTABLE"
            else:
                memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
                memoria["tp_s"] = "--"
                memoria["tp_e"] = "--"
                memoria["fase"] = "📊 RECAUDACIÓN"
        except:
            pass
    else:
        memoria["sugerencia"] = f"⏳ IA ENTRENANDO ({len(hist)}/60)"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
