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
    "radar_rosa": "BAJO",
    "fase": "ESTABILIZANDO",
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
    memoria["historial_visual"].insert(0, valor)
    if len(memoria["historial_visual"]) > 50: memoria["historial_visual"].pop()

    hist = [v for v in memoria["historial_visual"] if v > 0]
    if len(hist) < 10:
        memoria["sugerencia"] = "⏳ RECOLECTANDO DATOS"
        return {"status": "ok"}

    # --- MOTOR DE SEGURIDAD "BLACK ARMOR" ---
    
    # 1. Detectar "Zona de Vacío" (Crashes inmediatos)
    # Si los últimos 2 fueron < 1.20, NO ENTRAR bajo ninguna circunstancia.
    if hist[0] < 1.20 and hist[1] < 1.20:
        memoria["sugerencia"] = "🛑 ZONA DE RIESGO"
        memoria["fase"] = "⚠️ RECAUDACIÓN"
        memoria["confianza"] = "5%"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"
        return {"status": "ok"}

    # 2. Análisis de Mediana y Volatilidad
    mediana_reciente = statistics.median(hist[:15])
    
    # 3. Cálculo de Score (Probabilidad de rebote)
    azules = len([v for v in hist[:6] if v < 2.0])
    score = (azules * 20)
    
    # Bono por "Déficit de Pago"
    if mediana_reciente < 1.60: score += 30 # El casino está debiendo verdes

    # --- CÁLCULO DE TARGETS EXTREMADAMENTE ASERTIVOS ---
    # Para que el 1.50x sea "seguro", la mediana debe estar sana (>1.80)
    if mediana_reciente > 1.80:
        val_s = 1.50 # Tu objetivo solicitado
    else:
        val_s = round(mediana_reciente * 0.85, 2)
        val_s = max(1.25, val_s) # Mínimo absoluto de seguridad

    # Ganancia Alta (Ahora más conservadora para no fallar)
    val_e = round(val_s * 1.6, 2)

    # --- DETERMINACIÓN DE SALIDA ---
    confianza_num = min(score, 99)
    memoria["confianza"] = f"{confianza_num}%"

    # Solo activamos señales si la confianza es muy alta
    if confianza_num >= 80:
        memoria["sugerencia"] = "🔥 ENTRADA FUERTE"
        memoria["fase"] = "🚀 COMPENSACIÓN"
        memoria["tp_s"] = f"{val_s}x"
        memoria["tp_e"] = f"{val_e}x"
    elif confianza_num >= 50:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["fase"] = "⚖️ ESTABLE"
        memoria["tp_s"] = f"{val_s}x"
        memoria["tp_e"] = "--"
    else:
        memoria["sugerencia"] = "⏳ ESPERANDO PATRÓN"
        memoria["fase"] = "📊 ANALIZANDO"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
