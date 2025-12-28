import time
import requests
import json
from playwright.sync_api import sync_playwright

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_PORT = "http://localhost:9222"

def run():
    with sync_playwright() as p:
        print("🔗 Conectando al cable de datos (WebSocket)...")
        try:
            browser = p.chromium.connect_over_cdp(DEBUG_PORT)
            context = browser.contexts[0]
            page = context.pages[0]
        except:
            print("❌ Error: Abre Edge en modo debug primero.")
            return

        def on_websocket(ws):
            print(f"📡 WebSocket detectado: {ws.url}")
            
            # Escuchamos cada mensaje que el servidor le manda al juego
            @ws.on("framereceived")
            def on_message(payload):
                try:
                    # En Aviator (Spribe), los mensajes suelen ser strings de texto
                    # que contienen información del juego.
                    if isinstance(payload, str):
                        # Buscamos patrones de "crash" o "finish" en el mensaje
                        # Los datos reales suelen venir como: {"type":"f","val":2.54} o similares
                        if "multiplier" in payload or '"f"' in payload:
                            # Intentamos extraer el número (esto depende de la versión del juego)
                            # Usamos una lógica de limpieza rápida:
                            data = json.loads(payload)
                            
                            # Si el JSON tiene el formato de resultado final:
                            if 'val' in data and data.get('type') == 'f':
                                valor = float(data['val'])
                                print(f"🚀 [WS] DATO CAPTURADO: {valor}x")
                                requests.post(URL_SERVIDOR, json={"valor": valor})
                except:
                    pass

        # Activamos el escucha de WebSockets
        page.on("websocket", on_websocket)

        print("✅ Escucha de red activa. Juega una ronda para empezar a capturar...")
        
        # Ya no necesitamos un bucle 'while True' que busque elementos,
        # pero mantenemos el script vivo.
        while True:
            time.sleep(10)

if __name__ == "__main__":
    run()