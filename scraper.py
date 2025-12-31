import time
import requests
from playwright.sync_api import sync_playwright

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    print("🕵️ Scraper IA V100 - Iniciando monitoreo...")
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                page = browser.contexts[0].pages[0]
                print(f"✅ CONECTADO A: {page.title()[:15]}")
                
                ultimo_enviado = 0.0 
                sel = ".bubble-multiplier, .app-stats-item, [class*='multiplier']"

                while True:
                    try:
                        for f in page.frames:
                            el = f.locator(sel).first
                            if el and el.is_visible():
                                t = el.inner_text(timeout=1000).lower().replace('x','').replace(',','.').strip()
                                v = float(t)
                                
                                if v != ultimo_enviado and v > 0:
                                    print(f"🎯 NUEVA RONDA DETECTADA: {v}x")
                                    # ENVIAMOS AL SERVIDOR LOCAL
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    ultimo_enviado = v
                                    time.sleep(1) # Esperar a que el juego cambie
                                break
                    except Exception as e:
                        if "Target closed" in str(e): raise Exception("Edge cerrado")
                    time.sleep(0.4)
        except:
            print("🔄 Buscando navegador en puerto 9222...")
            time.sleep(5)

if __name__ == "__main__":
    run()
