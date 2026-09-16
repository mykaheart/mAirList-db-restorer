import sqlite3
import pandas as pd
import os
import sys
import re
import ntpath
import utils

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console(highlight=False)

SUPPORTED_SCHEMAS = [25]  

def get_schema_version(db_path):
    conn = None
    try:
        if not os.path.isfile(db_path):
            return None
        uri = f"file:{os.path.abspath(db_path)}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE name = 'schemaversion'")
        row = cur.fetchone()
        if row and row[0]:
            return int(row[0])
        return None
    except Exception as e:
        utils.log_change("ERROR", f"Konnte Schema-Version nicht lesen: {e}")
        return None
    finally:
        if conn is not None:
            conn.close()

def verify_db_compatibility(db_path):
    version = get_schema_version(db_path)
    if version is None:
        console.print(Panel(utils.t('db_invalid_file'), box=box.HEAVY, style="red"))
        return None

    if version not in SUPPORTED_SCHEMAS:
        console.print(Panel(
            utils.t('db_incompatible', version=version, supported=SUPPORTED_SCHEMAS, app_version=utils.APP_VERSION),
            box=box.HEAVY, style="red"
        ))
        return None

    return version

def detect_db_language(db_path, fallback_lang):
    conn = None
    try:
        uri = f"file:{os.path.abspath(db_path)}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT name FROM item_attributes")
        names = [str(row[0]).lower() for row in cur.fetchall()]
        if 'year' in names or 'language' in names: return 'en'
        if 'jaar' in names or 'taal' in names: return 'nl'
        if 'jahr' in names or 'sprache' in names: return 'de'
        return fallback_lang
    except Exception:
        return fallback_lang
    finally:
        if conn is not None:
            conn.close()

def is_db_locked(db_path, timeout=1.0):
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        conn.execute("BEGIN IMMEDIATE")
        conn.rollback()
        conn.close()
        return False
    except sqlite3.OperationalError: return True
    except Exception: return False

def check_integrity(db_path):
    """Run SQLite PRAGMA integrity_check in read-only mode."""
    conn = None
    try:
        uri = f"file:{os.path.abspath(db_path)}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        rows = conn.execute("PRAGMA integrity_check").fetchall()
        messages = [str(row[0]) for row in rows if row and row[0] is not None]
        ok = len(messages) == 1 and messages[0].strip().lower() == 'ok'
        return ok, ("OK" if ok else "; ".join(messages) or "Unknown integrity error")
    except Exception as e:
        utils.log_change("ERROR", f"Integritätsprüfung fehlgeschlagen: {e}")
        return False, str(e)
    finally:
        if conn is not None:
            conn.close()

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
        raise RuntimeError(f"items-Tabelle konnte nicht gelesen werden: {e}") from e
            
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

        # Lyrics/song texts are deliberately excluded from the temporary workspace.
        # They remain untouched in the original mAirList database.
        cache_excluded = {'lyrics', 'songtext', 'songtexte', 'song text'}
        attrs = attrs[~attrs['name'].astype(str).str.strip().str.lower().isin(cache_excluded)].copy()
        
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

def get_resolved_item_paths(db_path, item_ids=None):
    """Return absolute/canonical Windows-style audio paths keyed by item ID.

    mAirList usually stores filenames relative to a storage location. This helper
    combines items.filename with storages.defaultLocation in read-only mode. It
    deliberately does not require the files to exist on the machine running the
    Restorer; the paths are also useful for matching external library exports
    such as rekordbox XML.
    """
    wanted = None
    if item_ids is not None:
        wanted = {str(item_id).strip() for item_id in item_ids if str(item_id).strip()}
        if not wanted:
            return {}

    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        storage_rows = conn.execute(
            "SELECT idx, defaultLocation FROM storages"
        ).fetchall()
        storage_roots = {
            int(idx): str(root or '').strip()
            for idx, root in storage_rows
        }

        rows = conn.execute(
            "SELECT idx, storage, filename FROM items"
        ).fetchall()
        result = {}
        for item_id, storage_id, filename in rows:
            sid = str(item_id)
            if wanted is not None and sid not in wanted:
                continue
            raw = str(filename or '').strip()
            if not raw:
                continue
            raw = raw.replace('/', '\\')
            if ntpath.isabs(raw):
                full = raw
            else:
                try:
                    root = storage_roots.get(int(storage_id), '') if storage_id is not None else ''
                except (TypeError, ValueError):
                    root = ''
                full = ntpath.join(root.replace('/', '\\'), raw) if root else raw
            result[sid] = ntpath.normpath(full)
        return result
    finally:
        conn.close()


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

def _normalize_duplicate_text(value):
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text or text.lower() in ('nan', 'none'):
        return ""
    text = re.sub(r"[´`‘’]", "'", text)
    text = re.sub(r'\s+', ' ', text)
    return text.casefold()


