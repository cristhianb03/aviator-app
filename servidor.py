from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics
import collections
import pandas as pd
import numpy as np

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

# Estructura Maestra Sincronizada
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ ANALIZANDO",
    "confianza": "0%",
    "radar_rosa": "0%",
    "fase": "CALIBRANDO",
    "tp_s": "--",
    "tp_e": "--",
    "historial_visual": []
}

# Motor de Grafos para 1.50x
grafo = collections.defaultdict(lambda: collections.Counter())
def cat_150(v): return "OK" if v >= 1.50 else "FAIL"

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 100: memoria["historial_visual"].pop()
    
    hist = memoria["historial_visual"]
    if len(hist) < 12:
        memoria["sugerencia"] = f"🧠 IA RECOLECTANDO ({len(hist)}/12)"
        return {"status": "ok"}

    # --- 1. MOTOR DE GRAFOS (TRANSICIONES) ---
    for i in range(len(hist) - 4):
        nodo = tuple(cat_150(x) for x in hist[i+1:i+4])
        resultado = cat_150(hist[i])
        grafo[nodo][resultado] += 1
    
    situacion_act = tuple(cat_150(x) for x in hist[:3])
    prob_grafo = (grafo[situacion_act]["OK"] / sum(grafo[situacion_act].values()) * 100) if sum(grafo[situacion_act].values()) > 0 else 50

    # --- 2. MOTOR DE MOMENTUM Y RSI (SALUD DEL MERCADO) ---
    df = pd.Series(hist[:30])
    ema5 = df.ewm(span=5).mean().iloc[0]
    mediana = statistics.median(hist[:20])
    
    # RSI Simple
    cambios = df.diff()
    ganancia = (cambios.where(cambios > 0, 0)).rolling(10).mean().iloc[-1]
    perdida = (-cambios.where(cambios < 0, 0)).rolling(10).mean().iloc[-1]
    rsi = 100 - (100 / (1 + (ganancia/perdida))) if perdida > 0 else 50

    # --- 3. SCORE DE CONFIANZA UNIFICADO ---
    # Combinamos Grafos (60%) + RSI/EMA (40%)
    score = (prob_grafo * 0.6) + (40 if rsi < 40 else 10)
    if valor < 1.15: score += 20 # Efecto resorte
    
    # --- 4. FILTROS DE SEGURIDAD (ESCUDO) ---
    # Detección de Succión (Crashes extremos seguidos)
    succion = all(v < 1.25 for v in hist[:2])
    # Detección de Recaudación (Media muy baja)
    media_baja = statistics.mean(hist[:5]) < 1.35

    # --- 5. CÁLCULO DE TARGETS (MÍNIMO 1.50x) ---
    # Retiro Seguro: Basado en mediana adaptativa pero bloqueado en 1.50
    agresividad = 1.15 if rsi < 45 else 0.95
    t_s = round(max(1.50, mediana * 0.85 * agresividad), 2)
    # Ganancia Alta: Basada en el EMA y potencial de rebote
    t_e = round(max(t_s * 1.6, ema5 * 1.2), 2)

    # --- 6. DETERMINACIÓN DE SALIDA FINAL ---
    score_final = min(round(score), 99)
    memoria["confianza"] = f"{score_final}%"
    
    # Radar Rosa
    dist_r = 0
    for v in hist:
        if v >= 10.0: break
        dist_r += 1
    memoria["radar_rosa"] = f"{min(99, dist_r * 3)}%"

    # Lógica de estados
    if succion or media_baja:
        memoria["sugerencia"] = "🛑 NO ENTRAR (SUCCIÓN)"
        memoria["fase"] = "⚠️ RECAUDACIÓN"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"
    elif score_final >= 80:
        memoria["sugerencia"] = "🔥 ENTRADA FUERTE"
        memoria["fase"] = "🚀 EXPANSIÓN"
        memoria["tp_s"] = f"{t_s}x"
        memoria["tp_e"] = f"{t_e}x"
    elif score_final >= 50:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["fase"] = "⚖️ ESTABLE"
        memoria["tp_s"] = "1.50x" # Mínimo estricto
        memoria["tp_e"] = "--"
    else:
        memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
        memoria["fase"] = "📊 ANALIZANDO"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"

    print(f"[{valor}x] Prob:{prob_grafo:.0f}% | RSI:{rsi:.0f} | Sug:{memoria['sugerencia']}")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
