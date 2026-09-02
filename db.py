import sqlite3
import pandas as pd
import os
import sys
import re
import utils

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console(highlight=False)

SUPPORTED_SCHEMAS = [25]  

def get_schema_version(db_path):
    """Liest die Schema-Version aus der mAirList-Datenbank aus."""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE name = 'schemaversion'")
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return int(row[0])
        return None
    except Exception as e:
        utils.log_change("ERROR", f"Konnte Schema-Version nicht lesen: {e}")
        return None

def verify_db_compatibility(db_path):
    """Prüft, ob die DB-Version vom Restorer unterstützt wird und stoppt ggf. das Skript."""
    version = get_schema_version(db_path)
    if version is None:
        console.print("[bold red]Fehler: Konnte die Schema-Version der Datenbank nicht ermitteln. Ist das wirklich eine mAirList .mldb Datei?[/bold red]")
        sys.exit(1)
        
    if version not in SUPPORTED_SCHEMAS:
        console.print(Panel(f"[bold red]Inkompatible Datenbank![/bold red]\n\nDeine mAirList-Datenbank nutzt Schema-Version [bold yellow]{version}[/bold yellow].\nDieser Restorer (v{utils.APP_VERSION}) unterstützt aktuell nur die Versionen: [bold green]{SUPPORTED_SCHEMAS}[/bold green].\n\n[dim]Bitte wende dich an die Entwickler, um ein Update für dieses Schema zu erhalten.[/dim]", box=box.HEAVY, style="red"))
        sys.exit(1)
        
    return version

def detect_db_language(db_path, fallback_lang):
    """Liest ein paar Attribut-Namen aus und erkennt, welche Sprache in mAirList eingestellt ist."""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT name FROM item_attributes")
        names = [row[0].lower() for row in cur.fetchall()]
        conn.close()
        if 'year' in names or 'language' in names: return 'en'
        if 'jaar' in names or 'taal' in names: return 'nl'
        if 'jahr' in names or 'sprache' in names: return 'de'
        return fallback_lang
    except:
        return fallback_lang

def is_db_locked(db_path, timeout=1.0):
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        conn.execute("BEGIN IMMEDIATE")
        conn.rollback()
        conn.close()
        return False
    except sqlite3.OperationalError: return True
    except Exception: return False

