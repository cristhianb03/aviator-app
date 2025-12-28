import time
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"

def run():
    with sync_playwright() as p:
        print("🇨🇴 Iniciando túnel hacia Colombia (IP: 200.69.78.90)...")
        
        # CONFIGURACIÓN DEL PROXY
        # Reemplaza '8080' por el puerto correcto si lo tienes
        proxy_config = {
            "server": "http://200.69.78.90:8080" 
        }

        try:
            # Lanzamos el navegador usando la IP de Colombia
            browser = p.chromium.launch(
                headless=False, # Déjalo en False para verlo en el escritorio remoto
                proxy=proxy_config,
                args=['--no-sandbox']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Aplicamos sigilo
            stealth = Stealth()
            stealth.apply_stealth_sync(page)

            print("🔗 Conectando a 1Win a través de ETB Colombia...")
            page.goto("https://1wmxk.com/casino/play/v_spribe:aviator", wait_until="networkidle", timeout=60000)

            print("✅ Conexión establecida. Los valores ahora coinciden con Colombia.")

            ultimo_v = None
            sel = "[class*='bubble-multiplier'], [class*='multiplier'], .stats-list div"

            while True:
                try:
                    for f in page.frames:
                        el = f.locator(sel).first
                        if el.is_visible():
                            t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                            v = float(t)
                            if v != ultimo_v:
                                requests.post(URL_SERVIDOR, json={"valor": v}, timeout=2)
                                ultimo_v = v
                                print(f"🎯 Capturado (Sala COL): {v}x")
                            break
                except: pass
                time.sleep(0.5)

        except Exception as e:
            print(f"❌ Error de conexión al Proxy: {e}")
            print("Verifica si el puerto 8080 es correcto o si la IP está activa.")

if __name__ == "__main__":
    run()
