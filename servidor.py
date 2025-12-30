from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

# MEMORIA MAESTRA UNIFICADA
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ ANALIZANDO",
    "confianza": "0%",
    "fase": "ESCANEO",
    "tp_seguro": "--",
    "tp_explosivo": "--",
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
    if len(memoria["historial"]) > 50: memoria["historial"].pop(0)

    hist = memoria["historial"]
    if len(hist) < 5: 
        memoria["sugerencia"] = "⏳ RECOLECTANDO"
        return {"status": "ok"}

    # --- MOTOR ESTADÍSTICO ---
    recientes = hist[-10:]
    mediana = statistics.median(hist)
    verdes_ratio = len([v for v in recientes if v >= 2.0]) / 10
    
    azules_seguidos = 0
    for v in reversed(hist):
        if v < 2.0: azules_seguidos += 1
        else: break

    # --- DETERMINACIÓN DE FASE Y SCORE ---
    score = 0
    if verdes_ratio >= 0.6:
        memoria["fase"] = "🚀 EXPANSIÓN"
        score = 85 + (verdes_ratio * 10)
        agresividad = 1.2
    elif azules_seguidos >= 2:
        memoria["fase"] = "🔄 REBOTE"
        score = (azules_seguidos * 25) + (30 if valor < 1.15 else 0)
        agresividad = 0.95
    else:
        memoria["fase"] = "⚖️ ESTABLE"
        score = 40 + (verdes_ratio * 30)
        agresividad = 0.9

    # --- CÁLCULO DE TARGETS (SOLO DOS) ---
    buffer = 0.94 # Seguridad del 6%
    t_seguro = round(max(1.25, (mediana * 0.85) * agresividad * buffer), 2)
    t_explosivo = round(max(t_seguro * 1.5, (mediana * 1.5) * agresividad * buffer), 2)

    # --- ACTUALIZACIÓN DE MEMORIA ---
    score_final = min(round(score), 99)
    memoria["confianza"] = f"{score_final}%"
    
    if score_final >= 75:
        memoria["sugerencia"] = "🔥 ENTRADA CONFIRMADA"
        memoria["tp_seguro"] = f"{t_seguro}x"
        memoria["tp_explosivo"] = f"{t_explosivo}x"
    elif score_final >= 40:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["tp_seguro"] = f"{t_seguro}x"
        memoria["tp_explosivo"] = "--"
    else:
        memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
        memoria["tp_seguro"] = "--"
        memoria["tp_explosivo"] = "--"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
