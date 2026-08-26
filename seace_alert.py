import os
import json
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Palabras clave ATÓMICAS (de 1 solo término) para asegurar coincidencia directa en el SEACE
KEYWORDS = [
    "accesorios", "uniforme", "vestuario", "indumentaria", 
    "calzado", "zapato", "cartera", "correa", "cuero", 
    "marroquineria", "talabarteria", "billetera", "cinturon", 
    "maletin", "mochila", "dotacion", "confeccion", "minem"
]

SEACE_PORTAL_URL = "https://prodapp2.seace.gob.pe/seace3-public/"

def send_telegram_alert(proceso):
    """Envía la alerta a Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
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
        requests.post(url, json=payload, timeout=10)
        print(f"✅ Alerta enviada a Telegram: {proceso.get('descripcion')}")
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")

def main():
    print("🔎 Iniciando rastreador dinámico en el SEACE...")
    
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
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        for kw in KEYWORDS:
            print(f"📡 Buscando en SEACE el término: '{kw}'...")
            try:
                page.goto("https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml", timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                
                # Rellenar campo de descripción
                inp = page.locator("input[id*='tbDescripcion'], input[id*='txtObjeto']").first
                if inp.is_visible():
                    inp.fill(kw)
                    page.wait_for_timeout(500)
                    
                    # Clic en el botón Buscar
                    btn = page.locator("button[id*='btnBuscar'], input[id*='btnBuscar'], button:has-text('Buscar')").first
                    if btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(4000) # Esperar respuesta AJAX
                        
                        # Extraer filas resultantes
                        rows = page.locator("tbody[id*='tbProcesos'] tr, tbody[id*='dtProcesos'] tr, tr.ui-widget-content").all()
                        print(f"   📊 Filas detectadas para '{kw}': {len(rows)}")
                        
                        for row in rows:
                            text = row.inner_text().strip()
                            if not text or "No se encontraron registros" in text or "Sin datos" in text:
                                continue
                                
                            cols = [c.strip() for c in text.split("\t") if c.strip()]
                            if len(cols) < 2:
                                cols = [c.strip() for c in text.split("\n") if c.strip()]
                                
                            if len(cols) >= 2:
                                entidad = cols[1] if len(cols) > 1 else "Entidad Estatal"
                                desc = cols[2] if len(cols) > 2 else cols[0]
                                
                                proc_id = f"{entidad}-{desc}"
                                if proc_id not in processed_ids:
                                    send_telegram_alert({
                                        "entidad": entidad,
                                        "descripcion": desc,
                                        "monto": "Consultar Ficha",
                                        "keyword": kw
                                    })
                                    processed_ids.add(proc_id)
            except Exception as e:
                print(f"⚠️ Error procesando '{kw}': {e}")
        
        browser.close()

    with open(history_file, "w") as f:
        json.dump(list(processed_ids), f)
        
    print("✅ Escaneo completado.")

if __name__ == "__main__":
    main()
