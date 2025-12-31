import time
import requests
from playwright.sync_api import sync_playwright

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    print("🕵️ Scraper IA V100 - Iniciando modo resiliente...")
    while True: # Bucle de vida infinita
        try:
            with sync_playwright() as p:
                # Intentar conectar al puerto 9222
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                context = browser.contexts[0]
                
                # Buscar la pestaña del juego
                page = None
                for p_actual in context.pages:
                    if "aviator" in p_actual.url.lower() or "1win" in p_actual.url.lower():
                        page = p_actual
                        break
                
                if not page:
                    print("⏳ Esperando a que abras Aviator en el navegador...")
                    time.sleep(5)
                    continue

                print(f"✅ Vínculo activo con: {page.title()[:15]}")
                ultimo_v = 0.0
                sel = ".bubble-multiplier, .app-stats-item, [class*='multiplier']"

                while True: # Bucle de captura
                    try:
                        for f in page.frames:
                            el = f.locator(sel).first
                            if el and el.is_visible():
                                t = el.inner_text(timeout=1000).lower().replace('x','').replace(',','.').strip()
                                v = float(t)
                                if v != ultimo_v and v > 0:
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    ultimo_v = v
                                    print(f"🎯 Capturado: {v}x")
                                break
                    except Exception as e:
                        if "Target closed" in str(e) or "Browser sent invalid" in str(e):
                            print("❌ El navegador se cerró. Reintentando vínculo...")
                            break # Rompe al bucle exterior para reconectar
                    time.sleep(0.5)
        except Exception as e:
            print("🔄 Buscando puerto 9222 activo... Asegúrate de abrir Edge.")
            time.sleep(5)

if __name__ == "__main__":
    run()
