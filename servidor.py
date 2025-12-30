from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

# DICCIONARIO MAESTRO: Estos nombres deben ser IGUALES en el HTML
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ ANALIZANDO",
    "confianza": "0%",
    "radar_rosa": "❄️ BAJO",
    "fase": "ESCANEO",
    "tp_s": "--",
    "tp_e": "--",
    "historial_visual": [0.0]
}

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    
    # Historial para burbujas
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15:
        memoria["historial_visual"].pop()

    hist = [v for v in memoria["historial_visual"] if v > 0]
    if len(hist) < 3:
        memoria["sugerencia"] = "⏳ RECOLECTANDO"
        return {"status": "ok"}

    # LÓGICA DE CÁLCULO
    mediana = statistics.median(hist)
    azules = 0
    for v in hist:
        if v < 2.0: azules += 1
        else: break

    # Confianza y Radar
    score = (azules * 22) + (40 if valor < 1.15 else 0)
    score_final = min(round(score), 99)
    memoria["confianza"] = f"{score_final}%"
    
    rondas_sin_rosa = 0
    for v in hist:
        if v < 10.0: rondas_sin_rosa += 1
        else: break
    memoria["radar_rosa"] = "🔥 ALTO" if rondas_sin_rosa > 20 else "❄️ BAJO"

    # Targets
    agresividad = 1.15 if score_final > 70 else 0.95
    val_s = round(max(1.25, (mediana * 0.82) * agresividad), 2)
    val_e = round(max(val_s * 1.6, (mediana * 1.5) * agresividad), 2)

    # Estados
    if score_final >= 75:
        memoria["sugerencia"] = "🔥 ENTRADA CONFIRMADA"
        memoria["fase"] = "🚀 MOMENTUM"
        memoria["tp_s"] = f"{val_s}x"
        memoria["tp_e"] = f"{val_e}x"
    elif score_final >= 40:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["fase"] = "⚖️ ESTABLE"
        memoria["tp_s"] = f"{val_s}x"
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
