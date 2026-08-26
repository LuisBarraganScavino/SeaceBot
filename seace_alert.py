import os
import json
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Palabras clave estratégicas para detectar vestuario, calzado y accesorios
KEYWORDS = [
    "accesorios", "uniforme", "vestuario", "indumentaria", 
    "calzado", "zapato", "cartera", "correa", "cuero", 
    "marroquineria", "talabarteria", "billetera", "cinturon", 
    "maletin", "mochila", "dotacion", "confeccion"
]

SEACE_PORTAL_URL = "https://prodapp2.seace.gob.pe/seace3-public/"

def send_telegram_alert(proceso):
    """Envía la alerta a Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Faltan credenciales de Telegram.")
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

def main():
    print("🔎 Iniciando navegador virtual con evasión de bloqueos en SEACE 3.0...")
    
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
        # Lanzar Chromium desactivando banderas de automatización
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        
        page = context.new_page()
        # Ocultar indicador de automatización en JS
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("🌐 Cargando portal del SEACE...")
        try:
            page.goto("https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml", timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"⚠️ Error al cargar la página principal: {e}")

        for kw in KEYWORDS:
            print(f"\n📡 Escaneando término: '{kw}'...")
            try:
                # Localizar todos los campos de texto visibles
                inputs = page.locator("input[type='text'], input.ui-inputfield").all()
                target_input = None
                for inp in inputs:
                    if inp.is_visible() and inp.is_enabled():
                        target_input = inp
                        break

                if target_input:
                    # Limpiar y rellenar
                    target_input.click()
                    target_input.fill("")
                    page.wait_for_timeout(300)
                    target_input.fill(kw)
                    page.wait_for_timeout(500)

                    # Buscar el botón de búsqueda
                    btn = page.locator("button:has-text('Buscar'), input[value*='Buscar'], .ui-button:has-text('Buscar')").first
                    if btn.is_visible():
                        btn.click()
                    else:
                        target_input.press("Enter")

                    page.wait_for_timeout(4000) # Esperar respuesta AJAX

                    # Inspeccionar resultados
                    rows = page.locator("tr.ui-widget-content").all()
                    print(f"   📊 Filas detectadas en la tabla: {len(rows)}")

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
                                print(f"   🎯 ¡LICITACIÓN DETECTADA!: {desc[:50]}")
                                send_telegram_alert({
                                    "entidad": entidad,
                                    "descripcion": desc,
                                    "monto": "Consultar Ficha",
                                    "keyword": kw
                                })
                                processed_ids.add(proc_id)
                else:
                    print("   ⚠️ Reintentando recargar el formulario...")
                    page.goto("https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml", timeout=30000)
                    page.wait_for_timeout(3000)

            except Exception as e:
                print(f"   ⚠️ Error en la consulta del término '{kw}': {e}")

        browser.close()

    with open(history_file, "w") as f:
        json.dump(list(processed_ids), f)
        
    print("\n✅ Ejecución finalizada.")

if __name__ == "__main__":
    main()
