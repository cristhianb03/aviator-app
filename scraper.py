import time
import requests
from playwright.sync_api import sync_playwright

# CONFIGURACIÓN
URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    with sync_playwright() as p:
        print("🌐 Iniciando Motor de Escaneo Universal...")
        try:
            # Nos vinculamos al Edge que tienes abierto
            browser = p.chromium.connect_over_cdp(DEBUG_URL)
            context = browser.contexts[0]
            print("✅ Conectado a Edge. Buscando casinos activos...")
        except Exception as e:
            print(f"❌ ERROR: Edge no detectado. Abrelo por CMD en puerto 9222.")
            return

        u = None
        # Lista de palabras clave para detectar el juego en cualquier pestaña
        casinos_validos = ["aviator", "1win", "melbet", "betplay", "1w-", "spribe"]
        
        # Selector Maestro: Cubre casi todas las versiones del historial de Spribe
        selector_universal = ".bubble-multiplier, .app-stats-item, .payouts-block .payout, [class*='multiplier'], [class*='bubble']"

        while True:
            try:
                encontrado_en_alguna_pestaña = False
                
                # RECORREMOS TODAS LAS PESTAÑAS ABIERTAS
                for page in context.pages:
                    url_actual = page.url.lower()
                    
                    # Verificamos si esta pestaña es un casino con Aviator
                    if any(keyword in url_actual for keyword in casinos_validos):
                        
                        # Escaneamos los frames internos de esta pestaña
                        for f in page.frames:
                            try:
                                el = f.locator(selector_universal).first
                                if el and el.is_visible():
                                    t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                                    v = float(t)
                                    
                                    if v != u:
                                        # Enviar al Servidor
                                        requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                        u = v
                                        # Identificamos la fuente en el log
                                        fuente = "MELBET" if "melbet" in url_actual else "1WIN/OTRO"
                                        print(f"🎯 [{fuente}] CAPTURADO: {v}x")
                                    
                                    encontrado_en_alguna_pestaña = True
                                    break # Dato encontrado en esta pestaña
                            except:
                                continue
                    
                    if encontrado_en_alguna_pestaña:
                        break # Ya tenemos el dato más reciente del navegador

            except Exception as e:
                pass
            
            # Revisión rápida
            time.sleep(0.4)

if __name__ == "__main__":
    run()
