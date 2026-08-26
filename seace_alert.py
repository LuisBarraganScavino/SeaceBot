import os
import json
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Palabras clave atómicas para maximizar coincidencias en el SEACE
KEYWORDS = [
    "accesorios", "uniforme", "vestuario", "indumentaria", 
    "calzado", "zapato", "cartera", "correa", "cuero", 
    "marroquineria", "talabarteria", "billetera", "cinturon", 
    "maletin", "mochila", "dotacion", "confeccion"
]

SEACE_PORTAL_URL = "https://prodapp2.seace.gob.pe/seace3-public/"

def send_telegram_alert(proceso):
    """Envía la notificación formateada a Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Advertencia: Credenciales de Telegram no configuradas.")
        return

    mensaje = (
        f"🚨 *LICITACIÓN VIGENTE DETECTADA - SEACE*\n\n"
        f"🏢 *Entidad:* {proceso.get('entidad', 'N/A')}\n"
        f"📋 *Objeto:* {proceso.get('descripcion', 'N/A')}\n"
        f"💰 *Monto Ref.:* S/ {proceso.get('monto', 'N/A')}\n"
        f"🔑 *Filtro Coincidente:* `{proceso.get('keyword', 'N/A')}`\n\n"
        f"🔗 [Acceder al Buscador SEACE]({SEACE_PORTAL_URL})"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"✅ Alerta enviada a Telegram: {proceso.get('descripcion')[:40]}...")
        else:
            print(f"❌ Error al enviar a Telegram: {res.text}")
    except Exception as e:
        print(f"❌ Excepción de conexión a Telegram: {e}")

def resolve_search_frame(page):
    """Localiza el marco (iframe) o contexto principal donde reside el formulario."""
    for frame in page.frames:
        try:
            if frame.locator("input").count() > 0:
                return frame
        except Exception:
            continue
    return page

def main():
    print("🔎 Iniciando rastreador adaptativo avanzado para SEACE 3.0...")
    
    history_file = "processed_ids.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                processed_ids = set(json.load(f))
        except Exception:
            processed_ids = set()
    else:
        processed_ids = set()

    with sync_playwright() as p:
        # Configuración del navegador con banderas anti-detección
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("🌐 Accediendo al portal del SEACE...")
        try:
            page.goto("https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml", timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"⚠️ Error al cargar el sitio principal: {e}")
            page.screenshot(path="error_carga_inicial.png")

        for kw in KEYWORDS:
            print(f"\n📡 Escaneando término: '{kw}'...")
            try:
                frame = resolve_search_frame(page)
                
                # Búsqueda de cuadros de texto de descripción
                input_selectors = [
                    "input[id*='tbDescripcion']",
                    "input[id*='txtObjeto']",
                    "input[id*='descripcion']",
                    "input.ui-inputfield[type='text']",
                    "input[type='text']"
                ]
                
                target_input = None
                for sel in input_selectors:
                    loc = frame.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        target_input = loc.first
                        break

                if target_input:
                    target_input.click()
                    target_input.fill("")
                    page.wait_for_timeout(200)
                    target_input.fill(kw)
                    page.wait_for_timeout(300)

                    # Localizar y hacer clic en el botón de búsqueda
                    btn_selectors = [
                        "button[id*='btnBuscar']",
                        "input[id*='btnBuscar']",
                        "button:has-text('Buscar')",
                        "input[value*='Buscar']",
                        ".ui-button:has-text('Buscar')"
                    ]
                    
                    btn_clicked = False
                    for b_sel in btn_selectors:
                        btn_loc = frame.locator(b_sel)
                        if btn_loc.count() > 0 and btn_loc.first.is_visible():
                            btn_loc.first.click()
                            btn_clicked = True
                            break
                            
                    if not btn_clicked:
                        target_input.press("Enter")

                    page.wait_for_timeout(4500)  # Espera para carga AJAX de la tabla

                    # Extracción de la tabla de resultados
                    rows = frame.locator("tr.ui-widget-content, tbody[id*='tbProcesos'] tr, tbody[id*='dtProcesos'] tr").all()
                    print(f"   📊 Coincidencias en tabla: {len(rows)}")

                    for row in rows:
                        text = row.inner_text().strip()
                        if not text or "No se encontraron" in text or "Sin registros" in text:
                            continue

                        lines = [line.strip() for line in text.split("\n") if line.strip()]
                        if len(lines) >= 2:
                            entidad = lines[0]
                            desc = lines[1] if len(lines) > 1 else lines[0]

                            proc_id = f"{entidad}-{desc}"
                            if proc_id not in processed_ids:
                                print(f"   🎯 ¡PROCESO ENCONTRADO!: {desc[:50]}")
                                send_telegram_alert({
                                    "entidad": entidad,
                                    "descripcion": desc,
                                    "monto": "Consultar Ficha",
                                    "keyword": kw
                                })
                                processed_ids.add(proc_id)
                else:
                    print("   ⚠️ No se localizó el campo de búsqueda. Guardando captura de pantalla de diagnóstico...")
                    page.screenshot(path=f"debug_{kw}.png")
                    
                    # Reintento de navegación directa
                    page.goto("https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml", timeout=30000)
                    page.wait_for_timeout(3000)

            except Exception as e:
                print(f"   ⚠️ Error durante el escaneo de '{kw}': {e}")
                page.screenshot(path=f"error_{kw}.png")

        browser.close()

    with open(history_file, "w") as f:
        json.dump(list(processed_ids), f)
        
    print("\n✅ Proceso completado exitosamente.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
