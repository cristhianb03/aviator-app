import time
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"

def run():
    with sync_playwright() as p:
        print("🚀 Iniciando Navegador Invisible en Google Cloud...")
        
        # CAMBIO CLAVE: launch en lugar de connect_over_cdp
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        print("🔗 Conectando al Casino...")
        page.goto("https://1wmxk.com/casino/play/v_spribe:aviator", wait_until="networkidle")

        u = None
        sel = "[class*='bubble-multiplier'], [class*='multiplier'], .stats-list div"

        while True:
            try:
                for f in page.frames:
                    el = f.locator(sel).first
                    if el.is_visible():
                        t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                        v = float(t)
                        if v != u:
                            requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                            u = v
                            print(f"🎯 Capturado: {v}x")
                        break
            except: pass
            time.sleep(0.5)

if __name__ == "__main__":
    run()
