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
    "sugerencia": "⏳ ANALIZANDO GRAFOS",
    "confianza": "0%",
    "radar_rosa": "0%",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "APRENDIENDO",
    "historial_visual": []
}

# IA de Grafos: Analizamos si el patrón termina en EXITO (>=1.50) o FALLO (<1.50)
grafo = collections.defaultdict(lambda: collections.Counter())

def categorizar(v):
    return "OK" if v >= 1.50 else "FAIL"

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
    if len(hist) < 15:
        memoria["sugerencia"] = "📊 RECOLECTANDO..."
        return {"status": "ok"}

    # --- 1. ENTRENAMIENTO DEL GRAFO ---
    for i in range(len(hist) - 4):
        nodo = tuple(categorizar(x) for x in hist[i+1:i+4])
        resultado = categorizar(hist[i])
        grafo[nodo][resultado] += 1

    # --- 2. ANÁLISIS DE MERCADO (SALUD) ---
    # Si la media de los últimos 5 es muy baja, el casino está "succionando"
    media_reciente = statistics.mean(hist[:5])
    
    # --- 3. CONSULTA DE PROBABILIDAD IA ---
    situacion_actual = tuple(categorizar(x) for x in hist[:3])
    posibilidades = grafo[situacion_actual]
    total = sum(posibilidades.values())
    prob_exito = (posibilidades["OK"] / total * 100) if total > 0 else 0

    # --- 4. LÓGICA DE SEGURIDAD EXTREMA ---
    # Si la media es bajísima o hubo dos 1.0x recientes, bajamos confianza a 0
    if media_reciente < 1.35 or (hist[0] < 1.15 and hist[1] < 1.15):
        score_final = 5 # Peligro inminente
    else:
        score_final = prob_exito

    memoria["confianza"] = f"{round(score_final)}%"

    # --- 5. DETERMINACIÓN DE SEÑAL (SUELO 1.50x) ---
    mediana = statistics.median(hist[:25])
    val_s = round(max(1.50, mediana * 0.90), 2)
    val_e = round(max(val_s * 1.8, mediana * 1.6), 2)

    if score_final >= 85 and media_reciente > 1.45:
        # SEÑAL MAESTRA
        memoria["sugerencia"] = "🔥 ENTRADA CONFIRMADA"
        memoria["fase"] = "🚀 ALTA PROBABILIDAD"
        memoria["tp_s"] = f"{val_s}x"
        memoria["tp_e"] = f"{val_e}x"
    elif score_final < 30:
        # AVISO DE PÉRDIDA
        memoria["sugerencia"] = "❌ RIESGO DE PÉRDIDA"
        memoria["fase"] = "⚠️ RECAUDACIÓN"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"
    else:
        # ESTADO NEUTRO
        memoria["sugerencia"] = "⏳ ESPERANDO PATRÓN"
        memoria["fase"] = "⚖️ MERCADO MIXTO"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"

    # Radar Rosa
    dist = 0
    for v in hist:
        if v >= 10.0: break
        dist += 1
    memoria["radar_rosa"] = f"{min(99, dist * 2)}%"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
