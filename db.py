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
    version = get_schema_version(db_path)
    if version is None:
        console.print("[bold red]Fehler: Konnte die Schema-Version der Datenbank nicht ermitteln. Ist das wirklich eine mAirList .mldb Datei?[/bold red]")
        sys.exit(1)
        
    if version not in SUPPORTED_SCHEMAS:
        console.print(Panel(f"[bold red]Inkompatible Datenbank![/bold red]\n\nDeine mAirList-Datenbank nutzt Schema-Version [bold yellow]{version}[/bold yellow].\nDieser Restorer (v{utils.APP_VERSION}) unterstützt aktuell nur die Versionen: [bold green]{SUPPORTED_SCHEMAS}[/bold green].\n\n[dim]Bitte wende dich an die Entwickler, um ein Update für dieses Schema zu erhalten.[/dim]", box=box.HEAVY, style="red"))
        sys.exit(1)
        
    return version

def detect_db_language(db_path, fallback_lang):
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
    import sqlite3
    import utils
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    updates_made = 0
    
    cur.execute("PRAGMA table_info(items)")
    items_cols = [row[1].lower() for row in cur.fetchall()]
    has_native_genre = 'genre' in items_cols
    id_col = next((c for c in ['idx', 'id', 'itemidx'] if c in items_cols), None)
    
    if has_native_genre and id_col:
        cur.execute(f"SELECT {id_col}, genre FROM items")
        rows = cur.fetchall()
        updates = []
        for item_id, current_genre in rows:
            if not current_genre: continue
            mapped = utils.map_to_allowed_genre([current_genre], [])
            if mapped and mapped != current_genre:
                updates.append((mapped, item_id))
        if updates:
            cur.executemany(f"UPDATE items SET genre = ? WHERE {id_col} = ?", updates)
            updates_made += len(updates)
            
    cur.execute("PRAGMA table_info(item_attributes)")
    attr_cols = [row[1].lower() for row in cur.fetchall()]
    
    if not attr_cols:
        cur.execute("PRAGMA table_info(attributes)")
        attr_cols = [row[1].lower() for row in cur.fetchall()]
        attr_table = "attributes"
    else:
        attr_table = "item_attributes"
        
    if attr_cols:
        attr_id_col = next((c for c in ['item', 'itemidx', 'itemid', 'idx', 'id'] if c in attr_cols), None)
        if attr_id_col:
            cur.execute(f"SELECT {attr_id_col}, name, value FROM {attr_table} WHERE LOWER(name) = 'genre'")
            rows = cur.fetchall()
            updates = []
            for item_id, attr_name, current_genre in rows:
                if not current_genre: continue
                mapped = utils.map_to_allowed_genre([current_genre], [])
                if mapped and mapped != current_genre:
                    updates.append((mapped, item_id, attr_name))
            if updates:
                cur.executemany(f"UPDATE {attr_table} SET value = ? WHERE {attr_id_col} = ? AND name = ?", updates)
                updates_made += len(updates)
                
    conn.commit()
    if updates_made > 0:
        utils.log_change("MAINTENANCE", f"{updates_made} Genres bereinigt.")
    conn.close()
    return updates_made

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

