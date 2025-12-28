import time
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# AQUÍ ES DONDE SE DEFINE LA RUTA AL SERVIDOR
# Como el Scraper y el Servidor están en la misma máquina de Google, usamos localhost
URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"

def run():
    with sync_playwright() as p:
        print("🚀 Iniciando Ojo Invisible en Google Cloud...")
        
        # Lanzamiento invisible (Headless)
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Sigilo para evitar bloqueos
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        print("🔗 Conectando al Casino...")
        page.goto("https://1wmxk.com/casino/play/v_spribe:aviator", wait_until="networkidle")

        ultimo_valor = None
        # Selector universal de los globos de resultados
        sel = "[class*='bubble-multiplier'], [class*='multiplier'], .stats-list div"

        while True:
            try:
                for frame in page.frames:
                    el = frame.locator(sel).first
                    if el.is_visible():
                        # Limpiamos el texto para obtener solo el número
                        t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                        v = float(t)
                        
                        # Si el valor cambió, lo enviamos
                        if v != ultimo_valor:
                            
                            # ==========================================
                            # ESTA ES LA OPCIÓN QUE PREGUNTASTE:
                            # Enviamos el dato al "Cerebro" (servidor.py)
                            try:
                                requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                print(f"🎯 Capturado y enviado: {v}x")
                            except Exception as e:
                                print(f"⚠️ Error enviando al servidor: {e}")
                            # ==========================================
                            
                            ultimo_valor = v
                        break
            except: 
                pass
            
            # Revisa cada medio segundo
            time.sleep(0.5)

if __name__ == "__main__":
    run()
