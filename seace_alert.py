import os
import json
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def main():
    print("🔎 Iniciando diagnóstico de conexión al portal SEACE 3.0...")
    
    with sync_playwright() as p:
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

        try:
            response = page.goto("https://prodapp2.seace.gob.pe/seace3-public/busqueda/busquedaProceso.xhtml", timeout=60000)
            page.wait_for_timeout(4000)
            
            print(f"📌 Estado HTTP: {response.status if response else 'Sin respuesta'}")
            print(f"📌 Título de página: '{page.title()}'")
            print(f"📌 URL final renderizada: {page.url}")
            
            # Extraer muestra de texto visible para confirmar si hay un firewall o bloqueo
            text_sample = page.locator("body").inner_text().replace("\n", " ").strip()[:300]
            print(f"📄 Contenido de pantalla: {text_sample}")
            
            # Contar marcos e inputs en el DOM
            print(f"🧩 Cantidad de marcos (iframes): {len(page.frames)}")
            print(f"⌨️ Cantidad de campos input detectados: {page.locator('input').count()}")

        except Exception as e:
            print(f"❌ Error durante la conexión: {e}")

        browser.close()

if __name__ == "__main__":
    main()
