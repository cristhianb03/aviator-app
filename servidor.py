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
    "fase": "APRENDIENDO",
    "historial_visual": []
}

def contar_registros_totales():
    if not os.path.exists(FILE_DB): return 0
    try:
        df = pd.read_csv(FILE_DB, names=['valor'])
        return len(df)
    except:
        return 0

def preparar_modelo_ia():
    try:
        if not os.path.exists(FILE_DB): return None
        df = pd.read_csv(FILE_DB, names=['valor'])
        if len(df) < 50: return None # Mínimo 50 para empezar a ser inteligente

        # Entrenamiento para predecir si el siguiente es >= 1.50
        df['target'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['v1'] = df['valor'].shift(1)
        df['v2'] = df['valor'].shift(2)
        df['std5'] = df['valor'].rolling(5).std()
        df = df.dropna()

        if len(df) < 30: return None

        X = df[['v1', 'v2', 'std5']]
        y = df['target']
        
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
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
    
    # Burbujas para la App (máximo 15)
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15:
        memoria["historial_visual"].pop()

    # Guardar en base de datos para la IA
    with open(FILE_DB, 'a') as f:
        f.write(f"{valor}\n")

    # Contar datos reales en el archivo
    total_datos = contar_registros_totales()
    hist = memoria["historial_visual"]
    model = preparar_modelo_ia()
    
    if total_datos >= 50 and model and len(hist) >= 5:
        try:
            # PREDICCIÓN CON IA
            std_act = statistics.stdev(hist[:5])
            features = np.array([[hist[0], hist[1], std_act]])
            prob_ia = model.predict_proba(features)[0][1] * 100
            
            # Filtro de seguridad (Anti-succión)
            if all(v < 1.30 for v in hist[:2]): prob_ia *= 0.2
            
            conf_final = round(prob_ia)
            memoria["confianza"] = f"{conf_final}%"

            # LÓGICA DE RETIRO (Mínimo 1.50x)
            mediana = statistics.median(hist)
            val_s = round(max(1.50, mediana * 0.94), 2)
            val_e = round(max(val_s * 2.2, 4.5), 2)

            if conf_final >= 80:
                memoria["sugerencia"] = "🔥 ENTRADA IA CONFIRMADA"
                memoria["tp_s"] = f"{val_s}x"
                memoria["tp_e"] = f"{val_e}x"
                memoria["fase"] = "🚀 PRECISIÓN ALTA"
            elif conf_final >= 55:
                memoria["sugerencia"] = "⚠️ SEÑAL EN ANÁLISIS"
                memoria["tp_s"] = "1.50x"
                memoria["tp_e"] = "--"
                memoria["fase"] = "⚖️ ESTABLE"
            else:
                memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
                memoria["tp_s"] = "--"
                memoria["tp_e"] = "--"
                memoria["fase"] = "📊 RECAUDACIÓN"
        except Exception as e:
            print(f"Error IA: {e}")
    else:
        # AHORA EL CONTADOR MOSTRARÁ EL TOTAL REAL (50+)
        memoria["sugerencia"] = f"🧠 IA RECOLECTANDO ({total_datos}/50)"
        memoria["fase"] = "APRENDIENDO"

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
