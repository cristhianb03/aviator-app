from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics

app = FastAPI()

# PERMITIR CONEXIÓN DESDE GITHUB
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Resultado(BaseModel):
    valor: float

# MEMORIA MAESTRA SINCRONIZADA
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

    print(f"🎯 Recibido: {valor}x")

    hist = memoria["historial"]
    if len(hist) < 5: return {"status": "ok"}

    # --- LÓGICA DE CÁLCULO ---
    mediana = statistics.median(hist)
    azules = 0
    for v in reversed(hist):
        if v < 2.0: azules += 1
        else: break

    # SCORE
    score = (azules * 25) + (35 if valor < 1.2 else 0)
    score_final = min(round(score), 99)
    memoria["confianza"] = f"{score_final}%"

    # TARGETS DINÁMICOS
    t_s = round(max(1.25, mediana * 0.85), 2)
    t_e = round(max(t_s * 1.5, mediana * 1.4), 2)

    # ESTADOS
    if score_final >= 75:
        memoria["sugerencia"] = "🔥 ENTRADA CONFIRMADA"
        memoria["tp_seguro"] = f"{t_s}x"
        memoria["tp_explosivo"] = f"{t_e}x"
    elif score_final >= 40:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["tp_seguro"] = f"{t_s}x"
        memoria["tp_explosivo"] = "--"
    else:
        memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
        memoria["tp_seguro"] = "--"
        memoria["tp_explosivo"] = "--"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
