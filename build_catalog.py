import os
import re
import sqlite3
from datetime import datetime

# ==========================================
# 1. MAPPATURA COMPLETA DEI TAG DI CONTENUTO
# ==========================================
TAG_MAPPING = {
    # -------------------------------------------------------------
    # 1. AUTORI / FONTI
    # -------------------------------------------------------------
    "GW": [r"\bgw\b", r"games workshop", r"whtv"],
    "Tale of Painters": [r"tale of painters", r"top_"],
    "Xenus Minis": [r"xenus minis"],
    "Mengel Miniatures": [r"mengel miniatures"],
    "Oishi Studio": [r"oishi studio"],
    "Marco Venturini": [r"marco venturini"],
    "Fanatic Army Painter": [r"fanatic army painter", r"\bfap_"],
    "Duncan Rhodes": [r"duncan rhodes"],
    "Awesome Paint Job": [r"awesome paint job"],

    # -------------------------------------------------------------
    # 2. FAZIONI / CAPITOLI / ESERCITI
    # -------------------------------------------------------------
    "Ultramarines": [r"ultramarine", r"ultramarines", r"\bum_"],
    "Space Marines": [r"space marine", r"space marines", r"adeptus astartes"],
    "Blood Angels": [r"blood angel", r"blood angels", r"death company"],
    "Dark Angels": [r"dark angel", r"dark angels", r"ravenwing", r"deathwing"],
    "Space Wolves": [r"space wolf", r"space wolves"],
    "Black Templars": [r"black templar", r"black templars"],
    "Imperial Fists": [r"imperial fist", r"imperial fists"],
    "White Scars": [r"white scar", r"white scars"],
    "Salamanders": [r"salamander", r"salamanders"],
    "Raven Guard": [r"raven guard"],
    "Grey Knights": [r"grey knight", r"grey knights", r"\bgk\b"],
    "Death Guard": [r"death guard", r"deathguard"],
    "Orks / Orruk": [r"\bork\b", r"\borks\b", r"orruk", r"grot", r"ironjawz", r"bonesplitterz"],
    "Necrons": [r"necron", r"necrons"],
    "Adeptus Custodes": [r"custodes", r"custodian"],
    "Adepta Sororitas": [r"sororitas", r"battle sister"],
    "Stormcast Eternals": [r"stormcast"],
    "Drukhari": [r"drukhari", r"dark eldar"],
    "Tau Empire": [r"\btau\b", r"tau empire"],
    "Nighthaunt": [r"nighthaunt"],
    "Idoneth Deepkin": [r"idoneth", r"deepkin"],
    "Kharadron Overlords": [r"kharadron"],

    # -------------------------------------------------------------
    # 3. MINIATURE, EROI E UNITA' SPECIFICHE
    # -------------------------------------------------------------
    "Guilliman": [r"guilliman"],
    "Marneus Calgar": [r"calgar"],
    "Intercessors": [r"intercessor", r"intercessors"],
    "Terminators": [r"terminator", r"terminators"],
    "Dreadnought": [r"dreadnought", r"redemptor"],
    "Aggressors": [r"aggressor", r"aggressors"],
    "Inceptors": [r"inceptor", r"inceptors"],
    "Hellblasters": [r"hellblaster", r"hellblasters"],
    "Repulsor": [r"repulsor"],
    "Chaplain": [r"chaplain", r"cappellano"],
    "Librarian": [r"librarian", r"bibliotecario"],
    "Apothecary": [r"apothecary", r"apotecario"],
    "Captain / Commander": [r"captain", r"commander", r"capitano"],
    "Mephiston": [r"mephiston"],
    "Lemartes": [r"lemartes"],
    "Sanguinary Guard": [r"sanguinary guard"],

    # Chaos / Death Guard / Nurgle
    "Mortarion": [r"mortarion"],
    "Typhus": [r"typhus"],
    "Plague Marines": [r"plague marine", r"plague marines"],
    "Poxwalkers": [r"poxwalker", r"poxwalkers"],
    "Blightlord Terminators": [r"blightlord"],
    "Foetid Bloat-Drone": [r"bloat-drone", r"bloat drone"],
    "Myphitic Blight-hauler": [r"blight-hauler", r"blight hauler"],
    "Great Unclean One": [r"great unclean one"],
    "Plaguebearers": [r"plaguebearer", r"plaguebearers"],

    # Necrons
    "Overlord": [r"overlord"],
    "Necron Warriors": [r"necron warrior", r"necron warriors"],
    "Immortals": [r"immortal", r"immortals"],
    "Lychguard": [r"lychguard"],
    "Canoptek Scarabs / Wraiths": [r"scarab", r"scarabs", r"wraith", r"wraiths"],
    "Monolith": [r"monolith"],

    # Age of Sigmar / Stormcast & Ghosts
    "Vandus Hammerhand": [r"vandus"],
    "Liberators": [r"liberator", r"liberators"],
    "Retributors": [r"retributor", r"retributors"],
    "Judicators": [r"judicator", r"judicators"],
    "Chainrasp": [r"chainrasp"],
    "Grimghast Reapers": [r"grimghast"],
    "Kurdoss Valentian": [r"kurdoss"],
    "Lady Olynder": [r"olynder"],

    # Orks
    "Ghazghkull": [r"ghazghkull", r"thraka"],
    "Boyz": [r"\bboyz\b", r"\bboy\b"],
    "Nobz": [r"\bnobz\b", r"\bnob\b"],
    "Deff Dread": [r"deff dread"],

    # -------------------------------------------------------------
    # 4. TECNICHE ED ELEMENTI DI PITTURA
    # -------------------------------------------------------------
    "Basette": [r"\bbase\b", r"\bbases\b", r"basette", r"basetta"],
    "Lame / Armi": [r"blade", r"blades", r"sword", r"nemesis", r"power sword"],
    "Stoffe / Mantelli": [r"cloth", r"cloths", r"robe", r"robes", r"cape", r"tabard"],
    "Pelle / Volto": [r"skin", r"flesh", r"pelle", r"viso", r"faces", r"stubble"],
    "Occhi / Lenti": [r"eye", r"lenses", r"occhi"],
    "Metallo / NMM": [r"gold", r"nmm", r"metallics", r"weathered gold"],
    "Plasma / Effetti Luce": [r"plasma", r"glow", r"glowing", r"warpflame"],
    "Gemme": [r"gem", r"gems", r"gemme"],
    "Secco / Lavature": [r"dry brush", r"drybrush", r"wash", r"washing", r"oil wash"],
    "Freehand": [r"freehand", r"free hand"],

    # -------------------------------------------------------------
    # 5. AMBIENTE / TERRENI
    # -------------------------------------------------------------
    "Scenici / Terreno": [r"terrain", r"scenery", r"ruins", r"manufactorum"],
    "Lava": [r"lava", r"volcanic", r"burning"],
    "Ghiaccio": [r"ice", r"frost"],
    "Palude": [r"swamp"],
    "Urbano / Marmo": [r"urban", r"road", r"marble"]
}


