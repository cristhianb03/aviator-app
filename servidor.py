from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics
import math

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

# Memoria de la IA
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO",
    "confianza": "0%",
    "fase": "APRENDIENDO",
    "tp_s": "--",
    "tp_e": "--",
    "historial_visual": []
}

def calcular_probabilidad_ia(hist):
    if len(hist) < 10: return 0, 1.30, 2.00
    
    # 1. ANALIZADOR DE PATRONES (PATTERN MATCHING)
    # Comparamos la secuencia actual de 3 con el historial de 100
    secuencia_actual = [1 if x >= 2.0 else 0 for x in hist[:3]] # 1=verde, 0=azul
    coincidencias = 0
    exitos_verde = 0
    
    for i in range(1, len(hist) - 3):
        ventana = [1 if x >= 2.0 else 0 for x in hist[i:i+3]]
        if ventana == secuencia_actual:
            coincidencias += 1
            if hist[i-1] >= 2.0: exitos_verde += 1
            
    # Probabilidad basada en patrones pasados
    prob_patron = (exitos_verde / coincidencias) if coincidencias > 0 else 0.5

    # 2. MÉTRICA DE VOLATILIDAD (RIESGO)
    desviacion = statistics.stdev(hist[:15]) if len(hist) >= 15 else 1.0
    mediana = statistics.median(hist[:30])

    # 3. SCORE FINAL (Fusión de racha + patrones + volatilidad)
    azules = 0
    for v in hist:
        if v < 2.0: azules += 1
        else: break
        
    score = (prob_patron * 50) + (azules * 15)
    if hist[0] < 1.10: score += 30 # Efecto Resorte
    
    # Penalización por seguridad (ZONA DE VACÍO)
    if all(v < 1.25 for v in hist[:2]): score = score * 0.5 

    # 4. CÁLCULO DE TARGETS INTELIGENTES
    # El retiro seguro ya no es fijo. Se ajusta a la mediana y a la confianza.
    buffer_seguridad = 0.92 if desviacion > 2.0 else 0.96
    
    # Si la IA tiene mucha confianza, sube el target
    t_seguro = round(mediana * 0.85 * buffer_seguridad * (1.1 if score > 80 else 1.0), 2)
    t_explosivo = round(mediana * 1.5 * buffer_seguridad * (1.2 if score > 80 else 1.0), 2)

    # Forzar el 1.50x que pediste si las condiciones son óptimas
    if score > 85 and mediana > 1.8: t_seguro = 1.50

    return min(score, 99), t_seguro, t_explosivo

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
    if len(hist) < 10:
        memoria["sugerencia"] = f"⏳ IA RECOLECTANDO ({len(hist)}/10)"
        return {"status": "ok"}

    # EJECUTAR MOTOR DE IA
    score, ts, te = calcular_probabilidad_ia(hist)
    
    memoria["confianza"] = f"{round(score)}%"
    
    # Determinar Sugerencia
    if score >= 80:
        memoria["sugerencia"] = "🚀 ENTRADA IA CONFIRMADA"
        memoria["fase"] = "🔥 ALTA PROBABILIDAD"
        memoria["tp_s"] = f"{ts}x"
        memoria["tp_e"] = f"{te}x"
    elif score >= 50:
        memoria["sugerencia"] = "⚠️ SEÑAL MODERADA"
        memoria["fase"] = "⚖️ ESTABLE"
        memoria["tp_s"] = f"{ts}x"
        memoria["tp_e"] = "--"
    else:
        memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
        memoria["fase"] = "📊 RECAUDACIÓN"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
