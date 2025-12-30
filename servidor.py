from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ ANALIZANDO",
    "confianza": "0%",
    "prob_verde": "0%",
    "radar_rosa": "FRÍO",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "ESTABILIZANDO",
    "historial_visual": [] # Guardaremos los últimos 15 para la App
}

@app.get("/data")
async def get_data():
    return memoria

@app.post("/nuevo-resultado")
async def recibir_resultado(res: Resultado):
    valor = res.valor
    memoria["ultimo_valor"] = valor
    
    # Gestionar Historial Visual
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 15:
        memoria["historial_visual"].pop()

    # Lógica de Cálculo (Unificada)
    hist = memoria["historial_visual"]
    if len(hist) < 5:
        memoria["sugerencia"] = f"⏳ CARGANDO {len(hist)}/5"
        return {"status": "ok"}

    mediana = statistics.median(hist)
    azules = 0
    for v in hist:
        if v < 2.0: azules += 1
        else: break

    # Algoritmo de Score
    score = (azules * 22) + (40 if valor < 1.15 else 0)
    score_final = min(round(score), 99)
    
    # Cálculo de Retiros Adaptativos
    agresividad = 1.15 if score_final > 70 else 0.95
    t_s = round(max(1.25, (mediana * 0.82) * agresividad), 2)
    t_e = round(max(t_s * 1.6, (mediana * 1.5) * agresividad), 2)

    # Actualizar Memoria
    memoria["confianza"] = f"{score_final}%"
    memoria["prob_verde"] = f"{min(score_final + 5, 98)}%"
    
    # Radar Rosa
    rondas_sin_rosa = 0
    for v in hist:
        if v < 10.0: rondas_sin_rosa += 1
        else: break
    memoria["radar_rosa"] = "🔥 ALTO" if rondas_sin_rosa > 25 else "❄️ BAJO"

    if score_final >= 75:
        memoria["sugerencia"] = "🔥 ENTRADA CONFIRMADA"
        memoria["tp_s"] = f"{t_s}x"
        memoria["tp_e"] = f"{t_e}x"
        memoria["fase"] = "🚀 MOMENTUM"
    elif score_final >= 40:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["tp_s"] = f"{t_s}x"
        memoria["tp_e"] = "--"
        memoria["fase"] = "⚖️ ESTABLE"
    else:
        memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
        memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
        memoria["fase"] = "📊 RECAUDACIÓN"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
