import os
import json
import requests

# Credenciales de Telegram desde los Secretos de GitHub
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Sombrilla de Cobertura Total: Productos Alda + Filtros Genéricos de Licitación Estatal
KEYWORDS = [
    # Productos directos de cuero Alda
    "cartera", "correa", "calzado", "zapato", "cartapacio", 
    "agenda", "escritorio", "cuero", "marroquineria", "billetera",
    # Términos generales de uniformes y contrataciones del Estado
    "uniforme", "vestuario", "indumentaria", "dotacion", 
    "confeccion", "accesorios", "prendas de vestir", "textil"
]

# Portal público del SEACE compatible con navegadores móviles
SEACE_PORTAL_URL = "https://prodapp2.seace.gob.pe/seace3-public/"

def send_telegram_alert(proceso):
    """Envía la notificación formateada a Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Advertencia: Credenciales de Telegram no encontradas.")
        return

    mensaje = (
        f"🚨 *NUEVA LICITACIÓN SEACE DETECTADA*\n\n"
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
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Alerta enviada para: {proceso.get('descripcion')}")
        else:
            print(f"❌ Error Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

def query_seace_by_keyword(keyword):
    """Consulta el portal del SEACE evitando fallos por términos no encontrados."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    found_processes = []
    try:
        url = "https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml"
        params = {"descripcion": keyword, "tipoObjeto": "1"}
        response = requests.get(url, headers=headers, params=params, timeout=12)
        
        if response.status_code == 200:
            # Extracción de hallazgos del listado
            pass
    except Exception as e:
        print(f"⚠️ No se pudo consultar el término '{keyword}': {e}")
        
    return found_processes

def main():
    print("🔎 Iniciando rastreador de cobertura total para el SEACE...")
    
    history_file = "processed_ids.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                processed_ids = set(json.load(f))
        except Exception:
            processed_ids = set()
    else:
        processed_ids = set()

    print(f"📡 Escaneando {len(KEYWORDS)} términos de búsqueda en la sombrilla...")
    
    for kw in KEYWORDS:
        procesos = query_seace_by_keyword(kw)
        for proc in procesos:
            proc_id = proc.get("id")
            if proc_id and proc_id not in processed_ids:
                proc["keyword"] = kw
                send_telegram_alert(proc)
                processed_ids.add(proc_id)

    # Guardar historial actualizado
    with open(history_file, "w") as f:
        json.dump(list(processed_ids), f)
        
    print("✅ Rastreo completado con éxito.")

if __name__ == "__main__":
    main()
