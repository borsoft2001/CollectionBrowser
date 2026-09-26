import os
import sqlite3
import subprocess
import sys
import urllib.parse
from flask import Flask, render_template, request, jsonify, send_file, abort

app = Flask(__name__)
DB_PATH = "modellismo.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parent-folders', methods=['GET'])
def get_parent_folders():
    conn = get_db_connection()
    tags = conn.execute("SELECT id, name FROM tags WHERE name LIKE 'Padre:%' ORDER BY name ASC").fetchall()
    conn.close()
    return jsonify([dict(t) for t in tags])

@app.route('/api/sub-folders', methods=['GET'])
def get_sub_folders():
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
    query = request.args.get('q', '').strip() or request.args.get('search', '').strip()
    parents = request.args.getlist('parents')
    subs = request.args.getlist('subs')
    selected_tags = request.args.getlist('tags')
    if len(selected_tags) == 1 and ',' in selected_tags[0]:
        selected_tags = [t.strip() for t in selected_tags[0].split(',') if t.strip()]
    conn = get_db_connection()
    params = []
    sql = "SELECT f.id, f.filename, f.filepath, f.file_type, f.size_bytes, f.updated_at FROM files f"
    if parents:
        placeholders = ', '.join(['?'] * len(parents))
        sql += f" JOIN file_tags ft_p ON f.id = ft_p.file_id AND ft_p.tag_id IN ({placeholders})"
        params.extend(parents)
    if subs:
        placeholders = ', '.join(['?'] * len(subs))
        sql += f" JOIN file_tags ft_s ON f.id = ft_s.file_id AND ft_s.tag_id IN ({placeholders})"
        params.extend(subs)
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
    if selected_tags:
        sql += f" HAVING COUNT(DISTINCT ft_c.tag_id) = {len(selected_tags)}"
    sql += " ORDER BY f.filename ASC LIMIT 300"
    files = conn.execute(sql, params).fetchall()
    result = []
    for f in files:
        file_dict = dict(f)
        file_tags = conn.execute("""
            SELECT t.id, t.name FROM tags t JOIN file_tags ft ON t.id = ft.tag_id
            WHERE ft.file_id = ? ORDER BY t.name ASC
        """, (file_dict['id'],)).fetchall()
        file_dict['tags'] = [t['name'] for t in file_tags]
        result.append(file_dict)
    conn.close()
    return jsonify(result)

@app.route('/api/media', methods=['GET'])
@app.route('/api/preview', methods=['GET'])
def get_media():
    raw_path = request.args.get('filepath') or request.args.get('path', '')
    if not raw_path:
        return abort(400, "Percorso mancante")
    clean_path = os.path.normpath(urllib.parse.unquote(raw_path))
    if not os.path.exists(clean_path) or not os.path.isfile(clean_path):
        return "File non trovato", 404
    try:
        return send_file(clean_path)
    except Exception as e:
        return f"Errore apertura file: {e}", 500

def get_existing_file_path(filepath):
    if not filepath:
        return None
    path = os.path.normpath(filepath)
    return path if os.path.isfile(path) else None

@app.route('/api/open', methods=['POST'])
def open_file():
    filepath = (request.json or {}).get('filepath')
    path = get_existing_file_path(filepath)
    if not path:
        return jsonify({"status": "error", "message": "File non trovato"}), 404
    try:
        if sys.platform.startswith('win'):
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/select-file', methods=['POST'])
def select_file():
    filepath = (request.json or {}).get('filepath')
    path = get_existing_file_path(filepath)
    if not path:
        return jsonify({"status": "error", "message": "File non trovato"}), 404
    try:
        if sys.platform.startswith('win'):
            subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-R', path])
        else:
            subprocess.Popen(['xdg-open', os.path.dirname(path)])
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("Avvio Web App su http://127.0.0.1:5000")
    app.run(debug=False, port=5000)
