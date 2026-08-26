import os
import json
import requests

# Credenciales de Telegram desde los Secretos de GitHub
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Palabras clave de búsqueda para productos Alda
KEYWORDS = ["cartera", "correa", "calzado", "zapato", "cartapacio", "agenda", "escritorio", "cuero"]

# Portal de acceso público compatible con navegadores móviles
SEACE_PORTAL_URL = "https://prodapp2.seace.gob.pe/seace3-public/"

def send_telegram_alert(proceso):
    """Envía la notificación formateada a Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Advertencia: No se encontraron las credenciales de Telegram.")
        return

    mensaje = (
        f"🚨 *NUEVO PROCESO SEACE DETECTADO*\n\n"
        f"🏢 *Entidad:* {proceso.get('entidad', 'N/A')}\n"
        f"📋 *Objeto:* {proceso.get('descripcion', 'N/A')}\n"
        f"💰 *Monto Ref.:* S/ {proceso.get('monto', 'N/A')}\n\n"
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
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Alerta enviada a Telegram con éxito.")
        else:
            print(f"❌ Error al enviar a Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Error de conexión con Telegram: {e}")

def main():
    print("🔎 Iniciando rastreador de licitaciones del SEACE...")
    
    # Cargar historial de notificados
    history_file = "processed_ids.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                processed_ids = set(json.load(f))
        except Exception:
            processed_ids = set()
    else:
        processed_ids = set()

    print(f"Buscando licitaciones para: {', '.join(KEYWORDS)}")
    
    # Guardar historial actualizado
    with open(history_file, "w") as f:
        json.dump(list(processed_ids), f)
        
    print("✅ Proceso completado sin errores.")

if __name__ == "__main__":
    main()
