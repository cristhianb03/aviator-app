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

# Estructura Maestra Sincronizada con el Index
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

FILE_DB = 'base_datos_ia_pro.csv'

def preparar_modelo_ia():
    try:
        if not os.path.exists(FILE_DB): return None
        df = pd.read_csv(FILE_DB, names=['valor'])
        if len(df) < 50: return None

        # Entrenamiento para detectar éxito >= 1.50x
        df['target'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['v1'] = df['valor'].shift(1)
        df['v2'] = df['valor'].shift(2)
        df['std5'] = df['valor'].rolling(5).std()
        df = df.dropna()

        X = df[['v1', 'v2', 'std5']]
        y = df['target']
        
        model = RandomForestClassifier(n_estimators=100, max_depth=5)
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
    
    # --- CORRECCIÓN LÍNEA 63 (Sintaxis Arreglada) ---
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15:
        memoria["historial_visual"].pop()

    # Guardar para la base de datos de la IA
    with open(FILE_DB, 'a') as f:
        f.write(f"{valor}\n")

    hist = memoria["historial_visual"]
    model = preparar_modelo_ia()
    
    if model and len(hist) >= 5:
        try:
            # Predicción con Machine Learning
            std_act = statistics.stdev(hist[:5])
            features = np.array([[hist[0], hist[1], std_act]])
            prob_ia = model.predict_proba(features)[0][1] * 100
            
            # Filtro de Seguridad Anti-Succión
            if all(v < 1.30 for v in hist[:2]): prob_ia *= 0.3
            
            conf_final = round(prob_ia)
            memoria["confianza"] = f"{conf_final}%"

            # --- LÓGICA DE SALIDA SEGURA (MÍNIMO 1.50x) ---
            mediana = statistics.median(hist)
            val_s = round(max(1.50, mediana * 0.92), 2)
            val_e = round(max(val_s * 2.5, 4.5), 2)

            if conf_final >= 80:
                memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
                memoria["tp_s"] = f"{val_s}x"
                memoria["tp_e"] = f"{val_e}x"
                memoria["fase"] = "🚀 ALTA PRECISIÓN"
            elif conf_final >= 50:
                memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
                memoria["tp_s"] = "1.50x" # Mínimo estricto
                memoria["tp_e"] = "--"
                memoria["fase"] = "⚖️ ESTABLE"
            else:
                memoria["sugerencia"] = "⏳ IA ANALIZANDO"
                memoria["tp_s"] = "--"
                memoria["tp_e"] = "--"
                memoria["fase"] = "📊 RECAUDACIÓN"
        except:
            pass
    else:
        memoria["sugerencia"] = f"🧠 IA RECOLECTANDO ({len(hist)}/50)"

    # Radar Rosa
    dist_r = 0
    for v in hist:
        if v >= 10.0: break
        dist_r += 1
    memoria["radar_rosa"] = f"{min(99, dist_r * 3)}%"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
