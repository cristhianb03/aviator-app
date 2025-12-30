from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics
import csv
import os
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

# Estructura Maestra - Nombres sincronizados con el HTML
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ ANALIZANDO",
    "confianza": "0%",
    "radar_rosa": "BAJO",
    "fase": "ESTABLE",
    "tp_s": "--",
    "tp_e": "--",
    "historial_visual": []
}

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    
    # Actualizar historial
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 100: memoria["historial_visual"].pop()
    
    # Guardar en CSV para memoria a largo plazo
    with open('base_datos_v29.csv', mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime("%H:%M:%S"), valor])

    hist = [v for v in memoria["historial_visual"] if v > 0]
    if len(hist) < 10:
        memoria["sugerencia"] = f"⏳ CARGANDO ({len(hist)}/10)"
        return {"status": "ok"}

    # --- MOTOR DE INTELIGENCIA AVANZADA ---
    
    # 1. Medición de Riesgo (Volatilidad)
    volatilidad = statistics.stdev(hist[:10])
    mediana = statistics.median(hist[:20])
    
    # 2. Análisis de "Déficit" (Presión de Pago)
    recientes = hist[:6]
    azules = len([v for v in recientes if v < 2.0])
    
    # 3. SCORE DE CONFIANZA (Efecto Resorte + Momentum)
    score = (azules * 15) 
    if valor < 1.15: score += 40 # Bono por crash bajo
    if any(v > 10.0 for v in hist[:5]): score -= 30 # Penalizar tras un Rosa reciente

    # 4. CÁLCULO DE TARGETS DINÁMICOS (BUFFER DE SEGURIDAD)
    # Si la volatilidad es alta, bajamos el target para no fallar
    buffer = 0.95 if volatilidad < 2.0 else 0.88
    
    # Scalping: Punto de retorno del 90% de probabilidad
    val_s = round(max(1.25, (mediana * 0.82) * buffer), 2)
    # Explosivo: Punto de retorno del 60% de probabilidad
    val_e = round(max(val_s * 1.5, (mediana * 1.4) * buffer), 2)

    # --- DETERMINACIÓN DE FASES ---
    score_final = min(max(score, 5), 99)
    memoria["confianza"] = f"{score_final}%"
    
    # Radar Rosa
    rondas_sin_rosa = 0
    for v in hist:
        if v < 10.0: rondas_sin_rosa += 1
        else: break
    memoria["radar_rosa"] = "ALTO 🔥" if rondas_sin_rosa > 30 else "BAJO ❄️"

    # Sugerencia Final
    if score_final >= 75:
        memoria["sugerencia"] = "🔥 ENTRADA FUERTE"
        memoria["fase"] = "🚀 RECUPERACIÓN"
        memoria["tp_s"] = f"{val_s}x"
        memoria["tp_e"] = f"{val_e}x"
    elif score_final >= 45:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["fase"] = "⚖️ ESTABLE"
        memoria["tp_s"] = f"{val_s}x"
        memoria["tp_e"] = "--"
    else:
        memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
        memoria["fase"] = "📊 RECAUDACIÓN"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"

    print(f"[{valor}x] Score: {score_final}% | Sugerencia: {memoria['sugerencia']}")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
