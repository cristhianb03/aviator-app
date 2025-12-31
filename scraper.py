import time
import requests
from playwright.sync_api import sync_playwright

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    print("🚀 Iniciando Scraper Blindado V18...")
    while True: # Bucle infinito para no morir nunca
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                context = browser.contexts[0]
                
                # Buscamos la pestaña de Aviator
                page = None
                for p_actual in context.pages:
                    if "aviator" in p_actual.url.lower():
                        page = p_actual
                        break
                
                if not page:
                    print("⏳ Esperando a que abras el Aviator en Edge...")
                    time.sleep(5)
                    continue

                print(f"✅ VÍNCULO ACTIVO: {page.title()[:20]}")
                u = None
                sel = ".bubble-multiplier, .payout, .app-stats-item, [class*='multiplier']"

                while True:
                    try:
                        for f in page.frames:
                            el = f.locator(sel).first
                            if el and el.is_visible():
                                t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                                v = float(t)
                                if v != u:
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    u = v
                                    print(f"🎯 CAPTURADO: {v}x")
                                break
                    except Exception as e:
                        if "Target closed" in str(e):
                            print("❌ El navegador se cerró. Reintentando vínculo...")
                            break # Sale al bucle principal para reconectar
                    time.sleep(0.4)

        except Exception as e:
            print(f"🔄 Esperando conexión con Edge (Puerto 9222)...")
            time.sleep(5)

if __name__ == "__main__":
    run()
