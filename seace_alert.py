import os
import json
import re
import requests
import urllib3
from bs4 import BeautifulSoup

# Desactivar advertencias de SSL para el servidor del SEACE
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Sombrilla de palabras clave para productos Alda y licitaciones generales
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
    """Envía la alerta incluyendo la fecha de presentación de ofertas."""
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

def query_active_seace_processes(keyword):
    """Escanea los procesos en etapa activa de presentación de propuestas."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    found_processes = []
    try:
        url = "https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml"
        params = {"descripcion": keyword, "tipoObjeto": "1"}
        response = requests.get(url, headers=headers, params=params, timeout=15, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Buscar filas de la tabla de resultados del SEACE
            rows = soup.find_all('tr', class_=re.compile(r'ui-widget-content'))
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    entidad = cols[1].text.strip()
                    descripcion = cols[2].text.strip()
                    fecha_propuestas = cols[4].text.strip() if len(cols) > 4 else "Vigente"
                    proceso_id = f"{entidad}-{descripcion}"
                    
                    found_processes.append({
                        "id": proceso_id,
                        "entidad": entidad,
                        "descripcion": descripcion,
                        "monto": "Consultar Ficha",
                        "fecha_presentacion": fecha_propuestas
                    })
    except Exception as e:
        print(f"⚠️ Error escaneando término '{keyword}': {e}")
        
    return found_processes

def main():
    print("🔎 Iniciando rastreo de licitaciones vigentes en el SEACE...")
    
    history_file = "processed_ids.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                processed_ids = set(json.load(f))
        except Exception:
            processed_ids = set()
    else:
        processed_ids = set()

    print(f"📡 Escaneando {len(KEYWORDS)} filtros en búsqueda de propuestas activas...")
    
    for kw in KEYWORDS:
        procesos = query_active_seace_processes(kw)
        for proc in procesos:
            proc_id = proc.get("id")
            if proc_id and proc_id not in processed_ids:
                proc["keyword"] = kw
                send_telegram_alert(proc)
                processed_ids.add(proc_id)

    with open(history_file, "w") as f:
        json.dump(list(processed_ids), f)
        
    print("✅ Escaneo de licitaciones vigentes completado.")

if __name__ == "__main__":
    main()
