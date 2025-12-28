import time
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"

def run():
    with sync_playwright() as p:
        # Usamos argumentos para deshabilitar detecciones comunes de Linux
        browser = p.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-setuid-sandbox'
        ])
        
        # Simulamos una pantalla de celular para que el casino sea menos estricto
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            viewport={'width': 375, 'height': 667},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        
        page = context.new_page()
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        print("🔗 Intentando entrar por bypass móvil...")
        try:
            page.goto("https://1wmxk.com/casino/play/v_spribe:aviator", wait_until="domcontentloaded", timeout=60000)
            time.sleep(10) # Esperamos 10 segundos a que cargue el iframe
            page.screenshot(path="verificacion.png") # Foto para ver si hay error
        except Exception as e:
            print(f"❌ Error de carga: {e}")

        ultimo_v = None
        # Selector más agresivo
        sel = ".bubble-multiplier, [class*='multiplier'], .stats-list div"

        while True:
            try:
                # Escaneamos todos los frames (Aviator es un iframe dentro de otro)
                for f in page.frames:
                    el = f.locator(sel).first
                    if el.is_visible():
                        t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                        v = float(t)
                        if v != ultimo_v:
                            requests.post(URL_SERVIDOR, json={"valor": v}, timeout=2)
                            ultimo_v = v
                            print(f"🎯 Capturado: {v}x")
                        break
            except: pass
            time.sleep(0.5)

if __name__ == "__main__":
    run()
