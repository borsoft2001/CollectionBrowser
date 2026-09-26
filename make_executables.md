# crea eseguibile per il builder
pyinstaller --onefile build_catalog.py
# crea eseguibile per la webapp
pyinstaller --onefile --name "CollectionBrowser" --add-data "templates;templates" app.py
# crea eseguibile per la webapp con icona personalizzata
pyinstaller --onefile --name "CollectionBrowser" --icon "icona.ico" --add-data "templates;templates" app.py