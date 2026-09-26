# crea eseguibile per il builder
pyinstaller --onefile build_catalog.py
# crea eseguibile per la webapp
pyinstaller --onefile --name "CollectionBrowser" --add-data "templates;templates" app.py