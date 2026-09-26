import sqlite3
import os
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
DB_PATH = "modellismo.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Pagina principale."""
    return render_template('index.html')

@app.route('/api/parent-folders', methods=['GET'])
def get_parent_folders():
    """Restituisce le Cartelle Padre principali (Filtro 1)."""
    conn = get_db_connection()
    tags = conn.execute("SELECT id, name FROM tags WHERE name LIKE 'Padre:%' ORDER BY name ASC").fetchall()
    conn.close()
    return jsonify([dict(t) for t in tags])

@app.route('/api/sub-folders', methods=['GET'])
def get_sub_folders():
    """
    Restituisce le sottocartelle di Primo Livello (Filtro 2).
    Se sono selezionate delle Cartelle Padre, mostra solo il primo livello ad esse appartenente (OR).
    """
    selected_parents = request.args.getlist('parents')
    conn = get_db_connection()

    if selected_parents:
        placeholders = ', '.join(['?'] * len(selected_parents))
        sql = f"""
            SELECT DISTINCT t_sub.id, t_sub.name 
            FROM tags t_sub
            JOIN file_tags ft_sub ON t_sub.id = ft_sub.tag_id
            WHERE t_sub.name LIKE 'Sub:%'
            AND ft_sub.file_id IN (
                SELECT DISTINCT file_id FROM file_tags WHERE tag_id IN ({placeholders})
            )
            ORDER BY t_sub.name ASC
        """
        tags = conn.execute(sql, selected_parents).fetchall()
    else:
        tags = conn.execute("SELECT id, name FROM tags WHERE name LIKE 'Sub:%' ORDER BY name ASC").fetchall()

    conn.close()
    return jsonify([dict(t) for t in tags])

@app.route('/api/content-tags', methods=['GET'])
def get_content_tags():
    """
    Restituisce i tag di contenuto (Filtro 3).
    Mostra SOLO i tag presenti nei file appartenenti alle Cartelle Padre (OR)
    e/o alle Sottocartelle di Primo Livello (OR) attualmente selezionate.
    """
    parents = request.args.getlist('parents')
    subs = request.args.getlist('subs')
    conn = get_db_connection()

    params = []
    folder_conditions = []

    if parents:
        placeholders = ', '.join(['?'] * len(parents))
        folder_conditions.append(f"ft.file_id IN (SELECT file_id FROM file_tags WHERE tag_id IN ({placeholders}))")
        params.extend(parents)

    if subs:
        placeholders = ', '.join(['?'] * len(subs))
        folder_conditions.append(f"ft.file_id IN (SELECT file_id FROM file_tags WHERE tag_id IN ({placeholders}))")
        params.extend(subs)

    where_clause = "WHERE t.name NOT LIKE 'Padre:%' AND t.name NOT LIKE 'Sub:%'"
    if folder_conditions:
        where_clause += " AND " + " AND ".join(folder_conditions)

    sql = f"""
        SELECT DISTINCT t.id, t.name 
        FROM tags t
        JOIN file_tags ft ON t.id = ft.tag_id
        {where_clause}
        ORDER BY t.name ASC
    """
    
    tags = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tags])

@app.route('/api/files', methods=['GET'])
def search_files():
    """
    Cerca i file applicando:
    - Logica OR sulle Cartelle Padre
    - Logica OR sulle Sottocartelle di Primo Livello
    - Logica AND sui Tag di Contenuto
    """
    query = request.args.get('q', '').strip()
    parents = request.args.getlist('parents')
    subs = request.args.getlist('subs')
    selected_tags = request.args.getlist('tags')

    conn = get_db_connection()
    params = []

    sql = "SELECT f.id, f.filename, f.filepath, f.file_type, f.size_bytes, f.updated_at FROM files f"
    
    # 1. Filtro Padre in OR
    if parents:
        placeholders = ', '.join(['?'] * len(parents))
        sql += f" JOIN file_tags ft_p ON f.id = ft_p.file_id AND ft_p.tag_id IN ({placeholders})"
        params.extend(parents)

    # 2. Filtro Sottocartelle Primo Livello in OR
    if subs:
        placeholders = ', '.join(['?'] * len(subs))
        sql += f" JOIN file_tags ft_s ON f.id = ft_s.file_id AND ft_s.tag_id IN ({placeholders})"
        params.extend(subs)

    # 3. Filtro Tag Contenuto in AND
    if selected_tags:
        placeholders = ', '.join(['?'] * len(selected_tags))
        sql += f" JOIN file_tags ft_c ON f.id = ft_c.file_id AND ft_c.tag_id IN ({placeholders})"
        params.extend(selected_tags)

    where_clauses = []
    if query:
        where_clauses.append("(f.filename LIKE ? OR f.filepath LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += " GROUP BY f.id"

    # Garantisce la logica AND sui tag di contenuto scelti
    if selected_tags:
        sql += f" HAVING COUNT(DISTINCT ft_c.tag_id) = {len(selected_tags)}"

    sql += " ORDER BY f.filename ASC LIMIT 300"

    files = conn.execute(sql, params).fetchall()

    result = []
    for f in files:
        file_dict = dict(f)
        tags_query = """
            SELECT t.id, t.name 
            FROM tags t 
            JOIN file_tags ft ON t.id = ft.tag_id 
            WHERE ft.file_id = ?
            ORDER BY t.name ASC
        """
        file_tags = conn.execute(tags_query, (file_dict['id'],)).fetchall()
        file_dict['tags'] = [dict(t) for t in file_tags]
        result.append(file_dict)

    conn.close()
    return jsonify(result)

@app.route('/api/media')
def get_media():
    """Streaming di immagini, PDF e video per le anteprime."""
    filepath = request.args.get('filepath')
    if filepath and os.path.exists(filepath):
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        return send_from_directory(directory, filename)
    return "File non trovato", 404

@app.route('/api/open', methods=['POST'])
def open_file():
    """Apre il file direttamente nel sistema operativo locale."""
    data = request.json
    filepath = data.get('filepath')
    
    if filepath and os.path.exists(filepath):
        os.startfile(filepath)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "File non trovato"}), 404

if __name__ == '__main__':
    print("Avvio Web App su http://127.0.0.1:5000")
    app.run(debug=False, port=5000)