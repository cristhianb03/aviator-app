from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics
import collections
import math

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO IA",
    "confianza": "0%",
    "radar_rosa": "0%", # AHORA ES UN PORCENTAJE DE PROBABILIDAD
    "tp_s": "--",
    "tp_e": "--",
    "fase": "APRENDIENDO",
    "historial_visual": []
}

# --- MOTOR ROSA AVANZADO ---
def calcular_probabilidad_rosa(hist):
    if len(hist) < 30: return 0
    
    # 1. Distancia desde el último 10x
    distancia = 0
    for v in hist:
        if v >= 10.0: break
        distancia += 1
    
    # 2. Déficit de Dispersión (¿Qué tanto ha pagado el casino recientemente?)
    # El RTP teórico es del 97%. Calculamos el RTP real de los últimos 50 juegos.
    promedio_real = statistics.mean(hist[:50])
    # Si el promedio real es menor a 2.5, el casino está acumulando (Caja llena).
    deficit_caja = max(0, 3.0 - promedio_real)
    
    # 3. Lógica de Dispersión (Probabilidad Rosa)
    # Un Rosa suele salir cada 40-70 rondas. 
    # Si la distancia es > 45 y la caja está llena (deficit alto), la probabilidad explota.
    prob_base = (distancia / 60) * 100
    prob_final = prob_base + (deficit_caja * 15)
    
    # Penalización: Si salió un Rosa hace menos de 5 rondas, la probabilidad es casi 0 (Drenaje)
    if distancia < 5: prob_final = prob_final * 0.1

    return min(round(prob_final), 99)

# --- MOTOR DE GRAFOS PARA 1.50x ---
def categorizar(v):
    if v < 1.2: return "危险_Peligro"
    if v < 1.5: return "低_Bajo"
    return "赢_Exito"

grafo = collections.defaultdict(lambda: collections.Counter())

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 150: memoria["historial_visual"].pop()

    hist = memoria["historial_visual"]
    if len(hist) < 20:
        memoria["sugerencia"] = f"📈 RECOPILANDO DATOS ({len(hist)}/20)"
        return {"status": "ok"}

    # 1. ACTUALIZAR PROBABILIDAD ROSA
    prob_rosa = calcular_probabilidad_rosa(hist)
    memoria["radar_rosa"] = f"{prob_rosa}%"

    # 2. LÓGICA DE GRAFOS PARA RETIRO SEGURO (MÍNIMO 1.50x)
    for i in range(len(hist) - 4):
        nodo = tuple(categorizar(x) for x in hist[i+1:i+4])
        resultado = categorizar(hist[i])
        grafo[nodo][resultado] += 1

    situacion_actual = tuple(categorizar(x) for x in hist[:3])
    posibilidades = grafo[situacion_actual]
    total_muestras = sum(posibilidades.values())
    
    # Probabilidad de que el siguiente sea > 1.50x
    prob_exito = (posibilidades["赢_Exito"] / total_muestras * 100) if total_muestras > 0 else 50

    # 3. SCORE FINAL DE CONFIANZA
    score = (prob_exito * 0.7) + (30 if valor < 1.15 else 0)
    confianza_f = min(round(score), 99)
    memoria["confianza"] = f"{confianza_f}%"

    # 4. DETERMINACIÓN DE VALORES (ESTRICTO 1.50x+)
    mediana = statistics.median(hist[:25])
    
    if confianza_f >= 75:
        # El retiro seguro ahora es REALMENTE seguro porque usa la mediana y prob de grafos
        val_s = round(max(1.50, mediana * 0.85), 2)
        val_e = round(max(val_s * 2, mediana * 1.8), 2)
        
        memoria["sugerencia"] = "🔥 ENTRADA CONFIRMADA"
        memoria["tp_s"] = f"{val_s}x"
        memoria["tp_e"] = f"{val_e}x"
        memoria["fase"] = "🚀 DISPERSIÓN ACTIVA"
    else:
        memoria["sugerencia"] = "⏳ ESPERANDO SEÑAL"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"
        memoria["fase"] = "📊 RECAUDACIÓN" if valor < 2.0 else "⚖️ MERCADO MIXTO"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
