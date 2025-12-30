
import time
import requests
from playwright.sync_api import sync_playwright

# CONFIGURACIÓN
URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
# El puerto 9222 es el estándar para Edge/Chrome en modo debug
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    with sync_playwright() as p:
        print("🔗 Conectando a Microsoft Edge (Sala Colombia)...")
        
        try:
            # Conexión remota al navegador que abriste por terminal
            # No indicamos 'msedge' aquí porque connect_over_cdp usa el motor base
            browser = p.chromium.connect_over_cdp(DEBUG_URL)
            context = browser.contexts[0]
            
            # Buscador de la pestaña del juego
            page = None
            for p_actual in context.pages:
                if "aviator" in p_actual.url.lower() or "1win" in p_actual.url.lower():
                    page = p_actual
                    break
            
            if not page:
                print("⚠️ Pestaña de Aviator no detectada. Usando pestaña principal.")
                page = context.pages[0]

            print(f"✅ VÍNCULO EXITOSO CON EDGE: {page.title()}")
            
        except Exception as e:
            print(f"❌ ERROR: No se pudo conectar a Edge en el puerto 9222.")
            print(f"Detalle: {e}")
            return

        u = None
        # Súper Selector Unificado para 1Win
        sel = "[class*='bubble-multiplier'], [class*='multiplier'], [class*='payout'], .stats-list div"

        while True:
            try:
                for f in page.frames:
                    # Buscamos de forma más agresiva en el historial superior
                    # Agregamos .payouts-block y elementos de burbuja genéricos
                    elementos = f.locator(".bubble-multiplier, .payout, .app-stats-item, [class*='multiplier']").all()
                    
                    if len(elementos) > 0:
                        # Probamos con el primer elemento encontrado
                        el = elementos[0]
                        t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                        
                        # DEBUG: Si quieres ver si encuentra algo aunque no sea el número exacto
                        # print(f"DEBUG: Encontrado texto: {t}") 

                        try:
                            v = float(t)
                            if v != u:
                                requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                u = v
                                print(f"🎯 DATO CAPTURADO: {v}x")
                            break 
                        except ValueError:
                            continue # Si no es un número, sigue buscando
            except Exception as e:
                pass
            time.sleep(0.3)
if __name__ == "__main__":
    run()

