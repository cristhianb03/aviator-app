from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics

app = FastAPI()

# PERMITIR CONEXIÓN DESDE GITHUB (IMPORTANTE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Resultado(BaseModel):
    valor: float

# Estructura sincronizada con el Index
memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ ANALIZANDO",
    "confianza": "0%",
    "prob_verde": "0%",
    "radar_rosa": "FRÍO",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "INICIALIZANDO",
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
        memoria["sugerencia"] = f"⏳ RECOLECTANDO ({len(hist)}/5)"
        return {"status": "ok"}

    # --- LÓGICA DE CÁLCULO ---
    recientes = hist[-10:]
    mediana = statistics.median(hist)
    
    # Racha de azules
    azules = 0
    for v in reversed(hist):
        if v < 2.0: azules += 1
        else: break
    
    # Score de Confianza
    score = (azules * 20) + (35 if valor < 1.15 else 0)
    score_final = min(round(score), 99)
    
    # Radar Rosa (>10x)
    rosa_count = 0
    for v in reversed(hist):
        if v < 10.0: rosa_count += 1
        else: break
    
    # --- ASIGNACIÓN DE MEMORIA ---
    memoria["confianza"] = f"{score_final}%"
    memoria["prob_verde"] = f"{min(score_final + 10, 98)}%"
    memoria["radar_rosa"] = "🔥 ALTO" if rosa_count > 30 else "❄️ BAJO"
    
    t_s = round(max(1.28, mediana * 0.82), 2)
    t_e = round(max(t_s * 1.5, mediana * 1.4), 2)

    if score_final >= 75:
        memoria["sugerencia"] = "🔥 ENTRADA FUERTE"
        memoria["tp_s"] = f"{t_s}x"
        memoria["tp_e"] = f"{t_e}x"
        memoria["fase"] = "🚀 SALTO"
    elif score_final >= 40:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["tp_s"] = f"{t_s}x"
        memoria["tp_e"] = "--"
        memoria["fase"] = "⚖️ ESTABLE"
    else:
        memoria["sugerencia"] = "⏳ BUSCANDO PATRÓN"
        memoria["tp_s"] = "--"; memoria["tp_e"] = "--"
        memoria["fase"] = "📊 RECAUDACIÓN"

    print(f"🎯 Capturado: {valor}x | Confianza: {score_final}%")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