# ==========================================
# 2. FUNZIONI DI ESTRAZIONE LIVELLI E TAG
# ==========================================
def extract_folder_levels(file_path, target_folders):
    """Estrae la Cartella Padre (Livello 0) e il Primo Livello di sottocartella (Livello 1)."""
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


def extract_content_tags(file_path):
    """Analizza il file per estrarre SOLO i tag presenti nella mappatura TAG_MAPPING."""
    tags = set()

    # Estragga esclusivamente i tag definiti nelle RegEx di TAG_MAPPING
    for tag_name, patterns in TAG_MAPPING.items():
        for pattern in patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                tags.add(tag_name)
                break

    return tags


# ==========================================
# 3. GESTIONE DATABASE SQLITE
# ==========================================
def init_db(db_path="modellismo.db"):
    """Inizializza le tabelle del database SQLite."""
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
    """Inserisce un tag se non esiste e restituisce il suo ID."""
    cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    return cursor.fetchone()[0]


def scan_and_populate_db(folders_to_scan, db_path="modellismo.db"):
    """Scansiona ricorsivamente tutte le cartelle e popola il DB."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    total_files = 0
    print("Inizio scansione delle cartelle...")

    for folder in folders_to_scan:
        if not os.path.exists(folder):
            print(f"[ATTENZIONE] Cartella non trovata, saltata: {folder}")
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

                folder_tags = extract_folder_levels(full_path, folders_to_scan)
                content_tags = extract_content_tags(full_path)
                all_extracted_tags = folder_tags.union(content_tags)

                cursor.execute("DELETE FROM file_tags WHERE file_id = ?", (file_id,))

                for tag_name in all_extracted_tags:
                    tag_id = insert_or_get_tag(cursor, tag_name)
                    cursor.execute("INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?, ?)", (file_id, tag_id))

                total_files += 1

    conn.commit()
    conn.close()
    print(f"\nOperazione completata! Elaborati {total_files} file. Database pronto: '{db_path}'.")


# ==========================================
# 4. MAIN
# ==========================================
if __name__ == "__main__":
    TARGET_FOLDERS = [
        r"E:\\Wargames\\Sezione Modellismo\\01 Pittura",
        r"E:\\Wargames\\Sezione Modellismo\\80 Miniature 40K"
    ]

    scan_and_populate_db(TARGET_FOLDERS, db_path="modellismo.db")