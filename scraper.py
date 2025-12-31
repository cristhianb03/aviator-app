import time
import requests
from playwright.sync_api import sync_playwright

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    print("🚀 LANZANDO OJO RESILIENTE V100...")
    while True:
        try:
            with sync_playwright() as p:
                # Intentamos conectar al puerto 9222
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                context = browser.contexts[0]
                
                # Buscador inteligente de pestaña activa
                page = None
                for p_actual in context.pages:
                    if "aviator" in p_actual.url.lower():
                        page = p_actual
                        break
                
                if not page:
                    print("⏳ Esperando a que abras Aviator en Edge...")
                    time.sleep(5)
                    continue

                print(f"✅ CONECTADO A: {page.title()[:15]}")
                ultimo_v = 0.0
                sel = ".bubble-multiplier, .app-stats-item, [class*='multiplier']"

                while True:
                    # VERIFICACIÓN CRÍTICA: ¿La página sigue abierta?
                    if page.is_closed():
                        print("❌ La pestaña se cerró.")
                        break

                    try:
                        for f in page.frames:
                            # Usamos un selector con timeout corto para no trabar el bucle
                            el = f.locator(sel).first
                            if el and el.count() > 0:
                                t = el.inner_text(timeout=500).lower().replace('x','').replace(',','.').strip()
                                v = float(t)
                                
                                if v != ultimo_v and v > 0:
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    ultimo_v = v
                                    print(f"🎯 CAPTURADO: {v}x")
                                break
                    except Exception as e:
                        # Si el error es porque el navegador se cerró, salimos al bucle de reconexión
                        if "Target closed" in str(e) or "context" in str(e):
                            break
                    
                    time.sleep(0.4) # Frecuencia de escaneo
        except Exception as e:
            print(f"🔄 Buscando navegador... (Error: {e})")
            time.sleep(5)

if __name__ == "__main__":
    run()
