import time
import requests
from playwright.sync_api import sync_playwright

# CONFIGURACIÓN
URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_PORT = "http://localhost:9222"

def run():
    with sync_playwright() as p:
        print("🔗 Intentando conectar con Edge en puerto 9222...")
        try:
            # 1. Conexión al navegador
            browser = p.chromium.connect_over_cdp(DEBUG_PORT)
            context = browser.contexts[0]
            
            # 2. Buscador inteligente de pestaña
            page = None
            for p_actual in context.pages:
                if "aviator" in p_actual.url.lower() or "1win" in p_actual.url.lower():
                    page = p_actual
                    break
            
            if not page:
                print("❌ ERROR: No encontré ninguna pestaña con el juego Aviator.")
                print("Asegúrate de tener el juego abierto en la ventana de Edge que abriste por CMD.")
                return

            print(f"✅ CONECTADO a la pestaña: {page.title()}")
        except Exception as e:
            print(f"❌ ERROR DE CONEXIÓN: {e}")
            print("RECUERDA: Cierra Edge y ábrelo con el comando del CMD.")
            return

        u = None
        # Selectores actualizados al 28 de diciembre de 2025
        selectors = [
            ".stats-list .bubble-multiplier",
            ".payouts-block .app-stats-item",
            ".payouts-wrapper .payout",
            "[class*='bubble-multiplier']",
            "[class*='multiplier']"
        ]
        sel_string = ", ".join(selectors)

        print("🔍 Rastreando datos... (Espera a que termine una ronda)")

        while True:
            try:
                encontrado_en_esta_vuelta = False
                # 3. Escaneo profundo de frames
                for f in page.frames:
                    try:
                        # Buscamos el elemento más reciente
                        el = f.locator(sel_string).first
                        
                        if el and el.is_visible():
                            t = el.inner_text().lower().replace('x','').replace(',','.').strip()
                            v = float(t)
                            
                            if v != u:
                                # ENVIAR AL SERVIDOR
                                res = requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                if res.status_code == 200:
                                    print(f"🎯 DATO CAPTURADO: {v}x")
                                u = v
                            
                            encontrado_en_esta_vuelta = True
                            break
                    except:
                        continue
                
                if not encontrado_en_esta_vuelta:
                    # Si no encuentra nada, imprimimos un aviso cada 10 segundos
                    pass

            except Exception as e:
                # print(f"Aviso: {e}")
                pass
            
            time.sleep(0.5)

if __name__ == "__main__":
    run()