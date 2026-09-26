# crea eseguibile per il builder
pyinstaller --onefile --icon "icona1.ico" build_catalog.py
# crea eseguibile per la webapp
pyinstaller --onefile --name "CollectionBrowser" --add-data "templates;templates" app.py
# crea eseguibile per la webapp con icona personalizzata
pyinstaller --onefile --name "CollectionBrowser" --icon "icona2.ico" --add-data "templates;templates" app.py


# AI Model
Come integrare l'IA nel tuo script build_catalog_ai.py

1. Installa e avvia Ollama
Scarica Ollama da ollama.com e installalo.

2. Apri il terminale del tuo PC e scarica il modello avviando:
Bash
ollama run llama3