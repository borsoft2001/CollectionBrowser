import os
import re
import json
import sqlite3
import requests
from datetime import datetime

# ==========================================
# CONFIGURAZIONI E FILE LOCALI
# ==========================================
CONFIG_FILE = "cartelle.txt"
MAPPING_FILE = "tag_mapping.json"
DB_FILE = "modellismo.db"
OLLAMA_URL = "http://localhost:11434"

# Mappatura iniziale di base (utilizzata solo la prima volta per creare tag_mapping.json)
DEFAULT_TAG_MAPPING = {
    "GW": [r"\bgw\b", r"games workshop", r"whtv"],
    "Ultramarines": [r"ultramarine", r"ultramarines", r"\bum_"],
    "Space Marines": [r"space marine", r"space marines", r"adeptus astartes"],
    "Blood Angels": [r"blood angel", r"blood angels", r"death company"],
    "Dark Angels": [r"dark angel", r"dark angels", r"ravenwing", r"deathwing"],
    "Orks / Orruk": [r"\bork\b", r"\borks\b", r"orruk", r"grot"],
    "Necrons": [r"necron", r"necrons"],
    "HeroQuest": [r"heroquest", r"hero quest"],
    "Captain / Commander": [r"captain", r"commander", r"capitano"],
    "Basette": [r"\bbase\b", r"\bbases\b", r"basette", r"basetta"],
    "Metallo / NMM": [r"gold", r"nmm", r"metallics"]
}

# Variable globale per tracciare lo stato di Ollama
OLLAMA_AVAILABLE = False


# ==========================================
# 1. VERIFICA OLLAMA & GESTIONE FILE LOCALI
# ==========================================
def check_ollama_status():
    """Verifica una sola volta se Ollama è attivo e raggiungibile."""
    global OLLAMA_AVAILABLE
    try:
        # Timeout rapido a 1.0 secondo per non rallentare l'avvio
        response = requests.get(f"{OLLAMA_URL}/api/version", timeout=1.0)
        if response.status_code == 200:
            OLLAMA_AVAILABLE = True
            print("[INFO] Ollama è attivo e pronto. L'IA genererà nuove regole se necessario.")
            return True
    except Exception:
        pass

    OLLAMA_AVAILABLE = False
    print("[AVVISO] Ollama non è in esecuzione o non risponde. Verrà utilizzato solo il file 'tag_mapping.json' locale.")
    return False


def load_or_create_tag_mapping(filepath=MAPPING_FILE):
    """Carica TAG_MAPPING dal file JSON locale. Se non esiste, lo crea con le regole base."""
    if not os.path.exists(filepath):
        print(f"File '{filepath}' non trovato. Creazione in corso con i tag di base...")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_TAG_MAPPING, f, ensure_ascii=False, indent=2)
        return DEFAULT_TAG_MAPPING

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore nella lettura di {filepath}: {e}")
        return DEFAULT_TAG_MAPPING


def save_tag_mapping(mapping, filepath=MAPPING_FILE):
    """Salva il dizionario TAG_MAPPING aggiornato nel file JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def load_or_create_folders_config(config_path=CONFIG_FILE):
    """Legge le cartelle da scansionare."""
    default_folders = [
        r"C:\Wargames\Folder 1",
        r"C:\Wargames\Folder 2",
    ]
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            for folder in default_folders:
                f.write(folder + "\n")
        return default_folders

    folders = []
    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            path = line.strip()
            if path and not path.startswith("#"):
                folders.append(path)
    return folders


# ==========================================
# 2. ESTRAZIONE TAG & APPRENDIMENTO IA
# ==========================================
def extract_folder_levels(file_path, target_folders):
    """Estrae la Cartella Padre e Sub-cartella."""
    tags = set()
    norm_path = os.path.normpath(file_path)

    for target in target_folders:
        norm_target = os.path.normpath(target)
        if norm_path.startswith(norm_target):
            parent_name = os.path.basename(norm_target)
            tags.add(f"Padre: {parent_name}")

            rel_path = os.path.relpath(norm_path, norm_target)
            parts = rel_path.split(os.sep)

            if len(parts) > 1:
                tags.add(f"Sub: {parent_name} / {parts[0]}")
            else:
                tags.add(f"Sub: {parent_name} / (Radice)")
            break
    return tags


def extract_regex_tags(file_path, tag_mapping):
    """Analizza il file usando il dizionario TAG_MAPPING dinamico."""
    tags = set()
    for tag_name, patterns in tag_mapping.items():
        for pattern in patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                tags.add(tag_name)
                break
    return tags


def ask_ai_for_new_rules(file_path):
    """Chiede all'IA di identificare un nuovo Tag. Eseguita SOLO se Ollama è attivo."""
    if not OLLAMA_AVAILABLE:
        return None, None

    prompt = f"""
    Analizza il seguente percorso file di modellismo/giochi da tavolo: "{file_path}"
    
    Identifica il soggetto principale o franchise (es: "HeroQuest", "Space Marines", "Hasbro", "Barbarian").
    Estrai la parola chiave precisa presente nel percorso che lo identifica.

    Rispondi ESCLUSIVAMENTE con un JSON con questo formato esatto:
    {{
      "tag_name": "Nome Del Tag Pulito",
      "keyword": "parolachiave"
    }}
    """
    try:
        response = requests.post(
            f'{OLLAMA_URL}/api/generate',
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=3.0 # Timeout breve per evitare rallentamenti
        )
        if response.status_code == 200:
            data = json.loads(response.json().get('response', '{}'))
            tag_name = data.get("tag_name", "").strip()
            keyword = data.get("keyword", "").strip().lower()
            if tag_name and keyword:
                return tag_name, keyword
    except Exception:
        pass
    return None, None


