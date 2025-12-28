import time, requests
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        print("🔗 Conectando al navegador de Colombia...")
        try:
            # Nos conectamos al Chrome que abriste con el comando anterior
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            page = browser.contexts[0].pages[0] 
            print(f"✅ Conectado a: {page.title()}")
        except Exception as e:
            print(f"❌ Error: ¿Abriste Chrome con el comando de depuración? {e}")
            return

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
                            # Enviamos al servidor local (misma IP de Google)
                            requests.post("http://localhost:8000/nuevo-resultado", json={"valor": v})
                            u = v
                            print(f"🎯 Capturado (Sala COL): {v}x")
                        break
            except: pass
            time.sleep(0.4)
run()
