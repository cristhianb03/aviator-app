import time
import requests
from playwright.sync_api import sync_playwright

# CONFIGURACIÓN
URL_SERVIDOR = "http://localhost:8000/nuevo-resultado"
DEBUG_URL = "http://127.0.0.1:9222"

def run():
    with sync_playwright() as p:
        print("🔍 Iniciando Escaneo Profundo...")
        try:
            # Conexión al Edge abierto
            browser = p.chromium.connect_over_cdp(DEBUG_URL)
            context = browser.contexts[0]
            print("✅ Conectado a Edge.")
        except Exception as e:
            print(f"❌ ERROR: Edge no detectado en el puerto 9222. Revisa el comando del CMD.")
            return

        u = None

        while True:
            try:
                encontrado = False
                # Recorremos todas las pestañas
                for page in context.pages:
                    # Buscamos en cada rincón de la página (Frames)
                    for f in page.frames:
                        # BUSCADOR DINÁMICO: Buscamos cualquier cosa que parezca un multiplicador (ej: 1.50x)
                        # Este selector es casi imposible de bloquear para el casino
                        elementos = f.locator("text=/\\d+\\.\\d+x/").all()
                        
                        if len(elementos) > 0:
                            # Tomamos el primero de la lista (el más reciente en el historial)
                            texto = elementos[0].inner_text().lower().replace('x','').replace(',','.').strip()
                            
                            try:
                                v = float(texto)
                                if v != u:
                                    requests.post(URL_SERVIDOR, json={"valor": v}, timeout=1)
                                    u = v
                                    print(f"🎯 DATO CAPTURADO: {v}x (Fuente: {page.title()[:15]})")
                                encontrado = True
                                break
                            except:
                                continue
                    if encontrado: break
                
                if not encontrado:
                    # Imprime esto para saber que el script sigue intentando
                    print("⏳ Escaneando pantalla... (Asegúrate de que el juego sea visible)")
                    
            except Exception as e:
                pass
            
            # Revisa cada 0.5 segundos
            time.sleep(0.5)

if __name__ == "__main__":
    run()
