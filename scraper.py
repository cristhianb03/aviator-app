import time
import requests
from playwright.sync_api import sync_playwright

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    while True: # Bucle de auto-reconexión
        try:
            with sync_playwright() as p:
                print("🔗 Intentando conectar con Edge...")
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                context = browser.contexts[0]
                
                # Buscamos la pestaña del juego
                page = None
                for p_actual in context.pages:
                    if "aviator" in p_actual.url.lower() or "1win" in p_actual.url.lower():
                        page = p_actual
                        break
                
                if not page:
                    print("⚠️ Esperando a que abras el Aviator en Edge...")
                    time.sleep(5)
                    continue

                print(f"✅ VÍNCULO ACTIVO: {page.title()[:20]}")
                u = None
                # Selector universal ultra-rápido
                sel = ".bubble-multiplier, .app-stats-item, [class*='multiplier']"

                while True:
                    try:
                        found = False
                        for f in page.frames:
                            el = f.locator(sel).first
                            if el and el.is_visible():
                                t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                                v = float(t)
                                if v != u:
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    u = v
                                    print(f"🎯 CAPTURADO: {v}x")
                                found = True
                                break
                        if not found:
                            # Si no ve el elemento, puede que la página se haya recargado
                            pass
                    except Exception as e:
                        if "Target closed" in str(e):
                            print("❌ El navegador se cerró. Reintentando vínculo...")
                            break # Sale al bucle de arriba para reconectar
                    
                    time.sleep(0.3) # Revisa 3 veces por segundo

        except Exception as e:
            print(f"🔄 Error de conexión: {e}. Reintentando en 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    run()
