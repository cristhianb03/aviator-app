import os
import requests
import pandas as pd
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.ensemble import RandomForestClassifier
import statistics
from datetime import datetime

# --- CREDENCIALES SEGURAS ---
TOKEN_BOT = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HEADER_PRO = "🛰️ *APOLLO IA – Asistente de Riesgo 1.50x*\n"
FILE_DB = 'database_final_v112.csv'

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float
    jugadores: int = 0

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO",
    "estado": "🔴 BLOQUEADO",
    "confianza": "0%",
    "fecha_actual": datetime.now().date(),
    "entradas_evitadas_hoy": 0,
    "rondas_desde_alerta": 0,
    "alerta_enviada": False,
    "intentos_sesion": 0,
    "bloqueo_por_perdida": False,
    "cache_ia": None,
    "historial_visual": []
}

def enviar_telegram(mensaje, header=True):
    if not TOKEN_BOT: return
    texto = (HEADER_PRO + mensaje) if header else mensaje
    try:
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except: pass

def motor_ia_target_150(hist_data):
    if len(hist_data) < 80: return None
    try:
        df = pd.DataFrame(hist_data, columns=['valor'])
        df['target'] = (df['valor'].shift(-1) >= 1.50).astype(int)
        df['relativo'] = df['valor'] / df['valor'].rolling(10).mean()
        df['volatilidad'] = df['valor'].rolling(5).std()
        df['ratio_crashes'] = (df['valor'] < 1.20).rolling(10).mean()
        df = df.dropna()
        X = df[['relativo', 'volatilidad', 'ratio_crashes']]
        y = df['target']
        model = RandomForestClassifier(n_estimators=150, max_depth=4, random_state=42).fit(X, y)
        curr = X.tail(1)
        prob = model.predict_proba(curr)[0][1] * 100
        return round(prob), df['volatilidad'].iloc[-1], df['relativo'].iloc[-1]
    except: return None

@app.get("/data")
async def get_data(): return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    v = res.valor
    if v == memoria["ultimo_valor"]: return {"status": "skip"}

    # --- 1️⃣ RESET DIARIO ---
    hoy = datetime.now().date()
    if hoy != memoria["fecha_actual"]:
        memoria.update({"fecha_actual": hoy, "entradas_evitadas_hoy": 0, "intentos_sesion": 0, "bloqueo_por_perdida": False})

    # --- 2️⃣ AUDITORÍA DE CICLO (AJUSTE 1: BLINDAJE DE ARRANQUE) ---
    if memoria["alerta_enviada"] and memoria["ultimo_valor"] != 0.0:
        memoria["alerta_enviada"] = False
        if v < 1.50:
            memoria["bloqueo_por_perdida"] = True
            print(f"❌ Drawdown detectado en {v}x. Bloqueando IA.")
        else:
            print(f"✅ Éxito en {v}x. Ciclo completado.")

    # --- 3️⃣ CONGELAMIENTO IA (AJUSTE 2: PROTECCIÓN PRO) ---
    if memoria["bloqueo_por_perdida"]:
        memoria["estado"] = "🔒 BLOQUEO POR RIESGO"
        memoria["sugerencia"] = "🛑 SISTEMA EN PAUSA"
        # Permitimos resetear el bloqueo si sale un multiplicador alto (>10x) o manual
        if v >= 10.0: 
            memoria["bloqueo_por_perdida"] = False
            print("💎 Evento mayor detectado. Desbloqueando Sentinel.")
        else:
            memoria["ultimo_valor"] = v
            return {"status": "safety_locked"}

    memoria["ultimo_valor"] = v
    memoria["rondas_desde_alerta"] += 1
    with open(FILE_DB, 'a') as f: f.write(f"{v}\n")
    
    try:
        db = pd.read_csv(FILE_DB, names=['valor'])
        num_reg, total_hist = len(db), db.tail(250).values.tolist()
    except: num_reg, total_hist = 0, []

    if num_reg >= 100:
        if num_reg % 5 == 0 or memoria["cache_ia"] is None:
            memoria["cache_ia"] = motor_ia_target_150(total_hist)
        
        res_ia = memoria["cache_ia"]
        if res_ia:
            prob, std, rel = res_ia
            memoria["confianza"] = f"{prob}%"

            if memoria["intentos_sesion"] < 5:
                if prob >= 70 and std < 3.8 and rel >= 0.92:
                    memoria["estado"] = "🟢 OK"
                    if not memoria["alerta_enviada"]:
                        msg = (
                            "🟢 *VENTANA ESTADÍSTICA DETECTADA*\n\n"
                            "🎯 Objetivo: *1.50x*\n"
                            f"📊 Confianza IA: *{prob}%*\n"
                            f"📉 Volatilidad: *{round(std,2)}*\n\n"
                            "⚠️ *Entrada válida SOLO para la próxima ronda.*\n"
                            "🛡️ _Si no hay confirmación, APOLO bloqueará._\n\n"
                            "_- No predice. Gestiona riesgo._"
                        )
                        enviar_telegram(msg)
                        memoria["alerta_enviada"] = True
                        memoria["rondas_desde_alerta"] = 0
                        memoria["intentos_sesion"] += 1
                else:
                    memoria["estado"] = "🔴 BLOQUEADO"
                    memoria["entradas_evitadas_hoy"] += 1

            # Heartbeat cada 30 rondas
            if memoria["rondas_desde_alerta"] >= 30:
                msg_status = (
                    "🧠 *REPORTE DE TELEMETRÍA*\n\n"
                    "📉 Análisis de Varianza:\n"
                    f"• Estabilidad: {prob}%\n"
                    f"• Volatilidad: {round(std,2)}\n\n"
                    "⏳ No hay ventaja estadística para *1.50x*\n"
                    f"🛡️ *Entradas evitadas hoy: {memoria['entradas_evitadas_hoy']}*\n\n"
                    "📌 _Capital resguardado. Esperando nodo favorable._"
                )
                enviar_telegram(msg_status, header=False)
                memoria["rondas_desde_alerta"] = 0

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
