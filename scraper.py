import time, requests
from playwright.sync_api import sync_playwright

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    print("🕵️ Scraper V60 - Monitoreo Global")
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                page = browser.contexts[0].pages[0]
                print(f"✅ Vínculo Activo con {page.title()[:15]}...")
                
                u = 0.0
                # Súper Selector Universal
                sel = ".bubble-multiplier, .app-stats-item, [class*='multiplier'], .payout"

                while True:
                    try:
                        for f in page.frames:
                            el = f.locator(sel).first
                            if el and el.is_visible():
                                t = el.inner_text(timeout=1000).lower().replace('x','').replace(',','.').strip()
                                v = float(t)
                                if v != u and v > 0:
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    u = v
                                    print(f"🎯 Capturado: {v}x")
                                    time.sleep(1) # Evitar duplicados
                                break
                    except Exception as e:
                        if "Target closed" in str(e): raise Exception("Cerrado")
                    time.sleep(0.4)
        except:
            print("🔄 Reconectando...")
            time.sleep(5)

if __name__ == "__main__": run()