def _normalize_duplicate_path(value):
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().strip('"').strip("'")
    if not text or text.lower() in ('nan', 'none'):
        return ""
    return re.sub(r'\\+', r'\\', text.replace('/', '\\')).casefold()


def _normalize_isrc(value):
    if value is None or pd.isna(value):
        return ""
    clean = re.sub(r'[^A-Za-z0-9]', '', str(value)).upper()
    return clean if len(clean) == 12 else ""


def find_duplicate_groups(df):
    """Find conservative duplicate-candidate groups without modifying the database.

    Candidates are linked when they share an exact normalized Artist+Title pair,
    the same stored file path, or the same valid 12-character ISRC. Different
    durations deliberately do not suppress a candidate: that decision belongs
    in the mAirList DB app during human review.
    """
    if df is None or df.empty or 'ID' not in df.columns:
        return []

    work = df.copy()
    work['ID'] = work['ID'].astype(str)
    work = work[work['ID'].str.strip() != ''].copy()

    # Duplicate maintenance is intended for music tracks. Empty ItemType is kept
    # for compatibility with databases where type information is incomplete.
    if 'ItemType' in work.columns:
        item_type = work['ItemType'].fillna('').astype(str).str.strip().str.casefold()
        work = work[(item_type == '') | (item_type == 'music')].copy()

    ids = list(work['ID'])
    parent = {item_id: item_id for item_id in ids}

    def find(item_id):
        while parent[item_id] != item_id:
            parent[item_id] = parent[parent[item_id]]
            item_id = parent[item_id]
        return item_id

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    def union_by_key(key_pairs):
        buckets = {}
        for item_id, key in key_pairs:
            if not key:
                continue
            buckets.setdefault(key, []).append(item_id)
        for members in buckets.values():
            if len(members) < 2:
                continue
            first = members[0]
            for member in members[1:]:
                union(first, member)

    artist_title_pairs = []
    for _, row in work.iterrows():
        artist = _normalize_duplicate_text(row.get('Artist', ''))
        title = _normalize_duplicate_text(row.get('Title', ''))
        key = (artist, title) if artist and title else None
        artist_title_pairs.append((str(row['ID']), key))
    union_by_key(artist_title_pairs)

    union_by_key([
        (str(row['ID']), _normalize_duplicate_path(row.get('Filename', '')))
        for _, row in work.iterrows()
    ])

    union_by_key([
        (str(row['ID']), _normalize_isrc(row.get('ISRC', '')))
        for _, row in work.iterrows()
    ])

    components = {}
    for item_id in ids:
        root = find(item_id)
        components.setdefault(root, set()).add(item_id)

    groups = [members for members in components.values() if len(members) >= 2]
    groups.sort(key=lambda members: (min(int(x) if str(x).isdigit() else 10**18 for x in members), len(members)))
    return groups


def get_duplicate_flag_state(db_path):
    """Return all existing DOPPELUNG attributes keyed by item ID."""
    conn = None
    try:
        uri = f"file:{os.path.abspath(db_path)}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        rows = conn.execute(
            "SELECT item, name, value FROM item_attributes WHERE LOWER(name) = 'doppelung'"
        ).fetchall()
        state = {}
        for item_id, name, value in rows:
            state.setdefault(str(item_id), []).append((str(name), '' if value is None else str(value)))
        return state
    finally:
        if conn is not None:
            conn.close()


