import sqlite3
import pandas as pd
import os
import sys
import utils

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console(highlight=False)

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
        items['Filename'] = items['filename'] if 'filename' in items.columns else ''
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
            except:
                pass

    except Exception:
        item_folders = {}
        
    try:
        attrs = pd.read_sql_query("SELECT item AS ID, name, value FROM item_attributes", conn)
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
                if ign_lower in v_parts: 
                    return True
                if ign_lower == vpath:
                    return True
                
            if fn_norm:
                if '\\' in ign_norm or '/' in ign_norm:
                    if ign_norm in fn_norm:
                        return True
                else:
                    parts = fn_norm.split('\\')
                    if ign_lower in parts:
                        return True
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
                    attrs_insert.append((item_id, field, str(value).strip()))
                    
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