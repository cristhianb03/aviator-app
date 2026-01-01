from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float
    jugadores: int = 0

FILE_DB = 'database_qrp.csv'

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO RIESGO",
    "estabilidad_estadistica": "0%",
    "riesgo_ponderado": "ANALIZANDO",
    "fase": "MONITOREO",
    "tp_s": "--",
    "historial_visual": []
}

def motor_analisis_qrp(hist_data):
    if len(hist_data) < 100: return None
    try:
        df = pd.DataFrame(hist_data, columns=['valor', 'jugadores'])
        df['target_exit'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['volatilidad'] = df['valor'].rolling(5).std()
        df['momentum'] = df['valor'].ewm(span=5).mean()
        df = df.dropna()
        
        features = ['valor', 'jugadores', 'volatilidad', 'momentum']
        split = int(len(df) * 0.75)
        train, test = df.iloc[:split], df.iloc[split:]
        
        # Modelo conservador nivel enterprise
        model = RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42)
        model.fit(train[features], train['target_exit'])
        
        # Validación de Calidad (Precisión)
        preds = model.predict(test[features])
        precision_v = precision_score(test['target_exit'], preds, zero_division=0)
        baseline = test['target_exit'].mean()
        
        # Inferencia de clúster actual
        current_x = df.tail(1)[features]
        indice_estabilidad = model.predict_proba(current_x)[0][1]
        
        return round(indice_estabilidad * 100, 2), round(precision_v * 100, 2), round(baseline * 100, 2)
    except: return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v, j = res.valor, res.jugadores
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    memoria["ultimo_valor"] = v
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    with open(FILE_DB, 'a') as f: f.write(f"{v},{j}\n")

    try:
        db = pd.read_csv(FILE_DB, names=['valor', 'jugadores'])
        total_hist = db.tail(300).values.tolist()
    except: total_hist = []

    res_qrp = motor_analisis_qrp(total_hist)
    
    if res_qrp:
        ind_est, prec_val, baseline = res_qrp
        memoria["estabilidad_estadistica"] = f"{prec_val}%"
        
        # Criterio de Ventaja Estadística: Precisión > Baseline + 5%
        if prec_val > (baseline + 5):
            if ind_est > 75:
                memoria["sugerencia"] = "✅ CONTEXTO ESTABLE"
                memoria["riesgo_ponderado"] = "BAJO (VALIDADO)"
                memoria["tp_s"] = "1.50x"
                memoria["fase"] = "OPTIMIZACIÓN"
            else:
                memoria["sugerencia"] = "⏳ ESPERAR CONVERGENCIA"
                memoria["riesgo_ponderado"] = "MEDIO"
                memoria["tp_s"] = "--"
                memoria["fase"] = "ZONA NEUTRAL"
        else:
            memoria["sugerencia"] = "🛑 ABSTENCIÓN TÉCNICA"
            memoria["riesgo_ponderado"] = "MÁXIMO (CAOS)"
            memoria["tp_s"] = "--"
            memoria["fase"] = "SIN VENTAJA"
    else:
        memoria["sugerencia"] = f"🧠 CALIBRANDO ({len(total_hist)}/120)"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
