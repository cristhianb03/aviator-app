import time
import requests
from playwright.sync_api import sync_playwright

URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    print("🚀 LANZANDO ESCÁNER DE ALTA VELOCIDAD V19...")
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(DEBUG_URL)
                context = browser.contexts[0]
                page = context.pages[0]
                
                print(f"✅ VÍNCULO ESTABLECIDO CON: {page.title()[:15]}")
                
                ultimo_v = None
                # Selector Maestro para 1Win/Melbet
                sel = ".bubble-multiplier, .app-stats-item, [class*='multiplier']"

                while True:
                    try:
                        # Buscamos en todos los frames del juego
                        for f in page.frames:
                            # 'all()' es más rápido que 'first' para evitar bloqueos
                            elementos = f.locator(sel).all()
                            
                            if elementos:
                                # Tomamos el texto del primer elemento encontrado
                                t = elementos[0].inner_text().lower().replace('x','').replace(',','.').strip()
                                
                                # Validamos que sea un número válido
                                try:
                                    v = float(t)
                                    if v != ultimo_v:
                                        # ENVÍO INMEDIATO
                                        requests.post(URL_SERVIDOR, json={"valor": v}, timeout=0.5)
                                        ultimo_v = v
                                        print(f"🎯 CAPTURADO: {v}x")
                                    break # Salir de los frames tras encontrar el dato
                                except:
                                    continue
                                    
                    except Exception as e:
                        if "Target closed" in str(e) or "context" in str(e).lower():
                            print("❌ Navegador cerrado o pestaña perdida. Reconectando...")
                            raise Exception("Reconectar")
                    
                    # Frecuencia de escaneo optimizada (0.3s)
                    time.sleep(0.3)

        except Exception:
            # Si Edge se cierra o hay error de conexión, esperamos 5 segundos y volvemos a intentar
            time.sleep(5)

if __name__ == "__main__":
    run()
