from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

# MEMORIA DE ALTA CAPACIDAD (100 registros)
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO",
    "confianza": "0%",
    "tp_seguro": "--",
    "tp_explosivo": "--",
    "fase": "ANALIZANDO",
    "historial": []
}

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    memoria["historial"].append(valor)
    
    # Mantenemos 100 valores para una base estadística de alta precisión
    if len(memoria["historial"]) > 100: 
        memoria["historial"].pop(0)

    hist = memoria["historial"]
    if len(hist) < 15: 
        memoria["sugerencia"] = f"⏳ RECOLECTANDO ({len(hist)}/15)"
        return {"status": "ok"}

    # --- MOTOR ESTADÍSTICO Engine X ---
    
    # 1. Análisis de Ventanas (Corto vs Largo Plazo)
    ventana_corta = hist[-5:]   # Lo que está pasando YA
    ventana_media = hist[-20:]  # La tendencia del ciclo
    ventana_larga = hist        # El comportamiento del día
    
    media_corta = statistics.mean(ventana_corta)
    media_larga = statistics.mean(ventana_larga)
    mediana_media = statistics.median(ventana_media)
    
    # 2. Medición de Volatilidad (Riesgo real)
    # Si la desviación es alta, el avión es impredecible.
    desviacion = statistics.stdev(ventana_media)

    # 3. Índice de Presión (IPP)
    # Si el IPP es > 1, el casino está recaudando. Si es < 1, está pagando.
    ipp = media_larga / media_corta if media_corta > 0 else 1

    # 4. Lógica de Rachas de Supervivencia
    azules = 0
    for v in reversed(hist):
        if v < 2.0: azules += 1
        else: break

    # --- CÁLCULO DE TARGETS DINÁMICOS ---
    # Usamos un buffer de seguridad que crece si la volatilidad es alta
    # Si el juego está muy inestable, el buffer quita más valor para asegurar.
    buffer_seguridad = 0.95 - (desviacion * 0.01)
    buffer_seguridad = max(0.80, min(buffer_seguridad, 0.96))

    # Seguro: Basado en la estabilidad de la mediana reciente
    t_s = round(mediana_media * 0.85 * buffer_seguridad, 2)
    
    # Explosivo: Basado en la recuperación del IPP
    # Si hay mucha presión (muchos azules), el explosivo busca el rebote a la media larga
    t_e = round(media_larga * 0.90 * (1.1 if ipp > 1.5 else 1.0), 2)

    # --- DETERMINACIÓN DE FASE Y SCORE ---
    score = (azules * 20) + (ipp * 15)
    if valor < 1.10: score += 40 # Bono de resorte crítico

    if media_corta > media_larga:
        memoria["fase"] = "🚀 EXPANSIÓN ACTIVA"
        score += 20
    elif ipp > 1.8:
        memoria["fase"] = "⚡ ALTA TENSIÓN (REBOTE INMINENTE)"
    else:
        memoria["fase"] = "📊 ESTABILIDAD"

    # --- SALIDA FINAL SINCRONIZADA ---
    score_final = min(round(score), 99)
    memoria["confianza"] = f"{score_final}%"

    if score_final >= 80:
        memoria["sugerencia"] = "🔥 ENTRADA FUERTE"
        memoria["tp_seguro"] = f"{max(1.25, t_s)}x"
        memoria["tp_explosivo"] = f"{max(t_s + 0.5, t_e)}x"
    elif score_final >= 45:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["tp_seguro"] = f"{max(1.20, t_s)}x"
        memoria["tp_explosivo"] = "--"
    else:
        memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
        memoria["tp_seguro"] = "--"
        memoria["tp_explosivo"] = "--"

    print(f"[{valor}x] IPP: {ipp:.2f} | Volatilidad: {desviacion:.2f} | Score: {score_final}%")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
