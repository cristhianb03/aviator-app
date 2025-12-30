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
    "prob_verde": "0%", # NUEVO: Probabilidad de que el siguiente sea > 2.0x
    "radar_rosa": "FRÍO", # NUEVO: Estado del premio rosa (>10x)
    "tp_seguro": "--",
    "tp_explosivo": "--",
    "fase": "CALIBRANDO",
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
    if len(memoria["historial"]) > 100: memoria["historial"].pop(0)

    hist = memoria["historial"]
    if len(hist) < 10: 
        memoria["sugerencia"] = "⏳ RECOLECTANDO DATOS"
        return {"status": "ok"}

    # --- MOTOR DE PREDICCIÓN DE SALTO (SIGUIENTE VALOR ALTO) ---
    
    # 1. Análisis de Deuda (Déficit de Verdes)
    # Si han salido muchos azules seguidos, la probabilidad de verde sube.
    recientes = hist[-10:]
    azules_seguidos = 0
    for v in reversed(hist):
        if v < 2.0: azules_seguidos += 1
        else: break
    
    # Probabilidad base de verde (basada en el promedio de los últimos 10)
    # Si solo el 20% han sido verdes, la probabilidad del siguiente sube por compensación.
    verdes_en_ventana = len([v for v in recientes if v >= 2.0])
    prob_v = (azules_seguidos * 15) + (50 - (verdes_en_ventana * 5))
    if valor < 1.15: prob_v += 30 # Efecto resorte
    
    memoria["prob_verde"] = f"{min(max(prob_v, 10), 98)}%"

    # 2. Radar de Rosa (Premios > 10x)
    # Contamos cuántas rondas han pasado desde el último 10x
    rondas_sin_rosa = 0
    for v in reversed(hist):
        if v < 10.0: rondas_sin_rosa += 1
        else: break
    
    if rondas_sin_rosa > 35: memoria["radar_rosa"] = "🔥 MUY ALTO"
    elif rondas_sin_rosa > 20: memoria["radar_rosa"] = "⚠️ MEDIO"
    else: memoria["radar_rosa"] = "❄️ BAJO"

    # --- 3. CÁLCULO DE TARGETS (Ajustados por el Score de Salto) ---
    mediana = statistics.median(hist[-20:])
    
    # Si la probabilidad de verde es alta (>70%), somos más valientes con los números
    agresividad = 1.15 if prob_v > 70 else 0.95
    
    t_s = round(max(1.28, (mediana * 0.82) * agresividad), 2)
    
    # El explosivo ahora es inteligente: si el radar rosa está caliente, sugiere un valor alto
    if memoria["radar_rosa"] == "🔥 MUY ALTO":
        t_e = round(max(5.00, mediana * 3.5), 2)
    else:
        t_e = round(max(t_s * 1.5, mediana * 1.3), 2)

    # --- 4. ACTUALIZACIÓN DE ESTADOS ---
    score_final = prob_v
    memoria["confianza"] = f"{min(score_final, 99)}%"

    if score_final >= 80:
        memoria["sugerencia"] = "🔥 ENTRADA FUERTE"
        memoria["tp_seguro"] = f"{t_s}x"
        memoria["tp_explosivo"] = f"{t_e}x"
        memoria["fase"] = "🚀 SALTO INMINENTE"
    elif score_final >= 50:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["tp_seguro"] = f"{t_s}x"
        memoria["tp_explosivo"] = "--"
        memoria["fase"] = "⚖️ MERCADO ESTABLE"
    else:
        memoria["sugerencia"] = "⏳ ESPERANDO PATRÓN"
        memoria["tp_seguro"] = "--"
        memoria["tp_explosivo"] = "--"
        memoria["fase"] = "📊 RECAUDACIÓN"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
