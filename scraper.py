import time
import requests
from playwright.sync_api import sync_playwright

# CONFIGURACIÓN
URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    with sync_playwright() as p:
        print("🌐 Iniciando Escáner Universal de Aviator...")
        try:
            # Nos vinculamos al Edge/Chrome que tienes abierto en puerto 9222
            browser = p.chromium.connect_over_cdp(DEBUG_URL)
            context = browser.contexts[0]
            print("✅ Conectado al navegador. Buscando el juego en cualquier pestaña...")
        except Exception as e:
            print(f"❌ ERROR: No se detecta el navegador abierto. Abre Edge por CMD en el puerto 9222.")
            return

        u = None
        # SELECTOR MAESTRO: Busca cualquier burbuja de Spribe en cualquier casino
        # Cubre 1Win, Melbet, Betplay, Pin-up, etc.
        selectors = [
            ".bubble-multiplier", 
            ".app-stats-item", 
            ".payouts-block .payout",
            "[class*='multiplier']",
            "[class*='bubble']",
            ".stats-list div"
        ]
        sel_string = ", ".join(selectors)

        while True:
            try:
                encontrado_en_pestaña = False
                
                # RECORREMOS TODAS LAS PESTAÑAS (PAGES) DEL NAVEGADOR
                for page in context.pages:
                    try:
                        # Buscamos en el frame principal y en todos los iframes hijos
                        for f in page.frames:
                            # Intentamos localizar el primer número del historial
                            el = f.locator(sel_string).first
                            
                            if el and el.is_visible():
                                texto = el.inner_text().lower().replace('x','').replace(',','.').strip()
                                
                                # Validamos que sea un número (float)
                                try:
                                    v = float(texto)
                                    if v != u:
                                        # ENVIAR AL SERVIDOR IA
                                        res = requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                        if res.status_code == 200:
                                            print(f"🎯 CAPTURADO UNIVERSAL: {v}x (En: {page.title()[:20]}...)")
                                        u = v
                                    encontrado_en_pestaña = True
                                    break # Dato encontrado, salir de los frames
                                except:
                                    continue
                        if encontrado_en_pestaña: break # Salir de las pestañas tras capturar
                    except:
                        continue # Si una pestaña falla (ej. cargando), pasamos a la siguiente

            except Exception as e:
                # print(f"Buscando... {e}")
                pass
            
            # Velocidad de escaneo: 0.4 segundos para no saturar el CPU
            time.sleep(0.4)

if __name__ == "__main__":
    run()
