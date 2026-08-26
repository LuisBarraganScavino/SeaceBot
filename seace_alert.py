import os
import json
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Sombrilla de Cobertura Total para productos Alda e indumentaria estatal
KEYWORDS = [
    "cartera", "correa", "calzado", "zapato", "cartapacio", 
    "agenda", "escritorio", "cuero", "marroquineria", "talabarteria",
    "billetera", "cinturon", "maletin", "mochila",
    "accesorios de invierno", "accesorios de vestir", "accesorios de uniformes",
    "uniforme", "vestuario", "indumentaria", "dotacion", 
    "confeccion", "prendas de vestir", "textil"
]

SEACE_PORTAL_URL = "https://prodapp2.seace.gob.pe/seace3-public/"

def send_telegram_alert(proceso):
    """Envía la alerta incluyendo la fecha límite de presentación de ofertas."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    mensaje = (
        f"🚨 *LICITACIÓN VIGENTE DETECTADA - SEACE*\n\n"
        f"🏢 *Entidad:* {proceso.get('entidad', 'N/A')}\n"
        f"📋 *Objeto:* {proceso.get('descripcion', 'N/A')}\n"
        f"💰 *Monto Ref.:* S/ {proceso.get('monto', 'N/A')}\n"
        f"📅 *Presentación de Ofertas:* *{proceso.get('fecha_presentacion', 'Consultar Bases')}*\n"
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
        requests.post(url, json=payload, timeout=10)
        print(f"✅ Alerta enviada a Telegram: {proceso.get('descripcion')}")
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")

def main():
    print("🔎 Iniciando rastreador con navegador virtual (Playwright)...")
    
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
        page = browser.new_page()
        
        for kw in KEYWORDS:
            print(f"📡 Buscando en SEACE: '{kw}'...")
            try:
                page.goto("https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml", timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                
                # Rellenar descripción del objeto
                input_selector = "input[id*='tbDescripcion'], input[id*='txtObjeto'], input[id*='descripcion']"
                if page.locator(input_selector).count() > 0:
                    page.fill(input_selector, kw)
                    page.wait_for_timeout(500)
                    
                    # Presionar botón de búsqueda
                    btn_selector = "button[id*='btnBuscar'], input[id*='btnBuscar'], [value*='Buscar']"
                    if page.locator(btn_selector).count() > 0:
                        page.click(btn_selector)
                        page.wait_for_timeout(4000)
                
                # Extraer filas de la tabla de resultados
                rows = page.locator("tr.ui-widget-content").all()
                for row in rows:
                    text = row.inner_text()
                    cols = text.split("\t") if "\t" in text else text.split("\n")
                    if len(cols) >= 3:
                        entidad = cols[1].strip() if len(cols) > 1 else "Entidad Estatal"
                        desc = cols[2].strip() if len(cols) > 2 else "Objeto de contratación"
                        fecha_pres = cols[4].strip() if len(cols) > 4 else "Vigente"
                        
                        proc_id = f"{entidad}-{desc}"
                        if proc_id not in processed_ids:
                            send_telegram_alert({
                                "entidad": entidad,
                                "descripcion": desc,
                                "monto": "Consultar Ficha",
                                "fecha_presentacion": fecha_pres,
                                "keyword": kw
                            })
                            processed_ids.add(proc_id)
            except Exception as e:
                print(f"⚠️ Error procesando '{kw}': {e}")
        
        browser.close()

    with open(history_file, "w") as f:
        json.dump(list(processed_ids), f)
        
    print("✅ Escaneo de licitaciones vigentes completado.")

if __name__ == "__main__":
    main()