def load_dataframe_from_mldb(db_path, ignored_folders=None):
    if not os.path.exists(db_path): 
        raise FileNotFoundError(utils.t('err_file_not_found', file=db_path))
    if ignored_folders is None: ignored_folders = []
    
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    
    try:
        items = pd.read_sql_query("SELECT * FROM items", conn)
        items['ID'] = items['idx'].astype(str)
        items['Title'] = items['title'] if 'title' in items.columns else ''
        items['Artist'] = items['artist'] if 'artist' in items.columns else ''
        items['ItemType'] = items['type'] if 'type' in items.columns else ''
        items['Filename'] = items['filename'] if 'filename' in items.columns else ''
        items['Duration'] = items['duration'] if 'duration' in items.columns else 0.0
        items['TotalDuration'] = items['totalduration'] if 'totalduration' in items.columns else 0.0
    except Exception as e:
        console.print(f"[red]Kritischer Fehler beim Lesen der mAirList Items: {e}[/red]")
        sys.exit(1)
            
    try:
        folder_df = pd.read_sql_query("SELECT * FROM folders", conn)
        folder_df = folder_df.dropna(subset=['idx'])
        folder_df['idx'] = folder_df['idx'].astype(int)
        f_dict = folder_df.set_index('idx').to_dict('index')
        
        def build_vpath(fid):
            parts = []
            try: curr = int(fid)
            except: return ""
            visited = set()
            while curr in f_dict and curr != 0 and curr not in visited:
                visited.add(curr)
                name = str(f_dict[curr].get('name', '')).strip()
                if name and name.lower() not in ['nan', 'none']: 
                    parts.insert(0, name)
                p_val = f_dict[curr].get('parent', 0)
                try: curr = int(p_val) if pd.notna(p_val) else 0
                except: curr = 0
            return " / ".join(parts).lower()
            
        vpath_map = {k: build_vpath(k) for k in f_dict.keys()}
        item_folders = {}
        
        try:
            folder_items_df = pd.read_sql_query("SELECT * FROM item_folders", conn)
            for _, r in folder_items_df.iterrows():
                try:
                    i_id = int(r['item'])
                    f_id = int(r['folder'])
                    if i_id not in item_folders:
                        item_folders[i_id] = []
                    if f_id in vpath_map:
                        item_folders[i_id].append(vpath_map[f_id])
                except: pass
        except Exception:
            try:
                folder_items_df = pd.read_sql_query("SELECT * FROM folder_items", conn)
                for _, r in folder_items_df.iterrows():
                    try:
                        i_id = int(r['item'])
                        f_id = int(r['folder'])
                        if i_id not in item_folders:
                            item_folders[i_id] = []
                        if f_id in vpath_map:
                            item_folders[i_id].append(vpath_map[f_id])
                    except: pass
            except: pass

    except Exception:
        item_folders = {}
        
    try:
        attrs = pd.read_sql_query("SELECT item AS ID, name, value FROM item_attributes", conn)
        
        # --- Wir mappen alle internationalen Attribute intern auf Deutsch ---
        def map_read_attr(n):
            nl = str(n).lower()
            if nl in ['year', 'jaar']: return 'Jahr'
            if nl in ['language', 'taal']: return 'Sprache'
            if nl in ['type', 'soort']: return 'Typ'
            return n
            
        attrs['name'] = attrs['name'].apply(map_read_attr)
    except:
        attrs = pd.DataFrame()
        
    conn.close()

    def is_ignored(row):
        try: item_id = int(row.get('ID', 0))
        except: item_id = 0
        fn = str(row.get('Filename', ''))
        if fn.lower() in ['nan', 'none']: fn = ""
        v_paths = item_folders.get(item_id, [])
        fn_norm = fn.replace('/', '\\').lower() if fn else ""
        for ign in ignored_folders:
            ign_str = str(ign).strip()
            if not ign_str: continue
            ign_lower = ign_str.lower()
            ign_norm = ign_str.replace('/', '\\').lower()
            for vpath in v_paths:
                v_parts = [p.strip() for p in vpath.split('/')]
                if ign_lower in v_parts: return True
                if ign_lower == vpath: return True
            if fn_norm:
                if '\\' in ign_norm or '/' in ign_norm:
                    if ign_norm in fn_norm: return True
                else:
                    parts = fn_norm.split('\\')
                    if ign_lower in parts: return True
        return False

    before_count = len(items)
    items = items[~items.apply(is_ignored, axis=1)].copy()
    skipped_count = before_count - len(items)
    
    if skipped_count > 0: 
        console.print(utils.t('ign_skip_count', count=skipped_count))

    if not attrs.empty:
        attrs['ID'] = attrs['ID'].astype(str)
        pivot = attrs.pivot_table(index='ID', columns='name', values='value', aggfunc='first').reset_index()
        df = items.merge(pivot, on='ID', how='left')
    else:
        df = items.copy()
        
    for col in utils.MLDB_ATTRIBUTE_FIELDS:
        if col not in df.columns: df[col] = ''
    return df