def run_maintenance_file_tagger(db_path):
    try:
        import mutagen
        from mutagen.id3 import ID3, TPE1, TIT2, TDRC, TCON, TALB, TPUB
    except ImportError:
        import sys
        from rich.console import Console
        Console().print("\n[bold red]KRITISCHER FEHLER: Das Python-Modul 'mutagen' ist nicht installiert![/bold red]")
        Console().print("[yellow]Bitte öffne dein Terminal und tippe: pip install mutagen[/yellow]")
        return 0

    import sqlite3
    import logging
    import os
    from rich.console import Console
    c = Console(highlight=False)

    c.print("\n[cyan]=== Lokale Pfad-Zuordnung ===[/cyan]")
    c.print("Da mAirList Speicherorte (Storage Locations) nutzt, stehen in der DB oft nur relative Pfade")
    c.print("(z.B. 'Filler/Song.mp3'). Ziehe hier nacheinander die Hauptordner rein, in denen das Skript suchen soll.")
    c.print("[dim](Lass das Feld leer und drücke Enter, wenn du alle Ordner hinzugefügt hast)[/dim]")
    
    base_dirs = []
    while True:
        d = c.input("Basis-Ordner reinziehen (oder Enter zum Starten): ").strip().strip('"').strip("'")
        if not d:
            break
        if os.path.isdir(d):
            base_dirs.append(d)
            c.print(f"[green]✓ Ordner '{d}' zur Suchliste hinzugefügt.[/green]")
        else:
            c.print("[red]Ordner existiert nicht oder ist ungültig. Bitte erneut versuchen.[/red]")

    c.print("\n[magenta]Lese Dateien und schreibe Tags... (Das kann je nach Archivgröße dauern)[/magenta]")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(items)")
    items_cols = [row[1].lower() for row in cursor.fetchall()]
    id_col = next((c_name for c_name in ['idx', 'id', 'itemidx'] if c_name in items_cols), None)
    
    cursor.execute("PRAGMA table_info(item_attributes)")
    attr_cols = [row[1].lower() for row in cursor.fetchall()]
    if not attr_cols:
        cursor.execute("PRAGMA table_info(attributes)")
        attr_cols = [row[1].lower() for row in cursor.fetchall()]
        attr_table = "attributes"
    else:
        attr_table = "item_attributes"
    attr_id_col = next((c_name for c_name in ['item', 'itemidx', 'itemid', 'idx', 'id'] if c_name in attr_cols), None)
    
    if not id_col or not attr_id_col:
        conn.close()
        return 0

    query = f"""
    SELECT i.{id_col}, i.artist, i.title, i.filename,
           MAX(CASE WHEN a.name IN ('Jahr', 'Year', 'Jaar') THEN a.value END) as year,
           MAX(CASE WHEN a.name = 'Genre' THEN a.value END) as genre,
           MAX(CASE WHEN a.name = 'Album' THEN a.value END) as album,
           MAX(CASE WHEN a.name = 'Label' THEN a.value END) as label
    FROM items i
    LEFT JOIN {attr_table} a ON i.{id_col} = a.{attr_id_col}
    WHERE i.filename IS NOT NULL AND i.filename != ''
    GROUP BY i.{id_col}
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    stat_total = len(rows)
    stat_not_found = 0
    stat_unsupported = 0
    stat_already_perfect = 0
    updated_count = 0

    for row in rows:
        item_id, artist, title, raw_filename, year, genre, album, label = row

        filename = str(raw_filename).replace('\\', '/')
        actual_path = None
        
        if os.path.exists(filename) and os.path.isfile(filename):
            actual_path = filename
        else:
            for b_dir in base_dirs:
                test_path = os.path.join(b_dir, filename.lstrip('/'))
                if os.path.exists(test_path) and os.path.isfile(test_path):
                    actual_path = test_path
                    break

        if not actual_path:
            stat_not_found += 1
            if stat_not_found <= 5:
                c.print(f"[dim yellow]DEBUG Info: Suche erfolglos -> {filename}[/dim yellow]")
            continue

        c_artist = str(artist).strip() if artist else ""
        c_title = str(title).strip() if title else ""
        c_year = str(year).strip() if year else ""
        c_genre = str(genre).strip() if genre else ""
        c_album = str(album).strip() if album else ""
        c_label = str(label).strip() if label else ""

        try:
            audio = mutagen.File(actual_path)
            if audio is None: 
                stat_unsupported += 1
                continue
            
            changed = False
            file_type = type(audio).__name__

            if file_type in ['FLAC', 'OggVorbis']:
                def set_vorbis(tag, val):
                    nonlocal changed
                    if val:
                        if audio.get(tag) != [val]:
                            audio[tag] = [val]
                            changed = True
                            
                set_vorbis('artist', c_artist)
                set_vorbis('title', c_title)
                set_vorbis('date', c_year)
                set_vorbis('genre', c_genre)
                set_vorbis('album', c_album)
                set_vorbis('organization', c_label)
                
                if changed:
                    audio.save()
                    updated_count += 1
                else:
                    stat_already_perfect += 1

            elif file_type in ['MP3', 'AIFF']:
                if not getattr(audio, 'tags', None):
                    try:
                        audio.add_tags()
                    except:
                        stat_unsupported += 1
                        continue 

                def set_id3(frame_class, val):
                    nonlocal changed
                    if val:
                        frame_id = frame_class.__name__
                        existing = audio.tags.getall(frame_id)
                        if not existing or str(existing[0].text[0]) != str(val):
                            audio.tags.setall(frame_id, [frame_class(encoding=3, text=[val])])
                            changed = True

                set_id3(TPE1, c_artist)
                set_id3(TIT2, c_title)
                set_id3(TDRC, c_year)
                set_id3(TCON, c_genre)
                set_id3(TALB, c_album)
                set_id3(TPUB, c_label) 
                
                if changed:
                    audio.save()
                    updated_count += 1
                else:
                    stat_already_perfect += 1
            else:
                stat_unsupported += 1

        except Exception as e:
            logging.error(f"FILE-TAGGER ERROR bei Datei {actual_path}: {str(e)}")
            stat_unsupported += 1
            continue

    logging.info(f"MAINTENANCE: {updated_count} Dateien getaggt. (Nicht gefunden: {stat_not_found})")
    
    c.print(f"\n[cyan]=== Tagger-Diagnose ===[/cyan]")
    c.print(f"Tracks in Datenbank mit Pfad: [bold]{stat_total}[/bold]")
    c.print(f"Pfade/Dateien nicht gefunden: [bold yellow]{stat_not_found}[/bold yellow]")
    c.print(f"Nicht unterstütztes Format  : [bold yellow]{stat_unsupported}[/bold yellow]")
    c.print(f"Tags waren bereits perfekt  : [bold green]{stat_already_perfect}[/bold green]")
    c.print(f"Dateien erfolgreich getaggt : [bold green]{updated_count}[/bold green]\n")

    return updated_count