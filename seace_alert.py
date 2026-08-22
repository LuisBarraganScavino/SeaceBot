name: Evaluador SEACE

on:
  schedule:
    # Se ejecuta de lunes a viernes cada 3 horas en horario laboral peruano
    - cron: '0 13,16,19,22 * * 1-5'
  workflow_dispatch:

jobs:
  check-seace:
    runs-on: ubuntu-latest
    steps:
      - name: Descargar Código
        uses: actions/checkout@v3

      - name: Configurar Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Instalar Dependencias
        run: pip install requests

      - name: Ejecutar Rastreador
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python seace_alert.py

      - name: Guardar Registro de Vistos
        run: |
          git config --global user.name "SEACE-Bot"
          git config --global user.email "bot@github.com"
          git add processed_ids.json
          git commit -m "Update processed IDs" || exit 0
          git push
