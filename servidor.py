from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics
import collections

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO IA",
    "confianza": "0%",
    "radar_rosa": "0%",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "APRENDIENDO",
    "historial_visual": []
}

# --- MOTOR DE GRAFOS V33 ---
# Categoría 0: < 1.50 (Pérdida para tu objetivo)
# Categoría 1: >= 1.50 (Éxito para tu objetivo)
def categorizar_estricto(v):
    return "EXITO" if v >= 1.50 else "FALLO"

grafo = collections.defaultdict(lambda: collections.Counter())

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 200: memoria["historial_visual"].pop()

    hist = memoria["historial_visual"]
    if len(hist) < 20:
        memoria["sugerencia"] = f"📊 RECOLECTANDO ({len(hist)}/20)"
        return {"status": "ok"}

    # 1. ACTUALIZAR MAPA DE GRAFOS
    for i in range(len(hist) - 4):
        # Nodo: Secuencia de 3 resultados previos
        nodo = tuple(categorizar_estricto(x) for x in hist[i+1:i+4])
        resultado = categorizar_estricto(hist[i])
        grafo[nodo][resultado] += 1

    # 2. CONSULTAR ESTADO ACTUAL
    situacion_actual = tuple(categorizar_estricto(x) for x in hist[:3])
    posibilidades = grafo[situacion_actual]
    total_muestras = sum(posibilidades.values())
    
    # Probabilidad real de superar 1.50x basada en el historial
    prob_exito = (posibilidades["EXITO"] / total_muestras * 100) if total_muestras > 0 else 0

    # 3. FILTRO DE VOLATILIDAD (FILTRO DE SEGURIDAD)
    # Si los últimos 10 juegos tienen un promedio muy bajo, el mercado está en "Recaudación"
    media_reciente = statistics.mean(hist[:10])
    
    # 4. CALCULO DE RADAR ROSA (Basado en déficit)
    distancia_rosa = 0
    for v in hist:
        if v >= 10.0: break
        distancia_rosa += 1
    prob_rosa = min(99, (distancia_rosa * 1.5) + (20 if media_reciente < 2.0 else 0))
    memoria["radar_rosa"] = f"{round(prob_rosa)}%"

    # --- LÓGICA DE SEÑAL DE ALTA ASERTIVIDAD ---
    # Solo damos señal si la confianza del GRAFO es > 75% Y la media reciente no es crítica
    if prob_exito >= 78 and media_reciente > 1.30:
        # Calculamos el Retiro Seguro (Mínimo 1.50x)
        mediana = statistics.median(hist[:20])
        val_s = round(max(1.50, mediana * 0.85), 2)
        val_e = round(max(val_s * 2.1, mediana * 1.8), 2)

        memoria["sugerencia"] = "🔥 ENTRADA FUERTE"
        memoria["confianza"] = f"{round(prob_exito)}%"
        memoria["tp_s"] = f"{val_s}x"
        memoria["tp_e"] = f"{val_e}x"
        memoria["fase"] = "🚀 NODO DE ÉXITO"
    
    # Si hay tendencia pero no llega al 78% de seguridad
    elif prob_exito >= 50:
        memoria["sugerencia"] = "⏳ ESPERANDO CONFIRMACIÓN"
        memoria["confianza"] = f"{round(prob_exito)}%"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"
        memoria["fase"] = "⚖️ TRANSICIÓN"
    
    else:
        # BLOQUEO DE SEGURIDAD
        memoria["sugerencia"] = "🛑 NO ENTRAR"
        memoria["confianza"] = f"{round(prob_exito)}%"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"
        memoria["fase"] = "⚠️ RECAUDACIÓN"

    print(f"[{valor}x] Prob 1.50x: {prob_exito:.1f}% | Fase: {memoria['fase']}")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
