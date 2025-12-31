import time, requests
from playwright.sync_api import sync_playwright

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    print("🕵️ Scraper V100 - Sistema Anti-Duplicados")
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                page = browser.contexts[0].pages[0]
                
                ultimo_enviado = 0.0 # Memoria para no repetir
                sel = ".bubble-multiplier, .app-stats-item, [class*='multiplier']"

                while True:
                    try:
                        for f in page.frames:
                            el = f.locator(sel).first
                            if el and el.is_visible():
                                t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                                v = float(t)
                                
                                # SOLO ENVIAMOS SI ES UN NÚMERO NUEVO
                                if v != ultimo_enviado:
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    ultimo_enviado = v
                                    print(f"🎯 Capturado: {v}x")
                                    # Esperamos 1 segundo para que la burbuja se asiente
                                    time.sleep(1) 
                                break
                    except: pass
                    time.sleep(0.4)
        except: time.sleep(5)

if __name__ == "__main__": run()
