import time
import requests
import os
from playwright.sync_api import sync_playwright

# ELIMINAR LETRAS ROJAS DE LOS LOGS
os.environ["NODE_NO_WARNINGS"] = "1"

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    print("🕵️ Scraper V101 - Iniciando monitoreo de alta estabilidad...")
    
    while True: # Bucle de vida infinita
        try:
            with sync_playwright() as p:
                # Conectar al puerto de depuración
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                context = browser.contexts[0]
                
                # Buscar la pestaña del juego (escaneo dinámico)
                page = None
                for p_actual in context.pages:
                    if "aviator" in p_actual.url.lower():
                        page = p_actual
                        break
                
                if not page:
                    print("⏳ Aviator no detectado en Edge. Esperando...")
                    time.sleep(5)
                    continue

                print(f"✅ VÍNCULO RECUPERADO: {page.title()[:15]}")
                ultimo_v = 0.0
                # Selector universal robusto
                sel = ".bubble-multiplier, .app-stats-item, [class*='multiplier']"

                while True: # Bucle de captura continua
                    try:
                        # Buscamos el dato en todos los frames
                        for f in page.frames:
                            el = f.locator(sel).first
                            # Usamos un timeout corto para no trabar el sistema si hay lag
                            if el.count() > 0:
                                t = el.inner_text(timeout=1000).lower().replace('x','').replace(',','.').strip()
                                v = float(t)
                                
                                if v != ultimo_v and v > 0:
                                    # ENVIAR AL SERVIDOR
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    ultimo_v = v
                                    print(f"🎯 DATO CAPTURADO: {v}x")
                                    time.sleep(1) # Esperar a que la burbuja se asiente
                                break
                    except Exception as e:
                        # Si la conexión interna falla, salimos para reconectar
                        if "Target closed" in str(e) or "Browser sent invalid" in str(e):
                            raise Exception("Reconectar")
                    
                    time.sleep(0.3) # Alta frecuencia de escaneo

        except Exception as e:
            print(f"🔄 Reconectando con el puerto 9222... (Motivo: {str(e)[:30]})")
            time.sleep(5)

if __name__ == "__main__":
    run()
