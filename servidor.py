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

# IA de Grafos: Solo éxito si >= 1.50
grafo = collections.defaultdict(lambda: collections.Counter())

def categorizar(v):
    return "EXITO" if v >= 1.50 else "FALLO"

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
        memoria["sugerencia"] = "📊 CARGANDO..."
        return {"status": "ok"}

    # --- 1. ENTRENAMIENTO DEL GRAFO ---
    for i in range(len(hist) - 4):
        nodo = tuple(categorizar(x) for x in hist[i+1:i+4])
        resultado = categorizar(hist[i])
        grafo[nodo][resultado] += 1

    # --- 2. ANÁLISIS DE MOMENTUM (PARA ATRAPAR EL 40x) ---
    rondas_sin_rosa = 0
    for v in hist:
        if v >= 10.0: break
        rondas_sin_rosa += 1
    
    # Si llevamos mucho tiempo sin un rosa, la presión de explosión sube
    presion_explosion = min(99, rondas_sin_rosa * 2.5)
    memoria["radar_rosa"] = f"{round(presion_explosion)}%"

    # --- 3. CONSULTA DE PROBABILIDAD IA ---
    situacion_actual = tuple(categorizar(x) for x in hist[:3])
    posibilidades = grafo[situacion_actual]
    total = sum(posibilidades.values())
    prob_exito_150 = (posibilidades["EXITO"] / total * 100) if total > 0 else 0

    # --- 4. CÁLCULO DE TARGETS CON SUELO 1.50x ---
    mediana = statistics.median(hist[:20])
    
    # Filtro estricto: El Retiro Seguro NUNCA será menor a 1.50
    val_s = round(max(1.50, mediana * 0.92), 2)
    
    # Ganancia alta agresiva si el radar rosa está caliente
    if presion_explosion > 70:
        val_e = round(max(5.00, mediana * 3.0), 2)
        memoria["fase"] = "🚀 BUSCANDO ROSA"
    else:
        val_e = round(max(val_s * 2.1, 3.00), 2)
        memoria["fase"] = "⚖️ ESTABLE"

    # --- 5. LÓGICA DE SEGURIDAD (CUÁNDO MOSTRAR) ---
    # Si la probabilidad de llegar a 1.50 es baja (< 55%) o hay succión extrema
    if prob_exito_150 < 55 or (hist[0] < 1.20 and hist[1] < 1.20):
        memoria["sugerencia"] = "❌ RIESGO DE PÉRDIDA"
        memoria["confianza"] = f"{round(prob_exito_150)}%"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"
    else:
        # SEÑAL VÁLIDA
        memoria["sugerencia"] = "🔥 ENTRADA FUERTE" if prob_exito_150 > 75 else "⚠️ POSIBLE SEÑAL"
        memoria["confianza"] = f"{round(prob_exito_150)}%"
        memoria["tp_s"] = f"{val_s}x"
        memoria["tp_e"] = f"{val_e}x"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