def apply_duplicate_flags(db_path, candidate_ids):
    """Atomically synchronize the Restorer-managed DOPPELUNG=JA attributes."""
    candidate_ids = {str(item_id) for item_id in candidate_ids}
    state = get_duplicate_flag_state(db_path)
    existing_ids = set(state)
    existing_ja = {
        item_id for item_id, values in state.items()
        if any(value.strip().upper() == 'JA' for _, value in values)
    }

    stale_ids = existing_ids - candidate_ids
    new_or_changed_ids = candidate_ids - existing_ja
    unchanged_ids = candidate_ids & existing_ja

    if not stale_ids and not new_or_changed_ids:
        return {
            'new': 0,
            'unchanged': len(unchanged_ids),
            'removed': 0,
            'written': 0,
        }

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute('BEGIN IMMEDIATE')

        for item_id in sorted(stale_ids | new_or_changed_ids):
            cur.execute(
                "DELETE FROM item_attributes WHERE item = ? AND LOWER(name) = 'doppelung'",
                (int(item_id),)
            )

        if new_or_changed_ids:
            cur.executemany(
                "INSERT OR REPLACE INTO item_attributes (item, name, value) VALUES (?, 'DOPPELUNG', 'JA')",
                [(int(item_id),) for item_id in sorted(new_or_changed_ids)]
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    utils.log_change(
        'MAINTENANCE',
        f"Dopplungsstatus synchronisiert: {len(new_or_changed_ids)} neu/geändert, "
        f"{len(unchanged_ids)} weiterhin markiert, {len(stale_ids)} entfernt."
    )
    return {
        'new': len(new_or_changed_ids),
        'unchanged': len(unchanged_ids),
        'removed': len(stale_ids),
        'written': len(new_or_changed_ids) + len(stale_ids),
    }


def _parse_bpm_value(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            parsed = _parse_bpm_value(item)
            if parsed is not None:
                return parsed
        return None
    if hasattr(value, 'text'):
        return _parse_bpm_value(getattr(value, 'text'))
    match = re.search(r'(\d+(?:[\.,]\d+)?)', str(value))
    if not match:
        return None
    try:
        bpm = float(match.group(1).replace(',', '.'))
    except ValueError:
        return None
    if not 30 <= bpm <= 300:
        return None
    return int(bpm + 0.5)


def _valid_recording_mbid(value):
    text = str(value or '').strip().lower()
    if re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', text):
        return text
    return ''


def resolve_audio_path(raw_filename, base_dirs=None):
    """Resolve a database filename without modifying the stored path."""
    base_dirs = base_dirs or []
    raw = str(raw_filename or '').strip().strip('"').strip("'")
    if not raw or raw.lower() in ('nan', 'none'):
        return None

    candidates = [raw, raw.replace('\\', os.sep), raw.replace('/', os.sep)]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    rel_variants = {
        raw.lstrip('\\/'),
        raw.replace('\\', os.sep).lstrip(os.sep),
        raw.replace('/', os.sep).lstrip(os.sep),
    }
    for base_dir in base_dirs:
        if not base_dir:
            continue
        for rel in rel_variants:
            candidate = os.path.join(base_dir, rel)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
    return None


def read_audio_bpm_metadata(raw_filename, base_dirs=None):
    """Read existing BPM and optional MusicBrainz recording ID from an audio file.

    This is metadata-only: no audio analysis and no file modification is performed.
    The returned ``file_status`` is diagnostic only; unavailable files still fall
    back to the online MusicBrainz/AcousticBrainz path.
    """
    raw_filename = '' if raw_filename is None else str(raw_filename).strip()
    actual_path = resolve_audio_path(raw_filename, base_dirs)
    result = {'path': actual_path, 'bpm': None, 'mbid': '', 'file_status': 'ok'}
    if not raw_filename:
        result['file_status'] = 'no_filename'
        return result
    if not actual_path:
        result['file_status'] = 'not_found'
        return result

    try:
        import mutagen
        audio = mutagen.File(actual_path, easy=False)
    except Exception as exc:
        result['file_status'] = 'read_error'
        result['file_error'] = str(exc)
        utils.log_change('BPM', f"Audio-Metadaten konnten nicht gelesen werden: {actual_path}: {exc}")
        return result

    if audio is None or not getattr(audio, 'tags', None):
        result['file_status'] = 'no_tags'
        return result
    tags = audio.tags

    # ID3 (MP3/AIFF): standard BPM frame is TBPM. Picard stores the
    # MusicBrainz recording ID in UFID owned by http://musicbrainz.org.
    if hasattr(tags, 'getall'):
        try:
            frames = tags.getall('TBPM')
            if frames:
                result['bpm'] = _parse_bpm_value(frames[0])
        except Exception:
            pass
        try:
            for frame in tags.getall('UFID'):
                owner = str(getattr(frame, 'owner', '') or '').lower()
                if 'musicbrainz.org' not in owner:
                    continue
                raw_data = getattr(frame, 'data', b'')
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode('ascii', errors='ignore')
                mbid = _valid_recording_mbid(raw_data)
                if mbid:
                    result['mbid'] = mbid
                    break
        except Exception:
            pass

    # Vorbis/FLAC and other dict-like tags.
    try:
        if result['bpm'] is None:
            for key in ('bpm', 'BPM', 'tempo', 'TEMPO'):
                if key in tags:
                    parsed = _parse_bpm_value(tags.get(key))
                    if parsed is not None:
                        result['bpm'] = parsed
                        break
        if not result['mbid']:
            for key in (
                'musicbrainz_trackid', 'MUSICBRAINZ_TRACKID',
                'musicbrainz_recordingid', 'MUSICBRAINZ_RECORDINGID',
            ):
                if key not in tags:
                    continue
                value = tags.get(key)
                if isinstance(value, (list, tuple)) and value:
                    value = value[0]
                mbid = _valid_recording_mbid(value)
                if mbid:
                    result['mbid'] = mbid
                    break
    except Exception:
        pass
    return result


def get_bpm_flag_state(db_path):
    """Return existing BPM attributes keyed by item ID (case-insensitive name)."""
    conn = None
    try:
        uri = f"file:{os.path.abspath(db_path)}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        rows = conn.execute(
            "SELECT item, name, value FROM item_attributes WHERE LOWER(name) = 'bpm'"
        ).fetchall()
        state = {}
        for item_id, name, value in rows:
            state.setdefault(str(item_id), []).append((str(name), '' if value is None else str(value)))
        return state
    finally:
        if conn is not None:
            conn.close()


def apply_bpm_values(db_path, bpm_values):
    """Atomically fill BPM only where no valid BPM value exists yet."""
    clean = {}
    for item_id, bpm in (bpm_values or {}).items():
        parsed = _parse_bpm_value(bpm)
        if parsed is not None:
            clean[str(item_id)] = parsed
    if not clean:
        return {'written': 0, 'skipped_existing': 0, 'skipped_missing_item': 0}

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute('BEGIN IMMEDIATE')
        ids = [int(item_id) for item_id in clean]
        placeholders = ','.join('?' for _ in ids)

        valid_items = {
            int(row[0]) for row in cur.execute(
                f"SELECT idx FROM items WHERE idx IN ({placeholders})", ids
            ).fetchall()
        } if ids else set()

        existing_valid = set()
        if ids:
            rows = cur.execute(
                f"SELECT item, value FROM item_attributes WHERE LOWER(name) = 'bpm' AND item IN ({placeholders})",
                ids,
            ).fetchall()
            for item_id, value in rows:
                if _parse_bpm_value(value) is not None:
                    existing_valid.add(int(item_id))

        writable_ids = {
            int(item_id) for item_id in clean
            if int(item_id) in valid_items and int(item_id) not in existing_valid
        }

        # Remove only empty/invalid BPM spellings for items we are about to fill,
        # then write one canonical BPM attribute. Valid existing BPM never reach
        # this branch and are therefore never overwritten.
        for item_id in sorted(writable_ids):
            cur.execute(
                "DELETE FROM item_attributes WHERE item = ? AND LOWER(name) = 'bpm'",
                (item_id,)
            )
        to_write = [
            (item_id, 'BPM', str(clean[str(item_id)]))
            for item_id in sorted(writable_ids)
        ]
        if to_write:
            cur.executemany(
                "INSERT OR REPLACE INTO item_attributes (item, name, value) VALUES (?, ?, ?)",
                to_write,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    skipped_existing = len(existing_valid & set(ids))
    skipped_missing_item = len(set(ids) - valid_items)
    utils.log_change(
        'MAINTENANCE',
        f"BPM ergänzt: {len(to_write)} geschrieben, {skipped_existing} wegen vorhandener BPM übersprungen, "
        f"{skipped_missing_item} nicht mehr vorhandene Elemente übersprungen."
    )
    return {
        'written': len(to_write),
        'skipped_existing': skipped_existing,
        'skipped_missing_item': skipped_missing_item,
    }


def _parse_bpm_float(value):
    """Parse a BPM value without rounding so speed-zone boundaries stay exact."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            parsed = _parse_bpm_float(item)
            if parsed is not None:
                return parsed
        return None
    if hasattr(value, 'text'):
        return _parse_bpm_float(getattr(value, 'text'))
    match = re.search(r'(\d+(?:[\.,]\d+)?)', str(value))
    if not match:
        return None
    try:
        bpm = float(match.group(1).replace(',', '.'))
    except ValueError:
        return None
    if not 30.0 <= bpm <= 300.0:
        return None
    return bpm


def speed_group_for_bpm(value):
    """Map valid BPM to mAirList's standard Geschwindigkeit dropdown values."""
    bpm = _parse_bpm_float(value)
    if bpm is None:
        return None
    if bpm <= 100.0:
        return 'Langsam'
    if bpm < 130.0:
        return 'Medium'
    return 'Schnell'


def scan_speed_group_candidates(db_path):
    """Return missing Geschwindigkeit assignments without touching existing values."""
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        bpm_rows = conn.execute(
            "SELECT item, value FROM item_attributes WHERE LOWER(name) = 'bpm'"
        ).fetchall()
        speed_rows = conn.execute(
            "SELECT item, value FROM item_attributes WHERE LOWER(name) = 'geschwindigkeit'"
        ).fetchall()
        valid_items = {int(row[0]) for row in conn.execute('SELECT idx FROM items').fetchall()}
    finally:
        conn.close()

    bpm_by_item = {}
    for item_id, value in bpm_rows:
        bpm = _parse_bpm_float(value)
        if bpm is not None:
            bpm_by_item.setdefault(int(item_id), []).append(bpm)

    speed_by_item = {}
    for item_id, value in speed_rows:
        speed_by_item.setdefault(int(item_id), []).append('' if value is None else str(value).strip())

    candidates = {}
    stats = {
        'with_bpm': 0, 'existing': 0, 'candidates': 0,
        'slow': 0, 'medium': 0, 'fast': 0, 'ambiguous': 0,
    }
    for item_id in sorted(bpm_by_item):
        if item_id not in valid_items:
            continue
        stats['with_bpm'] += 1
        if any(value for value in speed_by_item.get(item_id, [])):
            stats['existing'] += 1
            continue
        groups = {speed_group_for_bpm(bpm) for bpm in bpm_by_item[item_id]}
        groups.discard(None)
        if len(groups) != 1:
            stats['ambiguous'] += 1
            continue
        group = groups.pop()
        candidates[str(item_id)] = group
        stats['candidates'] += 1
        if group == 'Langsam':
            stats['slow'] += 1
        elif group == 'Medium':
            stats['medium'] += 1
        else:
            stats['fast'] += 1
    return candidates, stats


def apply_speed_groups(db_path, assignments):
    """Atomically fill Geschwindigkeit only if it is still missing/blank."""
    allowed = {'Langsam', 'Medium', 'Schnell'}
    clean = {
        int(item_id): str(value)
        for item_id, value in (assignments or {}).items()
        if str(item_id).isdigit() and str(value) in allowed
    }
    if not clean:
        return {'written': 0, 'skipped_existing': 0, 'skipped_missing_item': 0}

    conn = sqlite3.connect(db_path)
    written = skipped_existing = skipped_missing_item = 0
    try:
        cur = conn.cursor()
        cur.execute('BEGIN IMMEDIATE')
        for item_id in sorted(clean):
            if cur.execute('SELECT 1 FROM items WHERE idx = ?', (item_id,)).fetchone() is None:
                skipped_missing_item += 1
                continue
            existing = cur.execute(
                "SELECT value FROM item_attributes WHERE item = ? AND LOWER(name) = 'geschwindigkeit'",
                (item_id,),
            ).fetchall()
            if any(str(row[0] or '').strip() for row in existing):
                skipped_existing += 1
                continue
            cur.execute(
                "DELETE FROM item_attributes WHERE item = ? AND LOWER(name) = 'geschwindigkeit'",
                (item_id,),
            )
            cur.execute(
                "INSERT OR REPLACE INTO item_attributes (item, name, value) VALUES (?, 'Geschwindigkeit', ?)",
                (item_id, clean[item_id]),
            )
            written += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    utils.log_change(
        'MAINTENANCE',
        f"Geschwindigkeitsgruppen ergänzt: {written} geschrieben, "
        f"{skipped_existing} vorhandene Einteilungen geschützt, "
        f"{skipped_missing_item} nicht mehr vorhandene Elemente übersprungen."
    )
    return {
        'written': written,
        'skipped_existing': skipped_existing,
        'skipped_missing_item': skipped_missing_item,
    }


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

_MMD_EXCLUDED_ATTRIBUTES = {
    'restauriert', 'doppelung', 'force_apply',
    'lyrics', 'songtext', 'songtexte', 'song text'
}


def _finite_float(value):
    try:
        if value is None or str(value).strip() == '':
            return None
        number = float(value)
        if number != number or number in (float('inf'), float('-inf')):
            return None
        return number
    except (TypeError, ValueError):
        return None


def _mmd_fixed(value, digits=3):
    number = _finite_float(value)
    if number is None:
        return None
    return f"{number:.{digits}f}"


def _mmd_amplification(value):
    number = _finite_float(value)
    if number is None:
        return None
    # mAirList's own MP3/MMD writer uses a decimal comma for Amplification,
    # while Duration/Markers/Levels use decimal points.
    return format(number, '.15g').replace('.', ',')


def _build_mairlist_xml(item, attributes=None, markers=None, declaration=False):
    """Build the mAirList <PlaylistItem> metadata block used in TXXX/.mmd.

    The structure is based on files written by mAirList itself. Duration is read
    only from the database; it is never recalculated or modified.
    """
    import xml.etree.ElementTree as ET

    attributes = attributes or []
    markers = markers or []
    root = ET.Element('PlaylistItem', {'Class': 'File'})

    amp = _mmd_amplification(item.get('amplification'))
    if amp is not None:
        ET.SubElement(root, 'Amplification').text = amp

    title = str(item.get('title') or '').strip()
    artist = str(item.get('artist') or '').strip()
    item_type = str(item.get('type') or '').strip()
    duration = _mmd_fixed(item.get('duration'))
    if title:
        ET.SubElement(root, 'Title').text = title
    if artist:
        ET.SubElement(root, 'Artist').text = artist
    if item_type:
        ET.SubElement(root, 'Type').text = item_type
    if duration is not None:
        ET.SubElement(root, 'Duration').text = duration

    filtered_attrs = []
    for name, value in attributes:
        name = str(name or '').strip()
        value = str(value or '').strip()
        if not name or not value:
            continue
        if name.casefold() in _MMD_EXCLUDED_ATTRIBUTES:
            continue
        filtered_attrs.append((name, value))
    if filtered_attrs:
        attrs_node = ET.SubElement(root, 'Attributes')
        for name, value in sorted(filtered_attrs, key=lambda pair: pair[0].casefold()):
            entry = ET.SubElement(attrs_node, 'Item')
            ET.SubElement(entry, 'Name').text = name
            ET.SubElement(entry, 'Value').text = value

    clean_markers = []
    for marker_type, marker_value in markers:
        marker_type = str(marker_type or '').strip()
        position = _mmd_fixed(marker_value)
        if marker_type and position is not None:
            clean_markers.append((marker_type, position))
    if clean_markers:
        markers_node = ET.SubElement(root, 'Markers')
        for marker_type, position in clean_markers:
            ET.SubElement(markers_node, 'Marker', {'Type': marker_type, 'Position': position})

    level_values = [
        ('Peak', item.get('level_peak')),
        ('TruePeak', item.get('level_truepeak')),
        ('Loudness', item.get('level_loudness')),
    ]
    clean_levels = [(name, _mmd_fixed(value)) for name, value in level_values]
    clean_levels = [(name, value) for name, value in clean_levels if value is not None]
    if clean_levels:
        levels = ET.SubElement(root, 'Levels')
        for name, value in clean_levels:
            ET.SubElement(levels, name).text = value

    body = ET.tostring(root, encoding='unicode', short_empty_elements=True).replace(' />', '/>')
    if declaration:
        return '<?xml version="1.0" encoding="UTF-8"?>' + body
    return body


def _write_text_atomic_if_changed(path, text):
    """Write UTF-8 text atomically and only when content differs."""
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8-sig') as handle:
                if handle.read() == text:
                    return False
    except Exception:
        pass
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)
    os.replace(tmp, path)
    return True


def _set_id3_mairlist_block(tags, xml_text):
    """Replace only TXXX:mAirList; preserve every unrelated ID3 frame."""
    from mutagen.id3 import TXXX

    matching_keys = []
    existing_texts = []
    for key in list(tags.keys()):
        frame = tags.get(key)
        if key.startswith('TXXX:') and getattr(frame, 'desc', '').casefold() == 'mairlist':
            matching_keys.append(key)
            existing_texts.extend(str(v) for v in getattr(frame, 'text', []) or [])
    if len(matching_keys) == 1 and existing_texts == [xml_text]:
        return False
    for key in matching_keys:
        del tags[key]
    tags.add(TXXX(encoding=3, desc='mAirList', text=[xml_text]))
    return True


def _attr_value(attributes, *names):
    wanted = {str(name).casefold() for name in names}
    for name, value in attributes:
        if str(name).casefold() in wanted and str(value or '').strip():
            return str(value).strip()
    return ''


def _clean_integerish_tag(value):
    text = str(value or '').strip()
    if not text:
        return ''
    try:
        number = float(text.replace(',', '.'))
        if number.is_integer():
            return str(int(number))
    except Exception:
        pass
    return text


def run_maintenance_file_tagger(db_path, metadata_mode=None, base_dirs=None):
    """Write portable audio tags and optionally mAirList metadata backups.

    metadata_mode:
      1 / 'tags' -> portable tags only
      2 / 'full' -> portable tags + mAirList TXXX (MP3/AIFF) or .mmd (FLAC/Ogg)
      None       -> ask interactively
    base_dirs can be supplied by tests/CLI integrations; None asks interactively.
    """
    try:
        import mutagen
        from mutagen.id3 import TPE1, TIT2, TDRC, TCON, TALB, TPUB, TLAN, TBPM, TSRC
    except ImportError:
        Console().print("\n[bold red]KRITISCHER FEHLER: Das Python-Modul 'mutagen' ist nicht installiert![/bold red]")
        Console().print("[yellow]Bitte öffne dein Terminal und tippe: pip install mutagen[/yellow]")
        return 0

    import logging
    c = Console(highlight=False)

    if metadata_mode is None:
        c.print("\n" + utils.t('tagger_mode_title'))
        c.print(utils.t('tagger_mode_desc'))
        while True:
            choice = c.input(utils.t('tagger_mode_prompt')).strip()
            if choice == '0':
                return 0
            if choice in ('1', '2'):
                metadata_mode = int(choice)
                break
            c.print(utils.t('tagger_mode_invalid'))
    elif str(metadata_mode).strip().casefold() in ('2', 'full', 'mairlist', 'tags+mairlist'):
        metadata_mode = 2
    else:
        metadata_mode = 1

    if base_dirs is None:
        c.print("\n" + utils.t('tagger_path_intro'))
        saved_dirs = utils.get_saved_source_folders(db_path)
        if saved_dirs:
            c.print(utils.t('source_dirs_saved', paths=', '.join(saved_dirs)))
        else:
            c.print(utils.t('source_dirs_none'))
        base_dirs = [d for d in saved_dirs if os.path.isdir(d)]
        added_dirs = []
        while True:
            d = c.input(utils.t('tagger_path_prompt')).strip().strip('"').strip("'")
            if not d:
                break
            if os.path.isdir(d):
                d = os.path.abspath(d)
                if os.path.normcase(d) not in {os.path.normcase(x) for x in base_dirs}:
                    base_dirs.append(d)
                    added_dirs.append(d)
                c.print(utils.t('tagger_path_added', path=d))
            else:
                c.print(utils.t('tagger_path_invalid'))
        if added_dirs:
            utils.save_source_folders(db_path, saved_dirs + added_dirs)
    else:
        base_dirs = [str(d) for d in base_dirs if os.path.isdir(str(d))]

    c.print("\n" + utils.t('tagger_working'))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(items)")
    items_cols = {row[1].lower() for row in cursor.fetchall()}
    id_col = next((name for name in ['idx', 'id', 'itemidx'] if name in items_cols), None)

    cursor.execute("PRAGMA table_info(item_attributes)")
    attr_cols = {row[1].lower() for row in cursor.fetchall()}
    if not attr_cols:
        cursor.execute("PRAGMA table_info(attributes)")
        attr_cols = {row[1].lower() for row in cursor.fetchall()}
        attr_table = 'attributes'
    else:
        attr_table = 'item_attributes'
    attr_id_col = next((name for name in ['item', 'itemidx', 'itemid', 'idx', 'id'] if name in attr_cols), None)

    if not id_col or not attr_id_col or 'filename' not in items_cols:
        conn.close()
        return 0

    def item_expr(column, alias=None):
        alias = alias or column
        return f"i.{column} AS {alias}" if column in items_cols else f"NULL AS {alias}"

    query = "SELECT " + ", ".join([
        f"i.{id_col} AS item_id",
        item_expr('artist'), item_expr('title'), item_expr('type'), item_expr('filename'),
        item_expr('duration'), item_expr('amplification'), item_expr('level_peak'),
        item_expr('level_truepeak'), item_expr('level_loudness'), item_expr('genre', 'native_genre')
    ]) + " FROM items i WHERE i.filename IS NOT NULL AND i.filename != ''"
    cursor.execute(query)
    rows = cursor.fetchall()
    row_names = [desc[0] for desc in cursor.description]

    attrs_by_item = {}
    cursor.execute(f"SELECT {attr_id_col}, name, value FROM {attr_table}")
    for item_id, name, value in cursor.fetchall():
        attrs_by_item.setdefault(item_id, []).append((name, value))

    markers_by_item = {}
    table_exists = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='item_cuemarkers'"
    ).fetchone()
    if table_exists:
        try:
            for item_id, marker_type, marker_value in cursor.execute(
                "SELECT item, type, value FROM item_cuemarkers ORDER BY item, rowid"
            ):
                markers_by_item.setdefault(item_id, []).append((marker_type, marker_value))
        except sqlite3.Error:
            pass
    conn.close()

    stat_total = len(rows)
    stat_not_found = 0
    stat_unsupported = 0
    stat_already_perfect = 0
    updated_count = 0
    embedded_count = 0
    sidecar_count = 0

    for raw_row in rows:
        item = dict(zip(row_names, raw_row))
        item_id = item['item_id']
        raw_filename = item.get('filename')
        attributes = attrs_by_item.get(item_id, [])
        markers = markers_by_item.get(item_id, [])

        filename = str(raw_filename).replace('\\', '/')
        actual_path = None
        if os.path.exists(filename) and os.path.isfile(filename):
            actual_path = filename
        else:
            for base_dir in base_dirs:
                test_path = os.path.join(base_dir, filename.lstrip('/'))
                if os.path.exists(test_path) and os.path.isfile(test_path):
                    actual_path = test_path
                    break

        if not actual_path:
            stat_not_found += 1
            if stat_not_found <= 5:
                c.print(f"[dim yellow]DEBUG Info: Suche erfolglos -> {filename}[/dim yellow]")
            continue

        c_artist = str(item.get('artist') or '').strip()
        c_title = str(item.get('title') or '').strip()
        c_year = _clean_integerish_tag(_attr_value(attributes, 'Jahr', 'Year', 'Jaar'))
        native_genre = str(item.get('native_genre') or '').strip()
        c_genre = native_genre or _attr_value(attributes, 'Genre')
        mmd_attributes = list(attributes)
        if c_genre and not _attr_value(attributes, 'Genre'):
            mmd_attributes.append(('Genre', c_genre))
        c_album = _attr_value(attributes, 'Album')
        c_label = _attr_value(attributes, 'Label')
        c_language = _attr_value(attributes, 'Sprache', 'Language', 'Taal')
        c_bpm = _clean_integerish_tag(_attr_value(attributes, 'BPM'))
        c_isrc = _attr_value(attributes, 'ISRC')

        try:
            audio = mutagen.File(actual_path, easy=False)
            if audio is None:
                stat_unsupported += 1
                continue

            portable_changed = False
            metadata_changed = False
            file_type = type(audio).__name__

            if file_type in ['FLAC', 'OggVorbis']:
                def set_vorbis(tag, val):
                    nonlocal portable_changed
                    if val and audio.get(tag) != [val]:
                        audio[tag] = [val]
                        portable_changed = True

                set_vorbis('artist', c_artist)
                set_vorbis('title', c_title)
                set_vorbis('date', c_year)
                set_vorbis('genre', c_genre)
                set_vorbis('album', c_album)
                set_vorbis('organization', c_label)
                set_vorbis('language', c_language)
                set_vorbis('bpm', c_bpm)
                set_vorbis('isrc', c_isrc)

                if portable_changed:
                    audio.save()

                if metadata_mode == 2:
                    xml_text = _build_mairlist_xml(item, mmd_attributes, markers, declaration=True)
                    metadata_changed = _write_text_atomic_if_changed(actual_path + '.mmd', xml_text)
                    if metadata_changed:
                        sidecar_count += 1

            elif file_type in ['MP3', 'AIFF']:
                if not getattr(audio, 'tags', None):
                    try:
                        audio.add_tags()
                    except Exception:
                        stat_unsupported += 1
                        continue

                def set_id3(frame_class, val):
                    nonlocal portable_changed
                    if not val:
                        return
                    frame_id = frame_class.__name__
                    existing = audio.tags.getall(frame_id)
                    if not existing or not getattr(existing[0], 'text', None) or str(existing[0].text[0]) != str(val):
                        audio.tags.setall(frame_id, [frame_class(encoding=3, text=[val])])
                        portable_changed = True

                set_id3(TPE1, c_artist)
                set_id3(TIT2, c_title)
                set_id3(TDRC, c_year)
                set_id3(TCON, c_genre)
                set_id3(TALB, c_album)
                set_id3(TPUB, c_label)
                set_id3(TLAN, c_language)
                set_id3(TBPM, c_bpm)
                set_id3(TSRC, c_isrc)

                if metadata_mode == 2:
                    xml_text = _build_mairlist_xml(item, mmd_attributes, markers, declaration=False)
                    metadata_changed = _set_id3_mairlist_block(audio.tags, xml_text)
                    if metadata_changed:
                        embedded_count += 1

                if portable_changed or metadata_changed:
                    audio.save()
            else:
                stat_unsupported += 1
                continue

            if portable_changed or metadata_changed:
                updated_count += 1
            else:
                stat_already_perfect += 1

        except Exception as exc:
            logging.error(f"FILE-TAGGER ERROR bei Datei {actual_path}: {exc}")
            stat_unsupported += 1
            continue

    logging.info(
        f"MAINTENANCE: {updated_count} Dateien getaggt/gesichert. "
        f"(Nicht gefunden: {stat_not_found}, mAirList embedded: {embedded_count}, MMD: {sidecar_count})"
    )

    c.print(f"\n[cyan]=== {utils.t('tagger_diag_title')} ===[/cyan]")
    c.print(f"{utils.t('tagger_diag_total')}: [bold]{stat_total}[/bold]")
    c.print(f"{utils.t('tagger_diag_missing')}: [bold yellow]{stat_not_found}[/bold yellow]")
    c.print(f"{utils.t('tagger_diag_unsupported')}: [bold yellow]{stat_unsupported}[/bold yellow]")
    c.print(f"{utils.t('tagger_diag_perfect')}: [bold green]{stat_already_perfect}[/bold green]")
    c.print(f"{utils.t('tagger_diag_updated')}: [bold green]{updated_count}[/bold green]")
    if metadata_mode == 2:
        c.print(f"{utils.t('tagger_diag_embedded')}: [bold green]{embedded_count}[/bold green]")
        c.print(f"{utils.t('tagger_diag_sidecar')}: [bold green]{sidecar_count}[/bold green]")
    c.print()
    return updated_count