def apply_dataframe_to_mldb(df, db_path, mark_restauriert=True):
    db_lang = detect_db_language(db_path, utils.CURRENT_LANG)
    
    def map_write_attr(n):
        if db_lang == 'en':
            if n == 'Jahr': return 'Year'
            if n == 'Sprache': return 'Language'
            if n == 'Typ': return 'Type'
        elif db_lang == 'nl':
            if n == 'Jahr': return 'Jaar'
            if n == 'Sprache': return 'Taal'
            if n == 'Typ': return 'Soort'
        return n

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    updated = 0
    
    items_update = []
    attrs_insert = []
    restauriert_insert = []
    
    try:
        cur.execute("SELECT idx FROM items")
        valid_ids = {row[0] for row in cur.fetchall()}
        
        for _, row in df.iterrows():
            item_id = row.get('ID')
            if pd.isna(item_id) or not str(item_id).strip(): continue
            item_id = int(item_id)
            
            if item_id not in valid_ids: continue 
            
            title, artist = row.get('Title', ''), row.get('Artist', '')
            
            if pd.notna(title) or pd.notna(artist):
                t_val = title if pd.notna(title) and str(title).strip() else None
                a_val = artist if pd.notna(artist) and str(artist).strip() else None
                items_update.append((t_val, a_val, item_id))
            
            for field in utils.MLDB_ATTRIBUTE_FIELDS:
                value = row.get(field, '')
                if pd.notna(value) and str(value).strip():
                    db_field = map_write_attr(field)
                    attrs_insert.append((item_id, db_field, str(value).strip()))
                    
            if mark_restauriert:
                restauriert_insert.append((item_id, 'RESTAURIERT', 'JA'))
            
            utils.log_change("APPLY", f"ID {item_id}: {artist} - {title}")
            updated += 1
        
        if items_update:
            cur.executemany("UPDATE items SET title = COALESCE(?, title), artist = COALESCE(?, artist) WHERE idx = ?", items_update)
        if attrs_insert:
            cur.executemany("INSERT OR REPLACE INTO item_attributes (item, name, value) VALUES (?, ?, ?)", attrs_insert)
        if restauriert_insert:
            cur.executemany("INSERT OR REPLACE INTO item_attributes (item, name, value) VALUES (?, ?, ?)", restauriert_insert)
            
        conn.commit()
    finally:
        conn.close()
    return updated

def run_maintenance_genres(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT item, value FROM item_attributes WHERE name = 'Genre'")
    rows = cur.fetchall()
    updates = []
    for item_id, current_genre in rows:
        if not current_genre: continue
        mapped = utils.map_to_allowed_genre([current_genre], [])
        if mapped and mapped != current_genre:
            updates.append((mapped, item_id, 'Genre'))
    if updates:
        cur.executemany("UPDATE item_attributes SET value = ? WHERE item = ? AND name = ?", updates)
        conn.commit()
        utils.log_change("MAINTENANCE", f"{len(updates)} Genres bereinigt.")
    conn.close()
    return len(updates)

def run_maintenance_case(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT idx, artist, title FROM items")
    rows = cur.fetchall()
    updates = []
    for idx, artist, title in rows:
        changed = False
        new_art = artist
        new_tit = title
        
        if artist:
            new_art = re.sub(r"[´`‘’]", "'", str(artist))
            new_art = utils.capitalize_smart(new_art)
            if new_art != artist: changed = True
            
        if title:
            new_tit = re.sub(r"[´`‘’]", "'", str(title))
            new_tit = utils.capitalize_smart(new_tit)
            if new_tit != title: changed = True
            
        if changed:
            updates.append((new_art, new_tit, idx))
            
    if updates:
        cur.executemany("UPDATE items SET artist = ?, title = ? WHERE idx = ?", updates)
        conn.commit()
        utils.log_change("MAINTENANCE", f"{len(updates)} Tracks (Title Case / Apostroph) korrigiert.")
    conn.close()
    return len(updates)

def run_maintenance_clear_fields(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM item_attributes WHERE name IN ('Platinum Notes', 'PLATINUMNOTES', 'Lyrics', 'LYRICS')")
    deleted = cur.rowcount
    conn.commit()
    if deleted > 0:
        utils.log_change("MAINTENANCE", f"{deleted} alte Attribute (Lyrics/Platinum Notes) entfernt.")
    conn.close()
    return deleted

def run_maintenance_types(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT item, value FROM item_attributes WHERE name = 'Typ'")
    existing_types = {row[0]: str(row[1]).strip() for row in cur.fetchall()}
    
    cur.execute("SELECT idx, type FROM items")
    items = cur.fetchall()
    
    inserts = []
    for idx, item_type in items:
        if not item_type: continue
        
        if idx not in existing_types or not existing_types[idx]:
            translated = utils.ITEM_TYPE_MAPPING.get(item_type, '')
            if translated:
                inserts.append((idx, 'Typ', translated))
                
    if inserts:
        cur.executemany("INSERT OR REPLACE INTO item_attributes (item, name, value) VALUES (?, ?, ?)", inserts)
        conn.commit()
        utils.log_change("MAINTENANCE", f"{len(inserts)} Elementtypen (Typ) übersetzt.")
        
    conn.close()
    return len(inserts)