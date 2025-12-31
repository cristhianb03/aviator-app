import time
import requests
from playwright.sync_api import sync_playwright

# CONFIGURACIÓN
URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
# Dirección del motor Chromium de Edge
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    print("🕵️ Scraper vinculado a Microsoft Edge Iniciado...")
    while True:
        try:
            with sync_playwright() as p:
                # Nos conectamos al motor de Edge (Chromium)
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                
                # Accedemos al contexto de Edge
                context = browser.contexts[0]
                
                # Buscamos la pestaña que tiene el juego abierto
                page = None
                for p_actual in context.pages:
                    if "aviator" in p_actual.url.lower() or "1win" in p_actual.url.lower():
                        page = p_actual
                        break
                
                if not page:
                    print("⏳ No veo el Aviator. Asegúrate de tener la pestaña abierta en Edge.")
                    time.sleep(5)
                    continue

                print(f"✅ VÍNCULO ACTIVO CON EDGE: {page.title()[:20]}")
                
                u = None
                # Selector universal para el historial de Spribe
                sel = ".bubble-multiplier, .app-stats-item, [class*='multiplier'], .payout"

                while True:
                    try:
                        # Escaneo de frames del juego
                        for f in page.frames:
                            # Buscamos el elemento más reciente del historial
                            el = f.locator(sel).first
                            if el and el.is_visible():
                                t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                                v = float(t)
                                
                                if v != u:
                                    # Enviar al servidor local de Google Cloud
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    u = v
                                    print(f"🎯 DATO CAPTURADO EN EDGE: {v}x")
                                break # Dato encontrado, salir de los frames
                    except Exception as e:
                        if "Target closed" in str(e):
                            print("❌ Edge se cerró o se perdió la pestaña.")
                            raise Exception("Reconectar")
                    
                    time.sleep(0.4) # Velocidad de captura equilibrada

        except Exception as e:
            print(f"🔄 Error de conexión: {e}. Reintentando en 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    run()
