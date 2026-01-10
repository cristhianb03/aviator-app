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
    jugadores: int = 0

FILE_DB = 'database_gatekeeper_v95_1.csv'

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO IA",
    "fase": "ESCANEO",
    "estado": "🔴 BLOQUEADO",
    "intentos_sesion": 0,    
    "bloqueo_por_perdida": False,
    "historial_visual": []
}

cache_ia = {"prob": 0, "std": 0, "rel": 1.0}

def motor_ia_contextual(hist_data):
    if len(hist_data) < 80: return None
    try:
        df = pd.DataFrame(hist_data, columns=['valor'])
        df['target'] = (df['valor'].shift(-1) >= 1.20).astype(int)
        df['relativo'] = df['valor'] / df['valor'].rolling(10).mean()
        df['volatilidad'] = df['valor'].rolling(5).std()
        df['ratio_crashes'] = (df['valor'] < 1.10).rolling(10).mean()
        df['std_larga'] = df['valor'].rolling(20).std()
        df = df.dropna()
        features = ['relativo', 'volatilidad', 'ratio_crashes', 'std_larga']
        X = df[features]
        y = df['target']
        model = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
        model.fit(X, y)
        current_x = X.tail(1)
        prob_safe = model.predict_proba(current_x)[0][1] * 100
        return round(prob_safe), df['volatilidad'].iloc[-1], df['relativo'].iloc[-1]
    except: return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v = res.valor
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    # --- 🔍 SENSOR DE RECUPERACIÓN EN TIEMPO REAL ---
    # Calculamos un 'rel' fresco aunque el modelo esté congelado
    # Esto permite que el bot sepa si el mercado sanó hoy o sigue enfermo.
    try:
        if os.path.exists(FILE_DB):
            df_check = pd.read_csv(FILE_DB, names=['valor']).tail(10)
            rel_fresco = v / df_check['valor'].mean() if len(df_check) > 0 else 1.0
        else: rel_fresco = 1.0
    except: rel_fresco = 1.0

    # 🔧 REINICIO VALIDADO CON SENSOR FRESCO
    if memoria["bloqueo_por_perdida"] and v >= 1.50 and rel_fresco >= 0.90:
        memoria["bloqueo_por_perdida"] = False
        memoria["intentos_sesion"] = 0
        memoria["fase"] = "MERCADO RESTABLECIDO"
        print(f"✅ REAPERTURA: V:{v}x Rel_F:{rel_fresco:.2f}")

    # AUDITORÍA DE STOP LOSS
    if memoria["estado"] == "🟢 OK":
        memoria["intentos_sesion"] += 1
        if v < 1.20:
            memoria["bloqueo_por_perdida"] = True
            memoria["fase"] = "BLOQUEO DE BANCA"

    # PROTECCIÓN POR CRASH 1.0X
    if v < 1.05:
        memoria["bloqueo_por_perdida"] = True
        memoria["fase"] = "PROTECCIÓN CRASH 1.0X"

    memoria["ultimo_valor"] = v
    memoria["historial_visual"].insert(0, v)
    if len(memoria["historial_visual"]) > 15: memoria["historial_visual"].pop()
    
    # --- CONGELAMIENTO DE APRENDIZAJE ---
    if memoria["bloqueo_por_perdida"]:
        return {"status": "shield_active_no_learning"}

    # PERSISTENCIA DE DATOS (Solo en mercados operables)
    with open(FILE_DB, 'a') as f: f.write(f"{v}\n")

    try:
        db = pd.read_csv(FILE_DB, names=['valor'])
        total_hist = db.tail(250).values.tolist()
    except: total_hist = []

    # Entrenamiento por lotes cada 5 rondas
    global cache_ia
    if len(total_hist) % 5 == 0 or cache_ia["prob"] == 0:
        res_ia = motor_ia_contextual(total_hist)
        if res_ia:
            cache_ia["prob"], cache_ia["std"], cache_ia["rel"] = res_ia

    # TOMA DE DECISIÓN
    if cache_ia["prob"] > 0 and memoria["intentos_sesion"] < 3:
        prob, std, rel = cache_ia["prob"], cache_ia["std"], cache_ia["rel"]
        umbral = 60 if std < 2.5 else 64

        if rel < 0.85:
            memoria["estado"] = "🔴 BLOQUEADO"; memoria["sugerencia"] = "NO JUGAR"; memoria["fase"] = "SUCCIÓN DETECTADA"
        elif std >= 4.5:
            memoria["estado"] = "🔴 BLOQUEADO"; memoria["sugerencia"] = "NO JUGAR"; memoria["fase"] = "VOLATILIDAD ALTA"
        elif prob < umbral:
            memoria["estado"] = "🔴 BLOQUEADO"; memoria["sugerencia"] = "NO JUGAR"; memoria["fase"] = "BAJA CONVERGENCIA"
        else:
            memoria["estado"] = "🟢 OK"; memoria["sugerencia"] = "ENTRADA: 1.20x"; memoria["fase"] = "CONTEXTO ÓPTIMO"
    else:
        if memoria["intentos_sesion"] >= 3:
            memoria["estado"] = "🔴 BLOQUEADO"; memoria["sugerencia"] = "🏁 TERMINADO"; memoria["fase"] = "LÍMITE DIARIO"
        else:
            memoria["sugerencia"] = f"🧠 CALIBRANDO ({len(total_hist)}/80)"

    print(f"[{v}x] Rel:{rel:.2f} | Std:{std:.2f} | Prob:{prob}% → {memoria['fase']}")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
