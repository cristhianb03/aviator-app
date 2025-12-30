from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import statistics
import collections

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Resultado(BaseModel):
    valor: float

memoria = {
    "ultimo_valor": 0.0,
    "sugerencia": "⏳ CALIBRANDO IA",
    "confianza": "0%",
    "radar_rosa": "0%",
    "tp_s": "--",
    "tp_e": "--",
    "fase": "APRENDIENDO",
    "historial_visual": []
}

# Grafo centrado en el objetivo 1.50x
grafo = collections.defaultdict(lambda: collections.Counter())

def categorizar_pro(v):
    if v < 1.20: return "PELIGRO_TOTAL"
    if v < 1.50: return "ZONA_PERDIDA"
    return "EXITO_150"

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
    if len(hist) < 15:
        memoria["sugerencia"] = f"📊 ANALIZANDO ({len(hist)}/15)"
        return {"status": "ok"}

    # --- 1. FILTRO ANTI-VACÍO (ELIMINA FALSOS POSITIVOS) ---
    # Si hubo dos crashes extremos (<1.20) muy recientes, bloqueamos todo.
    extremos_recientes = len([v for v in hist[:3] if v < 1.20])
    
    # --- 2. MOTOR DE GRAFOS ---
    for i in range(len(hist) - 4):
        nodo = tuple(categorizar_pro(x) for x in hist[i+1:i+4])
        resultado = categorizar_pro(hist[i])
        grafo[nodo][resultado] += 1

    situacion_actual = tuple(categorizar_pro(x) for x in hist[:3])
    posibilidades = grafo[situacion_actual]
    total_muestras = sum(posibilidades.values())
    
    # Probabilidad real de éxito para el objetivo 1.50x
    prob_exito = (posibilidades["EXITO_150"] / total_muestras * 100) if total_muestras > 0 else 0

    # --- 3. ANÁLISIS DE TENDENCIA (SALUD DEL MERCADO) ---
    media_corta = statistics.mean(hist[:5])
    
    # --- 4. CÁLCULO DE TARGETS (MÍNIMO 1.50x) ---
    mediana = statistics.median(hist[:20])
    val_s_raw = round(max(1.50, mediana * 0.88), 2)
    val_e_raw = round(max(val_s_raw * 1.8, mediana * 1.6), 2)

    # --- 5. LÓGICA DE DECISIÓN TITANIUM ---
    # CONDICIÓN PARA ENTRADA FUERTE:
    # - Probabilidad de éxito > 80%
    # - NO estar en zona de vacío (extremos_recientes < 2)
    # - La media corta no debe ser un desastre (>1.30)
    
    if extremos_recientes >= 2:
        memoria["sugerencia"] = "🛑 NO ENTRAR (SUCCIÓN)"
        memoria["confianza"] = "1%"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"
        memoria["fase"] = "⚠️ RECAUDACIÓN CRÍTICA"
        
    elif prob_exito >= 80 and media_corta > 1.35:
        memoria["sugerencia"] = "🚀 ENTRADA FUERTE"
        memoria["confianza"] = f"{round(prob_exito)}%"
        memoria["tp_s"] = f"{val_s_raw}x"
        memoria["tp_e"] = f"{val_e_raw}x"
        memoria["fase"] = "🔥 ALTA PROBABILIDAD"
        
    elif prob_exito >= 55:
        memoria["sugerencia"] = "⚠️ POSIBLE SEÑAL"
        memoria["confianza"] = f"{round(prob_exito)}%"
        memoria["tp_s"] = "1.50x" # Forzamos tu mínimo
        memoria["tp_e"] = "--"
        memoria["fase"] = "⚖️ TRANSICIÓN"
        
    else:
        memoria["sugerencia"] = "⏳ ESPERANDO PATRÓN"
        memoria["confianza"] = f"{round(prob_exito)}%"
        memoria["tp_s"] = "--"
        memoria["tp_e"] = "--"
        memoria["fase"] = "📊 RECAUDACIÓN"

    # Radar Rosa Dinámico
    rondas_sin_rosa = 0
    for v in hist:
        if v >= 10.0: break
        rondas_sin_rosa += 1
    memoria["radar_rosa"] = f"{min(99, rondas_sin_rosa * 2)}%"

    print(f"[{valor}x] Prob 1.50: {prob_exito:.1f}% | Extremos: {extremos_recientes}")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