# ==========================================
# 3. GESTIONE DATABASE SQLITE
# ==========================================
def init_db(db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT UNIQUE NOT NULL,
            file_type TEXT,
            size_bytes INTEGER,
            updated_at DATETIME
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_tags (
            file_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (file_id, tag_id),
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def insert_or_get_tag(cursor, tag_name):
    cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    return cursor.fetchone()[0]


# ==========================================
# 4. CICLO PRINCIPALE DI SCANSIONE
# ==========================================
def scan_and_populate_db(folders_to_scan, db_path=DB_FILE):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Controlla lo stato di Ollama una sola volta
    check_ollama_status()

    # Carica la mappatura tag dal file JSON locale
    tag_mapping = load_or_create_tag_mapping(MAPPING_FILE)
    mapping_updated = False

    total_files = 0
    print("\nInizio scansione delle cartelle...")

    for folder in folders_to_scan:
        if not os.path.exists(folder):
            print(f"[ATTENZIONE] Cartella non trovata: {folder}")
            continue

        print(f"Scansione cartella: {folder}")

        for root, _, files in os.walk(folder):
            for file in files:
                full_path = os.path.join(root, file)
                filename = os.path.basename(full_path)
                ext = os.path.splitext(filename)[1].lower().replace('.', '')
                
                try:
                    stat = os.stat(full_path)
                    size_bytes = stat.st_size
                    updated_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
                except Exception:
                    size_bytes = 0
                    updated_at = datetime.now().isoformat()

                cursor.execute("""
                    INSERT INTO files (filename, filepath, file_type, size_bytes, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(filepath) DO UPDATE SET
                        filename=excluded.filename,
                        file_type=excluded.file_type,
                        size_bytes=excluded.size_bytes,
                        updated_at=excluded.updated_at
                """, (filename, full_path, ext, size_bytes, updated_at))

                cursor.execute("SELECT id FROM files WHERE filepath = ?", (full_path,))
                file_id = cursor.fetchone()[0]

                # 1. Estragga i tag di cartella
                folder_tags = extract_folder_levels(full_path, folders_to_scan)
                
                # 2. Estragga i tag usando le RegEx di TAG_MAPPING locale
                content_tags = extract_regex_tags(full_path, tag_mapping)

                # 3. SE le RegEx non hanno trovato nulla E Ollama è attivo, chiedi una nuova regola
                if not content_tags and OLLAMA_AVAILABLE:
                    new_tag, new_keyword = ask_ai_for_new_rules(full_path)
                    if new_tag and new_keyword:
                        regex_pattern = r"\b" + re.escape(new_keyword) + r"\b"
                        
                        if new_tag in tag_mapping:
                            if regex_pattern not in tag_mapping[new_tag]:
                                tag_mapping[new_tag].append(regex_pattern)
                        else:
                            tag_mapping[new_tag] = [regex_pattern]
                        
                        content_tags.add(new_tag)
                        mapping_updated = True
                        print(f"  [IA -> TAG_MAPPING] Nuova regola aggiunta: '{new_tag}' -> '{new_keyword}'")

                all_extracted_tags = folder_tags.union(content_tags)

                cursor.execute("DELETE FROM file_tags WHERE file_id = ?", (file_id,))
                for tag_name in all_extracted_tags:
                    tag_id = insert_or_get_tag(cursor, tag_name)
                    cursor.execute("INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?, ?)", (file_id, tag_id))

                total_files += 1

    conn.commit()
    conn.close()

    # Se l'IA ha generato nuove regole, salva il file locale tag_mapping.json
    if mapping_updated:
        save_tag_mapping(tag_mapping, MAPPING_FILE)
        print(f"\n[OK] Il file '{MAPPING_FILE}' è stato aggiornato con le nuove regole dell'IA!")

    print(f"\nScansione completata! Elaborati {total_files} file. Database pronto: '{db_path}'.")


# ==========================================
# 5. MAIN
# ==========================================
if __name__ == "__main__":
    target_folders = load_or_create_folders_config(CONFIG_FILE)
    scan_and_populate_db(target_folders, db_path=DB_FILE)