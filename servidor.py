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
    "sugerencia": "⏳ ESCANEANDO",
    "confianza": "0%",
    "tp_s": "--", "tp_b": "--", "tp_g": "--", "tp_n": "--",
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
    if len(memoria["historial"]) > 30: memoria["historial"].pop(0)
    
    # ... (Aquí va tu lógica de cálculo que ya teníamos) ...
    # Por ahora, una lógica simple para que veas datos:
    memoria["sugerencia"] = "✅ DATOS RECIBIDOS"
    memoria["tp_s"] = "1.30x"
    
    print(f"🎯 Recibido desde el Scraper: {valor}x")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
