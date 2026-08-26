import os
import json
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Palabras clave estratégicas para detectar vestuario, calzado y accesorios de Alda
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
    print("🔎 Iniciando navegador virtual para escanear SEACE 3.0...")
    
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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = context.new_page()

        for kw in KEYWORDS:
            print(f"\n📡 Buscando en SEACE: '{kw}'...")
            try:
                page.goto("https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml", timeout=60000, wait_until="networkidle")
                page.wait_for_timeout(2000)

                # Localizar cualquier campo de texto de descripción
                input_field = page.locator("input[type='text']").filter(has=page.locator("xpath=ancestor::tr")).first
                
                # Intentar rellenar mediante selectores alternativos si el filtro falla
                if not input_field.is_visible():
                    input_field = page.locator("input[id*='tbDescripcion'], input[id*='txtObjeto'], input[id*='descripcion']").first

                if input_field.is_visible():
                    input_field.fill(kw)
                    page.wait_for_timeout(500)

                    # Buscar botón de acción (Buscar)
                    btn = page.locator("button:has-text('Buscar'), input[value*='Buscar'], [id*='btnBuscar']").first
                    if btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(5000) # Esperar respuesta AJAX del SEACE

                        # Obtener filas de resultados
                        rows = page.locator("tr.ui-widget-content").all()
                        print(f"   📊 Filas obtenidas en pantalla para '{kw}': {len(rows)}")

                        for row in rows:
                            text = row.inner_text().strip()
                            if not text or "No se encontraron" in text or "Sin registros" in text:
                                continue

                            # Limpiar y separar columnas
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
                    print("   ⚠️ No se pudo visibilizar el cuadro de texto de búsqueda.")

            except Exception as e:
                print(f"   ⚠️ Error escaneando '{kw}': {e}")

        browser.close()

    # Guardar historial actualizado
    with open(history_file, "w") as f:
        json.dump(list(processed_ids), f)
        
    print("\n✅ Paso 1 completado.")

if __name__ == "__main__":
    main()
