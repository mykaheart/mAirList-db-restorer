import pandas as pd
import os
import sys
import argparse
import hashlib
import logging
import shutil
import sqlite3
import time
import ntpath
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- ARBEITSVERZEICHNIS FIX ---
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich import box
import requests

import utils
import api
import db

console = Console(highlight=False)

# A complete track fetch can be retried after the request layer has already
# exhausted its own short retry cycle. These are automatic *retries* after the
# initial track attempt.
FETCH_TRACK_RETRY_DELAYS = (2.0, 5.0, 10.0)


def _is_transient_fetch_error(exc):
    """Return True only for errors that are worth retrying automatically."""
    if isinstance(exc, api.APIRequestError):
        if getattr(exc, 'kind', '') in {'network', 'rate_limit', 'server'}:
            return True
        status_code = getattr(exc, 'status_code', None)
        return status_code in getattr(api, 'RETRY_STATUS_CODES', set())
    return isinstance(exc, (requests.RequestException, TimeoutError, ConnectionError))


def _fetch_track_retry_delay(exc, retry_number):
    """Combine our backoff with Retry-After/rate-limit advice from the API."""
    index = max(0, min(int(retry_number) - 1, len(FETCH_TRACK_RETRY_DELAYS) - 1))
    base_delay = FETCH_TRACK_RETRY_DELAYS[index]
    try:
        advertised = float(getattr(exc, 'retry_after', None))
    except (TypeError, ValueError):
        advertised = 0.0
    return max(base_delay, advertised)


PROPOSAL_COLUMNS = [
    'Artist_Vorschlag', 'Title_Vorschlag', 'Jahr_Vorschlag', 'Jahr_Konfidenz',
    'Genre_Vorschlag', 'Genre_Konfidenz', 'Album_Vorschlag', 'STYLE_Vorschlag', 'DISCOGS_RELEASE_ID_Vorschlag',
    'Label_Vorschlag', 'Labelcode_Vorschlag', 'ISRC_Vorschlag', 'Sprache_Vorschlag',
    'Typ_Vorschlag', 'BPM_Vorschlag', 'BPM_Quelle', 'VORSCHLAG_STATUS', 'REVIEW_STATUS', 'FORCE_APPLY'
]

class StepBackException(Exception):
    pass

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def ask_input(prompt_text):
    utils.clear_input_buffer()
    val = console.input(prompt_text).strip()
    if val.lower() == 'b' or val == '<':
        raise StepBackException()
    return val

LIVE_DB_FIELDS = [
    'Artist', 'Title', 'ItemType', 'Filename', 'Duration', 'TotalDuration',
] + utils.MLDB_ATTRIBUTE_FIELDS


def sync_cache_from_db(df, input_df, item_ids=None):
    """Refresh original/cache values from the live .mldb snapshot without touching proposals."""
    if 'ID' not in df.columns or 'ID' not in input_df.columns:
        return

    source = input_df.copy()
    source['ID'] = source['ID'].astype(str)
    source = source.drop_duplicates(subset=['ID']).set_index('ID')

    target_ids = df['ID'].astype(str)
    mask = target_ids.isin(source.index)
    if item_ids is not None:
        wanted = {str(item_id) for item_id in item_ids}
        mask &= target_ids.isin(wanted)

    if not mask.any():
        return

    for field in LIVE_DB_FIELDS:
        if field not in source.columns or field not in df.columns:
            continue
        mapped = target_ids[mask].map(source[field])
        df.loc[mask, field] = mapped.where(pd.notna(mapped), '').values


def combine_year_confidence(mb_year, mb_conf, discogs_year, discogs_conf, final_year):
    if not final_year:
        return 'niedrig'
    if mb_year and discogs_year:
        if str(mb_year) == str(discogs_year):
            if mb_conf == 'hoch' or discogs_conf == 'hoch':
                return 'hoch'
            return 'mittel'
        # Two sources disagree: never auto-accept as high confidence.
        if mb_conf in ['hoch', 'mittel'] or discogs_conf in ['hoch', 'mittel']:
            return 'mittel'
        return 'niedrig'
    if mb_year:
        return mb_conf
    if discogs_year:
        return discogs_conf
    return 'niedrig'

def check_for_updates(interactive=False):
    try:
        url = "https://raw.githubusercontent.com/mykaheart/mAirList-db-restorer/main/utils.py"
        res = requests.get(url, timeout=1.5)
        if res.status_code == 200:
            for line in res.text.splitlines():
                if line.startswith("APP_VERSION ="):
                    remote_version = line.split("=")[1].strip().strip('"').strip("'")
                    
                    def get_v_tuple(v_str):
                        try:
                            num_part = v_str.split()[0]
                            return tuple(int(x) for x in num_part.split('.'))
                        except Exception:
                            return (0, 0, 0)
                            
                    remote_tuple = get_v_tuple(remote_version)
                    local_tuple = get_v_tuple(utils.APP_VERSION)
                    
                    if remote_tuple > local_tuple:
                        console.print(f"[bold yellow]⚡ Update verfügbar! Neue Version {remote_version} wurde veröffentlicht (Du nutzt {utils.APP_VERSION}).[/bold yellow]")
                        console.print(f"[bold cyan]👉 Download als fertige ZIP-Datei (inkl. Handbüchern) hier:[/bold cyan]")
                        console.print(f"[white]https://drive.google.com/drive/folders/18SmIOBFbSM5apwS6FA3F72-syLvBAftj?usp=drive_link[/white]")
                        
                        if interactive:
                            console.input("\nDrücke Enter zum Fortfahren (oder schließe das Programm, um zu updaten)...")
                            return False
                        sys.exit(2)
                    else:
                        if utils.CURRENT_LANG == 'de':
                            console.print(f"[dim]Version is up to date ({utils.APP_VERSION}).[/dim]")
                        elif utils.CURRENT_LANG == 'nl':
                            console.print(f"[dim]Versie is up-to-date ({utils.APP_VERSION}).[/dim]")
                        else:
                            console.print(f"[dim]Version is up to date ({utils.APP_VERSION}).[/dim]")
                        
                        if interactive:
                            time.sleep(1.5)
                            return True
                        sys.exit(0)
    except Exception:
        if interactive: return True
        sys.exit(0)
    return True

def get_db_session_name(db_path):
    """Create a collision-safe workspace name for a database path."""
    base_name = os.path.splitext(os.path.basename(db_path))[0]
    normalized = os.path.normcase(os.path.realpath(os.path.abspath(db_path)))
    digest = hashlib.sha1(normalized.encode('utf-8')).hexdigest()[:8]
    return f"{base_name}_{digest}"


def _migrate_legacy_cache_for_db(db_path, session_name, data_dir):
    """Move pre-0.62.05 cache files to the path-hashed workspace when unambiguous."""
    legacy_base = os.path.splitext(os.path.basename(db_path))[0]
    for suffix in ('_vorschlaege.csv', '_restauriert.csv'):
        old_path = os.path.join(data_dir, legacy_base + suffix)
        new_path = os.path.join(data_dir, session_name + suffix)
        if old_path != new_path and os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                os.replace(old_path, new_path)
            except OSError as e:
                utils.log_change("MIGRATION", f"Legacy-Cache konnte nicht migriert werden: {e}")


def setup_logging(db_path):
    data_dir = "Data"
    os.makedirs(data_dir, exist_ok=True)
    session_name = get_db_session_name(db_path)
    _migrate_legacy_cache_for_db(db_path, session_name, data_dir)

    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    dynamic_log_file = os.path.join(data_dir, f"{session_name}_{timestamp_str}.log")
    
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        filename=dynamic_log_file,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8'
    )
    return session_name, data_dir


def _migration_conflict_path(target_path):
    directory = os.path.dirname(target_path)
    filename = os.path.basename(target_path)
    stem, ext = os.path.splitext(filename)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    candidate = os.path.join(directory, f"{stem}_migration-conflict-{stamp}{ext}")
    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{stem}_migration-conflict-{stamp}-{counter}{ext}")
        counter += 1
    return candidate


def perform_migration():
    data_dir = "Data"
    os.makedirs(data_dir, exist_ok=True)
    for f in os.listdir('.'):
        if f.endswith('_vorschlaege.csv') or f.endswith('_restauriert.csv') or f.endswith('.log') or f == 'config.json':
            if os.path.isfile(f):
                target_path = os.path.join(data_dir, f)
                try:
                    if os.path.exists(target_path):
                        # Never delete potentially useful workspace data. Preserve both copies.
                        target_path = _migration_conflict_path(target_path)
                    shutil.move(f, target_path)
                except Exception as e:
                    utils.log_change("MIGRATION", f"Datei '{f}' konnte nicht verschoben werden: {e}")

def _prepare_fetch_bpm_context(db_path, input_df, rekordbox_xml=None):
    """Prepare read-only BPM lookup state for the normal Fetch workflow."""
    context = {
        'rb_map': {}, 'rb_stats': {}, 'resolved_paths': {},
        'existing_bpm_ids': set(), 'rekordbox_xml': '',
    }
    try:
        bpm_state = db.get_bpm_flag_state(db_path)
        for item_id, values in bpm_state.items():
            if any(db._parse_bpm_value(value) is not None for _, value in values):
                context['existing_bpm_ids'].add(str(item_id))
    except Exception as exc:
        utils.log_change('BPM', f"Fetch: vorhandene BPM konnten nicht gelesen werden: {exc}")

    try:
        ids = input_df['ID'].astype(str).tolist() if 'ID' in input_df.columns else None
        context['resolved_paths'] = db.get_resolved_item_paths(db_path, ids)
    except Exception as exc:
        utils.log_change('BPM', f"Fetch: mAirList-Speicherortpfade konnten nicht aufgelöst werden: {exc}")

    if rekordbox_xml:
        try:
            rb_map, rb_stats = _load_rekordbox_bpm_xml(rekordbox_xml)
            context['rb_map'] = rb_map
            context['rb_stats'] = rb_stats
            context['rekordbox_xml'] = rekordbox_xml
            console.print(utils.t(
                'fetch_bpm_rb_loaded', entries=rb_stats.get('entries', 0),
                valid=rb_stats.get('valid_bpm', 0)
            ))
        except Exception as exc:
            utils.log_change('BPM', f"Fetch: rekordbox XML konnte nicht geladen werden: {exc}")
            console.print(utils.t('fetch_bpm_rb_invalid', details=str(exc)))
    return context


def _fetch_bpm_proposal_for_row(row, bpm_context, artist, title, duration, isrc=''):
    """Return (bpm, source) for one Fetch row without modifying files or DB."""
    item_id = str(row.get('ID', '')).strip()
    if not item_id or item_id in bpm_context.get('existing_bpm_ids', set()):
        return None, ''

    filename = utils.clean_nan(row.get('Filename', ''))
    resolved = bpm_context.get('resolved_paths', {}).get(item_id) or filename

    rb_map = bpm_context.get('rb_map', {})
    if rb_map:
        rb = rb_map.get(_normalize_windows_path(resolved))
        if rb:
            return int(rb['bpm']), 'rekordbox XML'

    audio_meta = db.read_audio_bpm_metadata(resolved, [])
    if audio_meta.get('bpm') is not None:
        return int(audio_meta['bpm']), utils.t('maint_bpm_source_file')

    mbid = audio_meta.get('mbid', '')
    if not mbid:
        try:
            match = api.find_musicbrainz_recording_for_bpm(
                artist, title, isrc=isrc, local_duration_sec=duration
            )
        except api.APIRequestError as exc:
            utils.log_change('BPM', f"Fetch-BPM MusicBrainz-Fehler bei {artist} - {title}: {exc}")
            return None, ''
        if match:
            mbid = match.get('mbid', '')

    if not mbid:
        return None, ''

    try:
        response = api.fetch_acousticbrainz_bpms([mbid], include_status=True)
    except api.APIRequestError as exc:
        utils.log_change('BPM', f"Fetch-BPM AcousticBrainz-Fehler bei {artist} - {title}: {exc}")
        return None, ''
    except Exception as exc:
        utils.log_change('BPM', f"Fetch-BPM AcousticBrainz-Fehler bei {artist} - {title}: {exc}")
        return None, ''

    if isinstance(response, tuple) and len(response) == 2:
        values, _status = response
    else:
        values = response or {}
    selected = values.get(str(mbid).lower()) or values.get(str(mbid))
    if not selected:
        return None, ''
    return int(selected['bpm']), utils.t(
        'maint_bpm_source_ab', agree=selected.get('agree', 1), total=selected.get('total', 1)
    )


def _select_fetch_rekordbox_xml(db_path):
    """Interactive per-database rekordbox XML selector used by normal Fetch."""
    saved = utils.get_saved_rekordbox_xml(db_path)
    default = saved if saved and os.path.isfile(saved) else ''
    if not default:
        for candidate in (
            os.path.join(APP_DIR, 'rekordbox.xml'),
            os.path.join(utils.DATA_DIR, 'rekordbox.xml'),
        ):
            if os.path.isfile(candidate):
                default = os.path.abspath(candidate)
                break

    default_text = default if default else utils.t('fetch_bpm_rb_none')
    utils.clear_input_buffer()
    value = console.input(utils.t('fetch_bpm_rb_prompt', default=default_text)).strip().strip('"').strip("'")
    if value == '-':
        utils.save_rekordbox_xml(db_path, '')
        return None
    chosen = value or default
    if not chosen:
        return None
    if not os.path.isfile(chosen):
        console.print(utils.t('fetch_bpm_rb_missing', path=chosen))
        return None
    try:
        _load_rekordbox_bpm_xml(chosen)
    except Exception as exc:
        console.print(utils.t('fetch_bpm_rb_invalid', details=str(exc)))
        return None
    chosen = os.path.abspath(chosen)
    utils.save_rekordbox_xml(db_path, chosen)
    return chosen


def phase_fetch(db_path, fetch_csv, full=False, no_breaks=False, rekordbox_xml=None):
    if db.verify_db_compatibility(db_path) is None:
        return
    if db.is_db_locked(db_path):
        console.print(Panel(utils.t('apply_locked'), box=box.HEAVY, style="red"))
        return

    ignored_folders = utils.setup_ignored_folders(db_path)
    try:
        input_df = db.load_dataframe_from_mldb(db_path, ignored_folders)
    except Exception as e:
        utils.log_change("ERROR", f"Datenbank konnte nicht gelesen werden: {e}")
        console.print(Panel(utils.t('db_read_error', details=str(e)), box=box.HEAVY, style="red"))
        return
    
    forbidden_types = ['Dummy', 'Stream', 'Command', 'Silence', 'Other']
    if 'ItemType' in input_df.columns:
        input_df = input_df[~input_df['ItemType'].isin(forbidden_types)].copy()
    
    if os.path.exists(fetch_csv):
        df = pd.read_csv(fetch_csv, dtype=str)
        console.print(utils.t('fetch_load_prog', csv=fetch_csv, count=len(df)))
        
        if 'ID' in df.columns and 'ID' in input_df.columns:
            db_ids = set(input_df['ID'].dropna().astype(str))
            csv_ids = set(df['ID'].dropna().astype(str))
            deleted_ids = csv_ids - db_ids
            if deleted_ids:
                console.print(utils.t('fetch_sync_del', count=len(deleted_ids)))
                df = df[~df['ID'].astype(str).isin(deleted_ids)].copy()
        
        key = 'ID'
        if key in df.columns and key in input_df.columns:
            existing_keys = set(df[key].dropna().astype(str))
            new_rows = input_df[~input_df[key].astype(str).isin(existing_keys)].copy()
        else:
            df_key = (df.get('Artist', '').fillna('') + '||' + df.get('Title', '').fillna(''))
            input_key = (input_df.get('Artist', '').fillna('') + '||' + input_df.get('Title', '').fillna(''))
            new_rows = input_df[~input_key.isin(set(df_key))].copy()

        if len(new_rows) > 0:
            console.print(utils.t('fetch_new_tracks', count=len(new_rows), db=db_path))
            df = pd.concat([df, new_rows], ignore_index=True, sort=False)
            
        if 'Duration' not in df.columns:
            db_dur = input_df.set_index('ID')['Duration'].to_dict()
            df['Duration'] = df['ID'].map(db_dur).fillna(0.0)
        if 'TotalDuration' not in df.columns:
            db_tdur = input_df.set_index('ID')['TotalDuration'].to_dict()
            df['TotalDuration'] = df['ID'].map(db_tdur).fillna(0.0)
            
    else:
        console.print(utils.t('fetch_first', db=db_path))
        df = input_df.copy()

    for col in PROPOSAL_COLUMNS + utils.MLDB_ATTRIBUTE_FIELDS:
        if col not in df.columns: df[col] = ''

    bpm_context = _prepare_fetch_bpm_context(db_path, input_df, rekordbox_xml=rekordbox_xml)

    if full:
        # A Full Fetch must start from the current database state, not from stale
        # original values that may still live in an older CSV cache.
        sync_cache_from_db(df, input_df)
        df['FORCE_APPLY'] = 'JA'

    if 'RESTAURIERT' in input_df.columns:
        db_restauriert = input_df.set_index('ID')['RESTAURIERT'].to_dict()
        
        if not full and 'RESTAURIERT' in df.columns:
            reset_ids = []
            for idx, row in df.iterrows():
                item_id = str(row.get('ID', ''))
                old_val = str(row.get('RESTAURIERT', '')).strip().upper()
                new_val = str(db_restauriert.get(item_id, '')).strip().upper()

                if old_val == 'JA' and new_val != 'JA':
                    df.at[idx, 'VORSCHLAG_STATUS'] = ''
                    df.at[idx, 'REVIEW_STATUS'] = ''
                    df.at[idx, 'FORCE_APPLY'] = ''
                    reset_ids.append(item_id)

            if reset_ids:
                # The .mldb is the source of truth. Refresh every original field,
                # not only Artist/Title, before this track is fetched again.
                sync_cache_from_db(df, input_df, reset_ids)
                console.print(utils.t('fetch_reset', count=len(reset_ids)))
                
        df['RESTAURIERT'] = df['ID'].map(db_restauriert).fillna('')

    if not full:
        force_apply = df['FORCE_APPLY'].astype(str).str.upper() == 'JA'
        already_done = (df['RESTAURIERT'].astype(str).str.upper() == 'JA') & ~force_apply
        df.loc[already_done, 'VORSCHLAG_STATUS'] = 'FERTIG'
        if 'REVIEW_STATUS' in df.columns:
            df.loc[already_done, 'REVIEW_STATUS'] = 'JA'
    else:
        console.print(utils.t('fetch_full'))
        df['VORSCHLAG_STATUS'] = ''
        if 'REVIEW_STATUS' in df.columns: df['REVIEW_STATUS'] = ''

    todo_mask = (df['VORSCHLAG_STATUS'] != 'FERTIG')
    offen = todo_mask.sum()
    total = len(df)
    
    console.print(Panel(utils.t('fetch_start', offen=offen, total=total), box=box.ROUNDED))
    utils.log_change("FETCH_START", f"Pending: {offen}, Total: {total}")

    if offen == 0:
        console.print(utils.t('fetch_done_already'))
        return

    processed_counter = 0
    error_count = 0
    stopped_for_review = False
    item_type_lang = db.detect_db_language(db_path, utils.CURRENT_LANG)
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bold green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TextColumn("•"),
        TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"), TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task(utils.t('fetch_progress'), total=offen)

        try:
            for idx, row in df.iterrows():
                if str(row.get('VORSCHLAG_STATUS', '')).strip().upper() == 'FERTIG': continue

                try:
                    raw_artist, raw_title = row.get('Artist', ''), row.get('Title', '')
                    local_dur = utils.get_best_duration(row.get('Duration'), row.get('TotalDuration'))
                    
                    c_art, c_tit = utils.clean_artist_base(raw_artist), utils.clean_title_base(raw_title)

                    # The request layer already retries individual HTTP calls. If an
                    # entire track still fails because of a transient network/429/5xx
                    # condition, restart the complete track lookup up to three times.
                    for retry_index in range(len(FETCH_TRACK_RETRY_DELAYS) + 1):
                        try:
                            artist_proposal = api.suggest_artist_spelling(c_art)
                            art_sugg = artist_proposal or c_art
                            title_proposal = api.suggest_title_spelling(art_sugg, c_tit, local_dur)
                            tit_sugg = title_proposal or c_tit

                            with ThreadPoolExecutor(max_workers=2) as executor:
                                future_mb = executor.submit(
                                    api.fetch_musicbrainz_details, art_sugg, tit_sugg, None, None, local_dur
                                )
                                future_discogs = executor.submit(
                                    api.fetch_discogs_details, art_sugg, tit_sugg, None, None
                                )

                                mb_year, mb_conf, isrc, mb_album, mb_lang = future_mb.result()
                                discogs_res = future_discogs.result()
                            break
                        except Exception as exc:
                            if not _is_transient_fetch_error(exc) or retry_index >= len(FETCH_TRACK_RETRY_DELAYS):
                                raise
                            retry_number = retry_index + 1
                            delay = _fetch_track_retry_delay(exc, retry_number)
                            delay_text = f"{delay:.1f}".rstrip('0').rstrip('.')
                            utils.log_change(
                                "FETCH_RETRY",
                                f"Track ID {row.get('ID')}: automatischer Retry {retry_number}/{len(FETCH_TRACK_RETRY_DELAYS)} "
                                f"nach {delay_text}s wegen {exc}"
                            )
                            progress.console.print(utils.t(
                                'fetch_track_retry', id=row.get('ID'), retry=retry_number,
                                max_retry=len(FETCH_TRACK_RETRY_DELAYS), delay=delay_text
                            ))
                            time.sleep(delay)

                    all_years = [mb_year] if mb_year else []
                    all_years += [y for y in discogs_res['years']]
                    oldest_year = utils.filter_valid_years(all_years)
                    discogs_year = utils.filter_valid_years(discogs_res['years'])
                    combined_conf = combine_year_confidence(
                        mb_year, mb_conf, discogs_year, discogs_res['confidence'], oldest_year
                    )

                    df.at[idx, 'Artist_Vorschlag'] = artist_proposal or ''
                    df.at[idx, 'Title_Vorschlag'] = title_proposal or ''
                    df.at[idx, 'Jahr_Vorschlag'] = oldest_year
                    df.at[idx, 'Jahr_Konfidenz'] = combined_conf
                    df.at[idx, 'Genre_Vorschlag'] = discogs_res['genre'] or ''
                    df.at[idx, 'Genre_Konfidenz'] = discogs_res['confidence']
                    df.at[idx, 'Album_Vorschlag'] = discogs_res['album'] or mb_album or ''
                    df.at[idx, 'STYLE_Vorschlag'] = discogs_res['style']
                    df.at[idx, 'DISCOGS_RELEASE_ID_Vorschlag'] = discogs_res['discogs_id']
                    df.at[idx, 'Label_Vorschlag'] = discogs_res['label']
                    df.at[idx, 'Labelcode_Vorschlag'] = discogs_res['label_code']
                    df.at[idx, 'ISRC_Vorschlag'] = isrc or ''
                    df.at[idx, 'Sprache_Vorschlag'] = mb_lang or ''

                    # BPM is part of the normal Fetch, but only as a proposal.
                    # Existing valid BPM values in the live database are protected.
                    df.at[idx, 'BPM_Vorschlag'] = ''
                    df.at[idx, 'BPM_Quelle'] = ''
                    bpm_value, bpm_source = _fetch_bpm_proposal_for_row(
                        row, bpm_context, art_sugg, tit_sugg, local_dur, isrc=isrc or row.get('ISRC', '')
                    )
                    if bpm_value is not None:
                        df.at[idx, 'BPM_Vorschlag'] = str(bpm_value)
                        df.at[idx, 'BPM_Quelle'] = bpm_source
                    
                    current_typ = str(row.get('Typ', '')).strip()
                    if not current_typ:
                        raw_type = str(row.get('ItemType', '')).strip()
                        df.at[idx, 'Typ_Vorschlag'] = utils.map_item_type(raw_type, item_type_lang)
                    else:
                        df.at[idx, 'Typ_Vorschlag'] = ''
                        
                    df.at[idx, 'VORSCHLAG_STATUS'] = 'FERTIG'

                    conf_color = "green" if combined_conf == "hoch" else ("yellow" if combined_conf == "mittel" else "red")
                    locale_conf = utils.t(f"conf_{combined_conf}")
                    progress.console.print(utils.t('fetch_track_info', id=row.get('ID'), art=art_sugg, tit=tit_sugg, jahr=oldest_year or '?', c_color=conf_color, conf=locale_conf))
                
                except Exception as e:
                    error_count += 1
                    df.at[idx, 'VORSCHLAG_STATUS'] = 'FEHLER'
                    if 'REVIEW_STATUS' in df.columns:
                        df.at[idx, 'REVIEW_STATUS'] = ''
                    utils.log_change("ERROR", f"Track ID {row.get('ID')} konnte nicht abgeschlossen werden: {str(e)}")
                    progress.console.print(utils.t('fetch_track_error', id=row.get('ID')))

                processed_counter += 1
                progress.update(task, advance=1)
                if processed_counter % 20 == 0: utils.save_safe_csv(df, fetch_csv)

                if not no_breaks and processed_counter % 50 == 0 and processed_counter < offen:
                    utils.save_safe_csv(df, fetch_csv)
                    progress.stop()
                    console.print(utils.t('fetch_chunk_pause', count=processed_counter))
                    ans = console.input(utils.t('fetch_chunk_prompt')).strip().lower()
                    if ans == 'r':
                        stopped_for_review = True
                        break
                    progress.start()

        except KeyboardInterrupt:
            console.print(utils.t('fetch_interrupt'))
            utils.save_safe_csv(df, fetch_csv)
            return

    utils.save_safe_csv(df, fetch_csv)
    if error_count:
        console.print(utils.t('fetch_done_with_errors', count=error_count))
    if stopped_for_review:
        console.print(utils.t('fetch_paused_review'))
    elif not error_count:
        console.print(utils.t('fetch_success', db=db_path))

def phase_review(fetch_csv, final_csv, auto_hoch=False):
    try: 
        df = pd.read_csv(fetch_csv, dtype=str)
        orig_df = df.copy() 
    except FileNotFoundError:
        console.print(utils.t('err_file_not_found', file=fetch_csv) + utils.t('err_need_fetch'))
        return

    if 'REVIEW_STATUS' not in df.columns: df['REVIEW_STATUS'] = ''
    for col in utils.MLDB_ATTRIBUTE_FIELDS:
        if col not in df.columns: df[col] = ''

    todo = df[(df['VORSCHLAG_STATUS'] == 'FERTIG') & (df['REVIEW_STATUS'] != 'JA')]
    auto_txt = utils.t('rev_auto_active') if auto_hoch else ""
    console.print(Panel(utils.t('rev_mode', todo=len(todo), auto=auto_txt), box=box.ROUNDED))

    reviewed_counter = 0
    todo_indices = list(todo.index)
    i = 0

    try:
        while i < len(todo_indices):
            idx = todo_indices[i]
            row = df.loc[idx]
            artist, title = row.get('Artist', ''), row.get('Title', '')
            local_dur = utils.get_best_duration(row.get('Duration'), row.get('TotalDuration'))
            
            orig_art = utils.clean_nan(orig_df.at[idx, 'Artist'])
            orig_tit = utils.clean_nan(orig_df.at[idx, 'Title'])
            orig_jahr = utils.clean_nan(orig_df.at[idx, 'Jahr'])
            orig_genre = utils.clean_nan(orig_df.at[idx, 'Genre'])
            orig_album = utils.clean_nan(orig_df.at[idx, 'Album'])
            orig_label = utils.clean_nan(orig_df.at[idx, 'Label'])
            orig_lang = utils.clean_nan(orig_df.at[idx, 'Sprache'])

            console.print(f"\n[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
            console.print(utils.t('rev_row', row=idx+1, id=row.get('ID'), art=artist, tit=title))
            custom_refetch_needed = False

            try:
                art_sugg = utils.clean_nan(row.get('Artist_Vorschlag'))
                if art_sugg:
                    inp = ask_input(utils.t('rev_artist', sugg=art_sugg, orig=orig_art))
                    if inp.lower() in ['', 'j', 'ja', 'y', 'yes']: df.at[idx, 'Artist'] = art_sugg
                    elif inp.lower() == 'o': df.at[idx, 'Artist'] = orig_art
                    elif inp and inp.lower() not in ['n', 'nein']: 
                        df.at[idx, 'Artist'] = inp
                        custom_refetch_needed = True

                tit_sugg = utils.clean_nan(row.get('Title_Vorschlag'))
                if tit_sugg:
                    inp = ask_input(utils.t('rev_title', sugg=tit_sugg, orig=orig_tit))
                    if inp.lower() in ['', 'j', 'ja', 'y', 'yes']: df.at[idx, 'Title'] = tit_sugg
                    elif inp.lower() == 'o': df.at[idx, 'Title'] = orig_tit
                    elif inp and inp.lower() not in ['n', 'nein']:
                        df.at[idx, 'Title'] = inp
                        custom_refetch_needed = True

                jahr_sugg = utils.clean_nan(df.at[idx, 'Jahr_Vorschlag'])
                konf = utils.clean_nan(df.at[idx, 'Jahr_Konfidenz']) or 'niedrig'
                conf_badge = f"[green]{utils.t('conf_hoch')}[/green]" if konf == "hoch" else (f"[yellow]{utils.t('conf_mittel')}[/yellow]" if konf == "mittel" else f"[red]{utils.t('conf_niedrig')}[/red]")
                
                if jahr_sugg:
                    if auto_hoch and konf == 'hoch':
                        df.at[idx, 'Jahr'] = jahr_sugg
                        console.print(utils.t('rev_year_auto', sugg=jahr_sugg, orig=orig_jahr))
                    else:
                        inp = ask_input(utils.t('rev_year', sugg=jahr_sugg, badge=conf_badge, orig=orig_jahr))
                        if inp.lower() in ['', 'j', 'ja', 'y', 'yes']: df.at[idx, 'Jahr'] = jahr_sugg
                        elif inp.lower() == 'o': df.at[idx, 'Jahr'] = orig_jahr
                        elif inp and inp.lower() not in ['n', 'nein']: 
                            df.at[idx, 'Jahr'] = inp
                            custom_refetch_needed = True

                album_sugg = utils.clean_nan(df.at[idx, 'Album_Vorschlag'] if 'Album_Vorschlag' in df.columns else row.get('Album_Vorschlag'))
                disp_album = album_sugg if album_sugg else utils.t('no_sugg')
                inp = ask_input(utils.t('rev_album', sugg=disp_album, orig=orig_album))
                if inp.lower() in ['', 'j', 'ja', 'y', 'yes']:
                    if album_sugg: df.at[idx, 'Album'] = album_sugg
                elif inp.lower() == 'o': 
                    df.at[idx, 'Album'] = orig_album
                elif inp and inp.lower() not in ['n', 'nein']: 
                    df.at[idx, 'Album'] = inp
                    custom_refetch_needed = True

                if custom_refetch_needed:
                    updated_art, updated_tit = str(df.at[idx, 'Artist']), str(df.at[idx, 'Title'])
                    target_y = utils.clean_nan(df.at[idx, 'Jahr'])
                    target_a = utils.clean_nan(df.at[idx, 'Album'])
                    
                    console.print(utils.t('rev_refetch', art=updated_art, tit=updated_tit))
                    
                    c_art, c_tit = utils.clean_artist_base(updated_art), utils.clean_title_base(updated_tit)
                    
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        future_mb = executor.submit(api.fetch_musicbrainz_details, c_art, c_tit, target_y, target_a, local_dur)
                        future_discogs = executor.submit(api.fetch_discogs_details, c_art, c_tit, target_y, target_a)
                        
                        mb_year, mb_conf, isrc, mb_album, mb_lang = future_mb.result()
                        discogs_res = future_discogs.result()

                    df.at[idx, 'Genre_Vorschlag'] = discogs_res['genre'] or ''
                    df.at[idx, 'Genre_Konfidenz'] = discogs_res['confidence']
                    df.at[idx, 'Label_Vorschlag'] = discogs_res['label'] or ''
                    df.at[idx, 'Labelcode_Vorschlag'] = discogs_res['label_code'] or ''
                    df.at[idx, 'ISRC_Vorschlag'] = isrc or ''
                    df.at[idx, 'STYLE_Vorschlag'] = discogs_res['style'] or ''
                    df.at[idx, 'DISCOGS_RELEASE_ID_Vorschlag'] = discogs_res['discogs_id'] or ''
                    if mb_lang: df.at[idx, 'Sprache_Vorschlag'] = mb_lang

                    # An AcousticBrainz proposal depends on the previous recording
                    # identity. If Artist/Title/Year/Album was manually corrected,
                    # discard that BPM proposal instead of carrying a stale match
                    # into Apply. Path-/file-tag based BPM remains tied to the file.
                    bpm_source = utils.clean_nan(df.at[idx, 'BPM_Quelle'] if 'BPM_Quelle' in df.columns else '')
                    if bpm_source.casefold().startswith('acousticbrainz'):
                        df.at[idx, 'BPM_Vorschlag'] = ''
                        df.at[idx, 'BPM_Quelle'] = ''

                genre_sugg = utils.clean_nan(df.at[idx, 'Genre_Vorschlag'])
                genre_konf = utils.clean_nan(df.at[idx, 'Genre_Konfidenz']) or 'niedrig'
                genre_map = utils.get_genre_quick_map()
                genre_hint = "/".join([f"{key}={value}" for key, value in genre_map.items()] + ["Text"])
                if genre_sugg and auto_hoch and genre_konf == 'hoch' and not custom_refetch_needed:
                    df.at[idx, 'Genre'] = genre_sugg
                    console.print(utils.t('rev_genre_auto', sugg=genre_sugg, orig=orig_genre))
                else:
                    disp_genre = genre_sugg if genre_sugg else utils.t('no_sugg')
                    inp = ask_input(utils.t('rev_genre', sugg=disp_genre, orig=orig_genre, hint=genre_hint))
                    low = inp.lower()
                    if low in ['', 'j', 'ja', 'y', 'yes']:
                        if genre_sugg:
                            df.at[idx, 'Genre'] = genre_sugg
                    elif low == 'o':
                        df.at[idx, 'Genre'] = orig_genre
                    elif inp in genre_map:
                        df.at[idx, 'Genre'] = genre_map[inp]
                    elif inp and low not in ['n', 'nein', 'no', 'nee']:
                        chosen_genre = utils.canonical_genre_choice(inp)
                        df.at[idx, 'Genre'] = chosen_genre
                        utils.add_custom_genre(chosen_genre)

                label_sugg = utils.clean_nan(df.at[idx, 'Label_Vorschlag'])
                disp_label = label_sugg if label_sugg else utils.t('no_sugg')
                inp = ask_input(utils.t('rev_label', sugg=disp_label, orig=orig_label))
                if inp.lower() in ['', 'j', 'ja', 'y', 'yes']:
                    if label_sugg: df.at[idx, 'Label'] = label_sugg
                elif inp.lower() == 'o': 
                    df.at[idx, 'Label'] = orig_label
                elif inp and inp.lower() not in ['n', 'nein']: df.at[idx, 'Label'] = inp

                lang_sugg = utils.clean_nan(df.at[idx, 'Sprache_Vorschlag'] if 'Sprache_Vorschlag' in df.columns else row.get('Sprache_Vorschlag'))
                disp_lang = lang_sugg if lang_sugg else utils.t('no_sugg')
                
                lang_map = {'1': 'Engels' if utils.CURRENT_LANG == 'nl' else ('Englisch' if utils.CURRENT_LANG == 'de' else 'English'),
                            '2': 'Duits' if utils.CURRENT_LANG == 'nl' else ('Deutsch' if utils.CURRENT_LANG == 'de' else 'German'),
                            '3': 'Nederlands' if utils.CURRENT_LANG == 'nl' else ('Niederländisch' if utils.CURRENT_LANG == 'de' else 'Dutch')}
                nxt_idx = 4
                for cl in utils.CUSTOM_LANGS:
                    lang_map[str(nxt_idx)] = cl
                    nxt_idx += 1
                    
                hint_parts = []
                for k, v in lang_map.items(): hint_parts.append(f"{k}={v}")
                hint_parts.append("Text")
                hint_str = "/".join(hint_parts)
                
                inp = ask_input(utils.t('rev_lang', sugg=disp_lang, orig=orig_lang, hint=hint_str))
                
                if inp.lower() in ['', 'j', 'ja', 'y', 'yes']:
                    if lang_sugg: df.at[idx, 'Sprache'] = lang_sugg
                elif inp.lower() == 'o': 
                    df.at[idx, 'Sprache'] = orig_lang
                elif inp in lang_map:
                    df.at[idx, 'Sprache'] = lang_map[inp]
                elif inp and inp.lower() not in ['n', 'nein']: 
                    df.at[idx, 'Sprache'] = inp
                    if inp not in utils.CUSTOM_LANGS and inp not in [lang_map['1'], lang_map['2'], lang_map['3']]:
                        utils.add_custom_lang(inp)

                bpm_sugg = utils.clean_nan(df.at[idx, 'BPM_Vorschlag'] if 'BPM_Vorschlag' in df.columns else '')
                if bpm_sugg:
                    df.at[idx, 'BPM'] = bpm_sugg
                    console.print(utils.t(
                        'rev_bpm_auto', sugg=bpm_sugg, source=utils.clean_nan(df.at[idx, 'BPM_Quelle']) or '?'
                    ))

                for target_col, sugg_col in [
                    ('STYLE', 'STYLE_Vorschlag'), ('DISCOGS_RELEASE_ID', 'DISCOGS_RELEASE_ID_Vorschlag'),
                    ('Labelcode', 'Labelcode_Vorschlag'), ('ISRC', 'ISRC_Vorschlag'),
                    ('Typ', 'Typ_Vorschlag')
                ]:
                    s_val = utils.clean_nan(df.at[idx, sugg_col] if sugg_col in df.columns else row.get(sugg_col))
                    if s_val: df.at[idx, target_col] = s_val

            except StepBackException:
                if i > 0:
                    i -= 1
                    console.print("[yellow]⏪ Okay, einen Track zurück...[/yellow]")
                else:
                    console.print("[yellow]⚠️ Das ist bereits der erste Track! Weiter zurück geht's nicht.[/yellow]")
                continue

            df.at[idx, 'REVIEW_STATUS'] = 'JA'
            utils.log_change("REVIEW_OK", f"ID {row.get('ID')}: {df.at[idx, 'Artist']} - {df.at[idx, 'Title']}")
            reviewed_counter += 1
            if reviewed_counter % 10 == 0:
                utils.save_safe_csv(df, fetch_csv)
                console.print(utils.t('rev_interim'))
            
            i += 1

    except KeyboardInterrupt:
        console.print(utils.t('rev_interrupt'))
        utils.save_safe_csv(df, fetch_csv)
        return

    utils.save_safe_csv(df, fetch_csv)
    utils.save_safe_csv(df, final_csv)
    console.print(utils.t('rev_success', csv=final_csv))

def _apply_field_labels():
    labels = {
        'de': {
            'Artist': 'Artist', 'Title': 'Titel', 'Jahr': 'Jahr', 'Genre': 'Genre',
            'Album': 'Album', 'Label': 'Label', 'Labelcode': 'Labelcode', 'ISRC': 'ISRC',
            'Sprache': 'Sprache', 'Typ': 'Typ', 'BPM': 'BPM'
        },
        'en': {
            'Artist': 'Artist', 'Title': 'Title', 'Jahr': 'Year', 'Genre': 'Genre',
            'Album': 'Album', 'Label': 'Label', 'Labelcode': 'Label code', 'ISRC': 'ISRC',
            'Sprache': 'Language', 'Typ': 'Type', 'BPM': 'BPM'
        },
        'nl': {
            'Artist': 'Artiest', 'Title': 'Titel', 'Jahr': 'Jaar', 'Genre': 'Genre',
            'Album': 'Album', 'Label': 'Label', 'Labelcode': 'Labelcode', 'ISRC': 'ISRC',
            'Sprache': 'Taal', 'Typ': 'Soort', 'BPM': 'BPM'
        }
    }
    return labels.get(utils.CURRENT_LANG, labels['de'])


def build_apply_change_counts(df, db_path):
    current = db.load_dataframe_from_mldb(db_path, ignored_folders=[])
    if 'ID' not in current.columns:
        return {field: 0 for field in _apply_field_labels()}

    current = current.copy()
    current['ID'] = current['ID'].astype(str)
    current = current.drop_duplicates(subset=['ID']).set_index('ID')
    counts = {field: 0 for field in _apply_field_labels()}

    for _, row in df.iterrows():
        item_id = str(row.get('ID', ''))
        if item_id not in current.index:
            continue
        live = current.loc[item_id]
        for field in counts:
            new_value = utils.clean_nan(row.get(field, ''))
            old_value = utils.clean_nan(live.get(field, ''))
            # Empty values are not written by apply_dataframe_to_mldb.
            if new_value and new_value != old_value:
                counts[field] += 1
    return counts


def print_apply_summary(df, db_path):
    force_count = int((df['FORCE_APPLY'].astype(str).str.upper() == 'JA').sum()) if 'FORCE_APPLY' in df.columns else 0
    summary_text = (
        f"[bold]{utils.t('apply_summary_total')}:[/bold] [cyan]{len(df)}[/cyan]\n"
        f"[bold]{utils.t('apply_summary_force')}:[/bold] [cyan]{force_count}[/cyan]\n"
        f"[bold]{utils.t('apply_summary_restored')}:[/bold] [cyan]{len(df)}[/cyan]"
    )
    console.print(Panel(summary_text, title=utils.t('apply_summary_title'), box=box.ROUNDED))

    counts = build_apply_change_counts(df, db_path)
    labels = _apply_field_labels()
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
    table.add_column(utils.t('apply_summary_field'))
    table.add_column(utils.t('apply_summary_count'), justify="right")
    for field, count in counts.items():
        table.add_row(labels[field], str(count))
    console.print(table)


def _filter_apply_protection(df, db_path):
    if 'FORCE_APPLY' not in df.columns:
        df['FORCE_APPLY'] = ''

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(item_attributes)")
        attr_cols = [row[1].lower() for row in cur.fetchall()]
        attr_table = "item_attributes" if attr_cols else "attributes"

        cur.execute(f"PRAGMA table_info({attr_table})")
        attr_cols = [row[1].lower() for row in cur.fetchall()]
        attr_id_col = next((c for c in ['item', 'itemidx', 'itemid', 'idx', 'id'] if c in attr_cols), None)

        if attr_id_col:
            cur.execute(f"SELECT {attr_id_col} FROM {attr_table} WHERE name = 'RESTAURIERT' AND UPPER(value) = 'JA'")
            already_restored_ids = {str(row[0]) for row in cur.fetchall()}
            force_mask = df['FORCE_APPLY'].astype(str).str.upper() == 'JA'
            protected_mask = df['ID'].astype(str).isin(already_restored_ids) & ~force_mask
            return df[~protected_mask].copy()
    except Exception as e:
        utils.log_change("ERROR", f"Apply-Schutzprüfung fehlgeschlagen: {e}")
        raise
    finally:
        if conn is not None:
            conn.close()
    return df.copy()


def phase_apply(db_path, final_csv):
    if db.verify_db_compatibility(db_path) is None:
        return
    if not os.path.exists(db_path):
        console.print(utils.t('err_file_not_found', file=db_path))
        return
    if not os.path.exists(final_csv):
        console.print(utils.t('err_file_not_found', file=final_csv) + utils.t('err_need_fetch_rev'))
        return

    console.print(Panel(utils.t('apply_warn'), box=box.HEAVY))

    if db.is_db_locked(db_path):
        console.print(Panel(utils.t('apply_locked'), box=box.HEAVY, style="red"))
        return

    df = pd.read_csv(final_csv, dtype=str)
    if 'REVIEW_STATUS' in df.columns:
        df = df[df['REVIEW_STATUS'] == 'JA'].copy()

    try:
        df = _filter_apply_protection(df, db_path)
    except Exception as e:
        console.print(utils.t('apply_err_lock', err=str(e)))
        return

    if df.empty:
        console.print(utils.t('apply_no_new'))
        return

    console.print(utils.t('apply_integrity_check'))
    integrity_ok, integrity_details = db.check_integrity(db_path)
    if not integrity_ok:
        console.print(Panel(utils.t('apply_integrity_fail', details=integrity_details), box=box.HEAVY, style="red"))
        return
    console.print(utils.t('apply_integrity_ok'))

    print_apply_summary(df, db_path)

    utils.clear_input_buffer()
    confirm_word = utils.t('apply_confirm_word')
    confirm = console.input(utils.t('apply_confirm')).strip()
    if confirm.lower() not in [confirm_word.lower(), 'j', 'ja', 'y', 'yes']:
        console.print(utils.t('apply_abort'))
        return

    backup_path = f"{db_path}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    console.print(utils.t('apply_backup', path=backup_path))

    try:
        db_dir = os.path.dirname(os.path.abspath(db_path)) or "."
        base_name = os.path.basename(db_path)
        backups = [os.path.join(db_dir, f) for f in os.listdir(db_dir) if f.startswith(base_name + ".backup-")]
        backups.sort()

        if len(backups) > 5:
            for old_backup in backups[:-5]:
                os.remove(old_backup)
            console.print(utils.t('apply_backup_clean'))
    except Exception as e:
        utils.log_change("BACKUP", f"Alte Backups konnten nicht vollständig bereinigt werden: {e}")

    applied_ids = set(df['ID'].astype(str))
    try:
        updated = db.apply_dataframe_to_mldb(df, db_path)
        console.print(utils.t('apply_success', count=updated, db=db_path))
    except sqlite3.OperationalError as e:
        console.print(utils.t('apply_err_lock', err=str(e)))
        return

    console.print(utils.t('apply_integrity_check'))
    post_ok, post_details = db.check_integrity(db_path)
    if not post_ok:
        console.print(Panel(
            utils.t('apply_integrity_after_fail', backup=backup_path, details=post_details),
            box=box.HEAVY, style="red"
        ))
        utils.log_change("CRITICAL", f"Integrität nach Apply fehlgeschlagen: {post_details}; Backup: {backup_path}")
        return
    console.print(utils.t('apply_integrity_ok'))

    try:
        df_full = pd.read_csv(final_csv, dtype=str)
        final_mask = df_full['ID'].astype(str).isin(applied_ids)
        df_full.loc[final_mask, 'RESTAURIERT'] = 'JA'
        if 'FORCE_APPLY' in df_full.columns:
            df_full.loc[final_mask, 'FORCE_APPLY'] = ''
        utils.save_safe_csv(df_full, final_csv)

        fetch_csv = final_csv.replace('_restauriert.csv', '_vorschlaege.csv')
        if os.path.exists(fetch_csv):
            df_fetch = pd.read_csv(fetch_csv, dtype=str)
            fetch_mask = df_fetch['ID'].astype(str).isin(applied_ids)
            df_fetch.loc[fetch_mask, 'RESTAURIERT'] = 'JA'
            if 'FORCE_APPLY' in df_fetch.columns:
                df_fetch.loc[fetch_mask, 'FORCE_APPLY'] = ''
            utils.save_safe_csv(df_fetch, fetch_csv)
    except Exception as e:
        utils.log_change("ERROR", f"CSV-Status nach Apply konnte nicht synchronisiert werden: {e}")


def _normalize_windows_path(path):
    """Normalize a Windows path for case-insensitive library matching."""
    raw = str(path or '').strip().strip('"').strip("'")
    if not raw:
        return ''
    raw = raw.replace('/', '\\')
    return ntpath.normpath(raw).casefold()


def _rekordbox_location_to_path(location):
    """Decode a rekordbox file:// Location into a Windows-style path."""
    raw = str(location or '').strip()
    if not raw:
        return ''
    parsed = urlparse(raw)
    if parsed.scheme.casefold() != 'file':
        return unquote(raw).replace('/', '\\')
    path = unquote(parsed.path or '')
    if parsed.netloc and parsed.netloc.casefold() not in ('', 'localhost'):
        path = f"\\\\{parsed.netloc}{path}"
    elif len(path) >= 3 and path[0] == '/' and path[2] == ':':
        path = path[1:]
    return path.replace('/', '\\')


def _load_rekordbox_bpm_xml(xml_path):
    """Load valid AverageBpm values from an exported rekordbox XML file.

    Returns (path_map, stats). Duplicate file paths are accepted only when all
    occurrences agree on BPM; conflicting duplicates are excluded for safety.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    collection = root.find('COLLECTION')
    if collection is None:
        raise ValueError('rekordbox XML: COLLECTION fehlt')

    candidates = {}
    stats = {
        'entries': 0,
        'valid_bpm': 0,
        'no_bpm': 0,
        'invalid_path': 0,
        'duplicate_paths': 0,
        'conflicting_duplicates': 0,
    }
    for track in collection.findall('TRACK'):
        stats['entries'] += 1
        location = _rekordbox_location_to_path(track.get('Location', ''))
        key = _normalize_windows_path(location)
        if not key:
            stats['invalid_path'] += 1
            continue
        try:
            source_bpm = float(str(track.get('AverageBpm', '')).replace(',', '.'))
        except (TypeError, ValueError):
            source_bpm = 0.0
        if not 30.0 <= source_bpm <= 300.0:
            stats['no_bpm'] += 1
            continue

        value = {
            'bpm': int(source_bpm + 0.5),
            'source_bpm': round(source_bpm, 2),
            'artist': str(track.get('Artist', '') or ''),
            'title': str(track.get('Name', '') or ''),
            'path': location,
            'track_id': str(track.get('TrackID', '') or ''),
        }
        stats['valid_bpm'] += 1
        if key in candidates:
            stats['duplicate_paths'] += 1
            old = candidates[key]
            if old is None or abs(float(old['source_bpm']) - source_bpm) > 0.01:
                candidates[key] = None
                stats['conflicting_duplicates'] += 1
        else:
            candidates[key] = value

    return {k: v for k, v in candidates.items() if v is not None}, stats


def _is_half_double_conflict(existing_bpm, candidate_bpm):
    try:
        a = float(existing_bpm)
        b = float(candidate_bpm)
    except (TypeError, ValueError):
        return False
    if a <= 0 or b <= 0:
        return False
    ratio = a / b
    return 1.90 <= ratio <= 2.10 or 0.475 <= ratio <= 0.525


def _new_bpm_stats(missing=0, existing=0):
    return {
        'missing': int(missing), 'existing': int(existing), 'rekordbox': 0, 'file': 0,
        'acousticbrainz': 0, 'nomatch': 0, 'errors': 0,
        'rekordbox_entries': 0, 'rekordbox_valid': 0, 'rekordbox_no_bpm': 0,
        'rekordbox_unmatched': 0, 'rekordbox_conflicts': 0,
        'diagnostics': {
            'file_unreachable': 0,
            'file_read_error': 0,
            'mb_no_match': 0,
            'mb_network': 0,
            'mb_rate_limit': 0,
            'mb_server': 0,
            'mb_http': 0,
            'mb_other': 0,
            'ab_no_data': 0,
            'ab_no_bpm': 0,
            'ab_ambiguous': 0,
            'ab_network': 0,
            'ab_rate_limit': 0,
            'ab_server': 0,
            'ab_http': 0,
            'ab_other': 0,
        },
        'review_csv': '',
    }


def _api_diag_key(prefix, exc):
    kind = getattr(exc, 'kind', 'api') or 'api'
    if kind in ('network', 'rate_limit', 'server', 'http'):
        return f'{prefix}_{kind}'
    return f'{prefix}_other'


def _save_bpm_review_csv(db_path, preview):
    """Write the complete BPM proposal list to Data as a human-reviewable CSV."""
    if not preview:
        return ''
    session_name = get_db_session_name(db_path)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    path = os.path.join(utils.DATA_DIR, f'{session_name}_bpm-review_{stamp}.csv')
    rows = []
    for row in preview:
        rows.append({
            'ID': str(row.get('id', '')),
            'Artist': str(row.get('artist', '')),
            'Title': str(row.get('title', '')),
            'BPM': str(row.get('bpm', '')),
            'Existing_BPM': str(row.get('existing_bpm', '')),
            'Source_BPM': str(row.get('source_bpm', row.get('bpm', ''))),
            'Source': str(row.get('source_name', row.get('source', ''))),
            'Status': str(row.get('status', 'VORSCHLAG')),
            'Consensus': str(row.get('consensus', '')),
            'MBID': str(row.get('mbid', '')),
            'Matched_By': str(row.get('matched_by', '')),
        })
    utils.save_safe_csv(pd.DataFrame(rows), path)
    return path


def _scan_bpm_candidates(db_path, base_dirs=None, rekordbox_xml=None):
    """Collect safe BPM proposals without writing to the database.

    Source priority: rekordbox XML (exact file path), existing audio BPM tag,
    then MusicBrainz -> AcousticBrainz. Existing valid BPM values are protected.
    """
    base_dirs = base_dirs or []
    ignored_folders = utils.get_saved_ignored_folders(db_path)
    frame = db.load_dataframe_from_mldb(db_path, ignored_folders)
    if frame is None or frame.empty:
        return {}, [], _new_bpm_stats()

    work = frame.copy()
    work['ID'] = work['ID'].astype(str)
    if 'ItemType' in work.columns:
        item_type = work['ItemType'].fillna('').astype(str).str.strip().str.casefold()
        work = work[(item_type == '') | (item_type == 'music')].copy()
    # BPM only makes sense for file-backed audio items. This also excludes
    # virtual markers such as Stundenbeginn/Stundenende.
    if 'Filename' in work.columns:
        has_file = work['Filename'].fillna('').astype(str).str.strip() != ''
        work = work[has_file].copy()

    existing_state = db.get_bpm_flag_state(db_path)
    existing_ids = set()
    for item_id, values in existing_state.items():
        if any(db._parse_bpm_value(value) is not None for _, value in values):
            existing_ids.add(str(item_id))

    existing_in_work = int(work['ID'].isin(existing_ids).sum())
    todo = work[~work['ID'].isin(existing_ids)].copy()
    stats = _new_bpm_stats(len(todo), existing_in_work)
    diag = stats['diagnostics']
    proposals = {}
    preview = []
    review_extra = []
    pending = []

    try:
        resolved_paths = db.get_resolved_item_paths(db_path, work['ID'].tolist())
    except Exception as exc:
        utils.log_change('BPM', f"mAirList-Speicherortpfade konnten nicht aufgelöst werden: {exc}")
        resolved_paths = {}

    rb_map = {}
    if rekordbox_xml:
        rb_map, rb_stats = _load_rekordbox_bpm_xml(rekordbox_xml)
        stats['rekordbox_entries'] = rb_stats['entries']
        stats['rekordbox_valid'] = rb_stats['valid_bpm']
        stats['rekordbox_no_bpm'] = rb_stats['no_bpm']

        # Existing BPM values remain untouched. Only material discrepancies are
        # surfaced in the review CSV so half/double-time cases are visible.
        existing_rows = work[work['ID'].isin(existing_ids)]
        for _, row in existing_rows.iterrows():
            item_id = str(row.get('ID', '')).strip()
            raw_path = resolved_paths.get(item_id) or utils.clean_nan(row.get('Filename', ''))
            rb = rb_map.get(_normalize_windows_path(raw_path))
            if not rb:
                continue
            existing_bpm = None
            for _, value in existing_state.get(item_id, []):
                parsed = db._parse_bpm_value(value)
                if parsed is not None:
                    existing_bpm = parsed
                    break
            if existing_bpm is None:
                continue
            significant = abs(float(existing_bpm) - float(rb['bpm'])) >= 5.0
            half_double = _is_half_double_conflict(existing_bpm, rb['bpm'])
            if not (significant or half_double):
                continue
            status = 'HALF_DOUBLE_KONFLIKT' if half_double else 'ABWEICHUNG'
            stats['rekordbox_conflicts'] += 1
            review_extra.append({
                'id': item_id,
                'artist': utils.clean_nan(row.get('Artist', '')),
                'title': utils.clean_nan(row.get('Title', '')),
                'bpm': rb['bpm'],
                'existing_bpm': existing_bpm,
                'source_bpm': rb['source_bpm'],
                'source': utils.t('maint_bpm_source_rb'),
                'source_name': 'rekordbox XML',
                'status': status,
                'consensus': '', 'mbid': '', 'matched_by': 'Dateipfad',
            })

    if todo.empty:
        try:
            stats['review_csv'] = _save_bpm_review_csv(db_path, review_extra)
        except Exception as exc:
            utils.log_change('BPM', f"BPM-Review-CSV konnte nicht geschrieben werden: {exc}")
        return proposals, preview, stats

    with Progress(
        SpinnerColumn(),
        TextColumn('[progress.description]{task.description}'),
        BarColumn(),
        TextColumn('{task.completed}/{task.total}'),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task('BPM: rekordbox / Datei-Tags / MusicBrainz', total=len(todo))
        for _, row in todo.iterrows():
            item_id = str(row.get('ID', '')).strip()
            artist = utils.clean_nan(row.get('Artist', ''))
            title = utils.clean_nan(row.get('Title', ''))
            filename = utils.clean_nan(row.get('Filename', ''))
            isrc = utils.clean_nan(row.get('ISRC', ''))
            resolved = resolved_paths.get(item_id) or filename
            try:
                duration = float(row.get('Duration', 0) or 0)
            except (TypeError, ValueError):
                duration = 0.0

            if rb_map:
                rb = rb_map.get(_normalize_windows_path(resolved))
                if rb:
                    bpm = int(rb['bpm'])
                    proposals[item_id] = bpm
                    preview.append({
                        'id': item_id, 'artist': artist, 'title': title, 'bpm': bpm,
                        'existing_bpm': '', 'source_bpm': rb['source_bpm'],
                        'source': utils.t('maint_bpm_source_rb'),
                        'source_name': 'rekordbox XML',
                        'status': 'VORSCHLAG', 'consensus': '', 'mbid': '',
                        'matched_by': 'Dateipfad',
                    })
                    stats['rekordbox'] += 1
                    progress.advance(task)
                    continue
                stats['rekordbox_unmatched'] += 1

            audio_meta = db.read_audio_bpm_metadata(resolved, base_dirs)
            file_status = audio_meta.get('file_status', '')
            if file_status == 'not_found':
                diag['file_unreachable'] += 1
            elif file_status == 'read_error':
                diag['file_read_error'] += 1
                stats['errors'] += 1

            if audio_meta.get('bpm') is not None:
                bpm = int(audio_meta['bpm'])
                proposals[item_id] = bpm
                preview.append({
                    'id': item_id, 'artist': artist, 'title': title, 'bpm': bpm,
                    'existing_bpm': '', 'source_bpm': bpm,
                    'source': utils.t('maint_bpm_source_file'),
                    'source_name': utils.t('maint_bpm_source_file'),
                    'status': 'VORSCHLAG',
                    'consensus': '', 'mbid': audio_meta.get('mbid', ''),
                    'matched_by': 'Datei-Tag',
                })
                stats['file'] += 1
                progress.advance(task)
                continue

            mbid = audio_meta.get('mbid', '')
            matched_by = 'Datei-MBID' if mbid else ''
            if not mbid:
                try:
                    match = api.find_musicbrainz_recording_for_bpm(
                        artist, title, isrc=isrc, local_duration_sec=duration
                    )
                except api.APIRequestError as exc:
                    utils.log_change('BPM', f"MusicBrainz-Fehler bei {artist} - {title}: {exc}")
                    diag[_api_diag_key('mb', exc)] += 1
                    stats['errors'] += 1
                    progress.advance(task)
                    continue
                if match:
                    mbid = match['mbid']
                    matched_by = match.get('matched_by', '')

            if mbid:
                pending.append({
                    'id': item_id, 'artist': artist, 'title': title,
                    'mbid': mbid.lower(), 'matched_by': matched_by,
                })
            else:
                diag['mb_no_match'] += 1
                stats['nomatch'] += 1
            progress.advance(task)

    if pending:
        console.print(f"[cyan]AcousticBrainz: {len(pending)} eindeutig zugeordnete Recording(s) auf BPM prüfen...[/cyan]")
        ab_response = api.fetch_acousticbrainz_bpms(
            [row['mbid'] for row in pending], include_status=True
        )
        if isinstance(ab_response, tuple) and len(ab_response) == 2:
            ab_values, ab_status = ab_response
        else:
            ab_values = ab_response or {}
            ab_status = {
                row['mbid']: {'status': 'ok' if row['mbid'] in ab_values else 'no_data'}
                for row in pending
            }

        for row in pending:
            selected = ab_values.get(row['mbid'])
            if selected:
                bpm = int(selected['bpm'])
                proposals[row['id']] = bpm
                consensus = f"{selected['agree']}/{selected['total']}"
                preview.append({
                    'id': row['id'], 'artist': row['artist'], 'title': row['title'],
                    'bpm': bpm, 'existing_bpm': '', 'source_bpm': bpm,
                    'source': utils.t(
                        'maint_bpm_source_ab', agree=selected['agree'], total=selected['total']
                    ),
                    'source_name': 'AcousticBrainz', 'status': 'VORSCHLAG',
                    'consensus': consensus, 'mbid': row['mbid'],
                    'matched_by': row.get('matched_by', ''),
                })
                stats['acousticbrainz'] += 1
                continue

            info = ab_status.get(row['mbid'], {'status': 'no_data'})
            status_name = info.get('status', 'no_data')
            if status_name == 'api_error':
                kind = info.get('kind', 'api')
                key = f'ab_{kind}' if f'ab_{kind}' in diag else 'ab_other'
                diag[key] += 1
                stats['errors'] += 1
            elif status_name == 'ambiguous':
                diag['ab_ambiguous'] += 1
                stats['nomatch'] += 1
            elif status_name == 'no_bpm':
                diag['ab_no_bpm'] += 1
                stats['nomatch'] += 1
            else:
                diag['ab_no_data'] += 1
                stats['nomatch'] += 1

    try:
        stats['review_csv'] = _save_bpm_review_csv(db_path, preview + review_extra)
    except Exception as exc:
        utils.log_change('BPM', f"BPM-Review-CSV konnte nicht geschrieben werden: {exc}")
        stats['review_csv'] = ''

    return proposals, preview, stats

def _print_bpm_preview(preview, limit=40):
    if not preview:
        return
    table = Table(title=utils.t('maint_bpm_preview'), box=box.ROUNDED)
    table.add_column('ID', justify='right')
    table.add_column('Artist - Title')
    table.add_column('BPM', justify='right')
    table.add_column('Quelle / Source')
    for row in preview[:limit]:
        label = f"{row['artist']} - {row['title']}".strip(' -')
        table.add_row(str(row['id']), label, str(row['bpm']), str(row['source']))
    console.print(table)
    if len(preview) > limit:
        console.print(f"[dim]… {len(preview) - limit} weitere Vorschläge werden aus Platzgründen nicht angezeigt.[/dim]")


def _print_bpm_diagnostics(stats):
    diag = stats.get('diagnostics') or {}
    rows = [
        ('maint_bpm_diag_file_unreachable', 'file_unreachable'),
        ('maint_bpm_diag_file_read', 'file_read_error'),
        ('maint_bpm_diag_mb_nomatch', 'mb_no_match'),
        ('maint_bpm_diag_mb_network', 'mb_network'),
        ('maint_bpm_diag_mb_rate', 'mb_rate_limit'),
        ('maint_bpm_diag_mb_server', 'mb_server'),
        ('maint_bpm_diag_mb_http', 'mb_http'),
        ('maint_bpm_diag_mb_other', 'mb_other'),
        ('maint_bpm_diag_ab_nodata', 'ab_no_data'),
        ('maint_bpm_diag_ab_nobpm', 'ab_no_bpm'),
        ('maint_bpm_diag_ab_ambiguous', 'ab_ambiguous'),
        ('maint_bpm_diag_ab_network', 'ab_network'),
        ('maint_bpm_diag_ab_rate', 'ab_rate_limit'),
        ('maint_bpm_diag_ab_server', 'ab_server'),
        ('maint_bpm_diag_ab_http', 'ab_http'),
        ('maint_bpm_diag_ab_other', 'ab_other'),
    ]
    if not any(diag.get(key, 0) for _, key in rows):
        return
    table = Table(title=utils.t('maint_bpm_diag_title'), box=box.ROUNDED)
    table.add_column(utils.t('maint_bpm_diag_kind'))
    table.add_column(utils.t('apply_summary_count'), justify='right')
    for label_key, key in rows:
        count = int(diag.get(key, 0) or 0)
        if count:
            table.add_row(utils.t(label_key), str(count))
    console.print(table)

def phase_maintenance(db_path):
    if db.verify_db_compatibility(db_path) is None:
        return
    if not os.path.exists(db_path):
        console.print(utils.t('err_file_not_found', file=db_path))
        return

    if db.is_db_locked(db_path):
        console.print(Panel(utils.t('apply_locked'), box=box.HEAVY, style="red"))
        return
        
    while True:
        utils.clear_input_buffer()
        console.print(utils.t('maint_title'))
        console.print(Panel(utils.t('maint_warn'), box=box.HEAVY))
        console.print(utils.t('maint_opt1'))
        console.print(utils.t('maint_opt2'))
        console.print(utils.t('maint_opt3'))
        console.print(utils.t('maint_opt4'))
        console.print(utils.t('maint_opt5'))
        console.print(utils.t('maint_opt6'))
        console.print(utils.t('maint_opt7'))
        console.print(utils.t('maint_opt0'))
        
        choice = console.input(f"\n[cyan]{utils.t('maint_prompt')}[/cyan]").strip()
        
        if choice == '0':
            break
        elif choice in ['1', '2', '3', '4', '5', '6', '7']:
            do_genres = choice in ['1', '4']
            do_case   = choice in ['2', '4']
            do_tags   = choice == '3'
            do_duplicates = choice == '5'
            do_bpm = choice == '6'
            do_speed = choice == '7'
            
            try:
                if do_genres:
                    count = db.run_maintenance_genres(db_path)
                    if count > 0: console.print(utils.t('std_done', count=count))
                    else: console.print(utils.t('maint_no_changes'))
                        
                if do_case:
                    count = db.run_maintenance_case(db_path)
                    if count > 0: console.print(utils.t('maint_done_case', count=count))
                    else: console.print(utils.t('maint_no_changes'))
                        
                if do_tags:
                    count = db.run_maintenance_file_tagger(db_path)
                    if count > 0: console.print(utils.t('maint_done_tags', count=count))
                    else: console.print(utils.t('maint_no_changes'))

                if do_duplicates:
                    console.print(utils.t('maint_dup_scan'))
                    ignored_folders = utils.get_saved_ignored_folders(db_path)
                    frame = db.load_dataframe_from_mldb(db_path, ignored_folders)
                    groups = db.find_duplicate_groups(frame)
                    candidate_ids = set().union(*groups) if groups else set()

                    flag_state = db.get_duplicate_flag_state(db_path)
                    existing_ids = set(flag_state)
                    existing_ja = {
                        item_id for item_id, values in flag_state.items()
                        if any(value.strip().upper() == 'JA' for _, value in values)
                    }
                    new_count = len(candidate_ids - existing_ja)
                    still_count = len(candidate_ids & existing_ja)
                    removed_count = len(existing_ids - candidate_ids)

                    table = Table(title=utils.t('maint_dup_summary_title'), box=box.ROUNDED)
                    table.add_column(utils.t('apply_summary_field'))
                    table.add_column(utils.t('apply_summary_count'), justify='right')
                    table.add_row(utils.t('maint_dup_groups'), str(len(groups)))
                    table.add_row(utils.t('maint_dup_items'), str(len(candidate_ids)))
                    table.add_row(utils.t('maint_dup_new'), str(new_count))
                    table.add_row(utils.t('maint_dup_still'), str(still_count))
                    table.add_row(utils.t('maint_dup_removed'), str(removed_count))
                    console.print(table)

                    if new_count == 0 and removed_count == 0:
                        console.print(utils.t('maint_dup_nochange'))
                    else:
                        console.print(utils.t('apply_integrity_check'))
                        integrity_ok, integrity_details = db.check_integrity(db_path)
                        if not integrity_ok:
                            console.print(Panel(
                                utils.t('apply_integrity_fail', details=integrity_details),
                                box=box.HEAVY, style='red'
                            ))
                            break
                        console.print(utils.t('apply_integrity_ok'))

                        backup_path = f"{db_path}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                        shutil.copy2(db_path, backup_path)
                        console.print(utils.t('apply_backup', path=backup_path))

                        try:
                            db_dir = os.path.dirname(os.path.abspath(db_path)) or "."
                            base_name = os.path.basename(db_path)
                            backups = [
                                os.path.join(db_dir, f) for f in os.listdir(db_dir)
                                if f.startswith(base_name + ".backup-")
                            ]
                            backups.sort()
                            if len(backups) > 5:
                                for old_backup in backups[:-5]:
                                    os.remove(old_backup)
                                console.print(utils.t('apply_backup_clean'))
                        except Exception as e:
                            utils.log_change('BACKUP', f"Alte Backups konnten nicht vollständig bereinigt werden: {e}")

                        result = db.apply_duplicate_flags(db_path, candidate_ids)

                        console.print(utils.t('apply_integrity_check'))
                        post_ok, post_details = db.check_integrity(db_path)
                        if not post_ok:
                            console.print(Panel(
                                utils.t('apply_integrity_after_fail', backup=backup_path, details=post_details),
                                box=box.HEAVY, style='red'
                            ))
                            utils.log_change(
                                'CRITICAL',
                                f"Integrität nach Dopplungsprüfung fehlgeschlagen: {post_details}; Backup: {backup_path}"
                            )
                            break
                        console.print(utils.t('apply_integrity_ok'))
                        console.print(utils.t(
                            'maint_dup_done',
                            new=result['new'], still=result['unchanged'], removed=result['removed']
                        ))

                if do_bpm:
                    console.print(utils.t('maint_bpm_intro'))
                    rekordbox_xml = _select_fetch_rekordbox_xml(db_path)
                    console.print(Panel(utils.t('maint_bpm_path_intro'), box=box.ROUNDED))
                    saved_dirs = utils.get_saved_source_folders(db_path)
                    if saved_dirs:
                        console.print(utils.t('source_dirs_saved', paths=', '.join(saved_dirs)))
                    else:
                        console.print(utils.t('source_dirs_none'))
                    base_dirs = [d for d in saved_dirs if os.path.isdir(d)]
                    added_dirs = []
                    while True:
                        raw_dir = console.input(utils.t('maint_bpm_path_prompt')).strip().strip('\"').strip("'")
                        if not raw_dir:
                            break
                        if os.path.isdir(raw_dir):
                            raw_dir = os.path.abspath(raw_dir)
                            if os.path.normcase(raw_dir) not in {os.path.normcase(x) for x in base_dirs}:
                                base_dirs.append(raw_dir)
                                added_dirs.append(raw_dir)
                            console.print(utils.t('maint_bpm_path_added', path=raw_dir))
                        else:
                            console.print(utils.t('maint_bpm_path_invalid'))
                    if added_dirs:
                        utils.save_source_folders(db_path, saved_dirs + added_dirs)

                    proposals, preview, stats = _scan_bpm_candidates(db_path, base_dirs, rekordbox_xml=rekordbox_xml)
                    _print_bpm_preview(preview)

                    table = Table(title=utils.t('maint_bpm_summary_title'), box=box.ROUNDED)
                    table.add_column(utils.t('apply_summary_field'))
                    table.add_column(utils.t('apply_summary_count'), justify='right')
                    table.add_row(utils.t('maint_bpm_missing'), str(stats['missing']))
                    table.add_row(utils.t('maint_bpm_existing'), str(stats['existing']))
                    if rekordbox_xml:
                        console.print(utils.t(
                            'maint_bpm_rb_loaded',
                            entries=stats.get('rekordbox_entries', 0),
                            valid=stats.get('rekordbox_valid', 0)
                        ))
                        table.add_row(utils.t('maint_bpm_rb'), str(stats.get('rekordbox', 0)))
                        table.add_row(utils.t('maint_bpm_rb_unmatched'), str(stats.get('rekordbox_unmatched', 0)))
                        table.add_row(utils.t('maint_bpm_rb_conflicts'), str(stats.get('rekordbox_conflicts', 0)))
                    table.add_row(utils.t('maint_bpm_file'), str(stats['file']))
                    table.add_row(utils.t('maint_bpm_ab'), str(stats['acousticbrainz']))
                    table.add_row(utils.t('maint_bpm_nomatch'), str(stats['nomatch']))
                    table.add_row(utils.t('maint_bpm_errors'), str(stats['errors']))
                    console.print(table)
                    _print_bpm_diagnostics(stats)
                    if stats.get('review_csv'):
                        console.print(utils.t('maint_bpm_review_saved', path=stats['review_csv']))

                    if not proposals:
                        console.print(utils.t('maint_bpm_nochange'))
                    else:
                        answer = console.input(
                            f"[yellow]{utils.t('maint_bpm_confirm', count=len(proposals))}[/yellow]"
                        ).strip().lower()
                        if answer not in ['j', 'ja', 'y', 'yes']:
                            console.print(utils.t('maint_bpm_cancel'))
                        else:
                            console.print(utils.t('apply_integrity_check'))
                            integrity_ok, integrity_details = db.check_integrity(db_path)
                            if not integrity_ok:
                                console.print(Panel(
                                    utils.t('apply_integrity_fail', details=integrity_details),
                                    box=box.HEAVY, style='red'
                                ))
                                break
                            console.print(utils.t('apply_integrity_ok'))

                            backup_path = f"{db_path}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                            shutil.copy2(db_path, backup_path)
                            console.print(utils.t('apply_backup', path=backup_path))

                            try:
                                db_dir = os.path.dirname(os.path.abspath(db_path)) or '.'
                                base_name = os.path.basename(db_path)
                                backups = [
                                    os.path.join(db_dir, f) for f in os.listdir(db_dir)
                                    if f.startswith(base_name + '.backup-')
                                ]
                                backups.sort()
                                if len(backups) > 5:
                                    for old_backup in backups[:-5]:
                                        os.remove(old_backup)
                                    console.print(utils.t('apply_backup_clean'))
                            except Exception as e:
                                utils.log_change('BACKUP', f"Alte Backups konnten nicht vollständig bereinigt werden: {e}")

                            result = db.apply_bpm_values(db_path, proposals)

                            console.print(utils.t('apply_integrity_check'))
                            post_ok, post_details = db.check_integrity(db_path)
                            if not post_ok:
                                console.print(Panel(
                                    utils.t('apply_integrity_after_fail', backup=backup_path, details=post_details),
                                    box=box.HEAVY, style='red'
                                ))
                                utils.log_change(
                                    'CRITICAL',
                                    f"Integrität nach BPM-Wartung fehlgeschlagen: {post_details}; Backup: {backup_path}"
                                )
                                break
                            console.print(utils.t('apply_integrity_ok'))
                            console.print(utils.t(
                                'maint_bpm_done',
                                written=result['written'], skipped=result['skipped_existing']
                            ))

                if do_speed:
                    console.print(utils.t('maint_speed_intro'))
                    assignments, stats = db.scan_speed_group_candidates(db_path)
                    table = Table(title=utils.t('maint_speed_summary_title'), box=box.ROUNDED)
                    table.add_column(utils.t('apply_summary_field'))
                    table.add_column(utils.t('apply_summary_count'), justify='right')
                    table.add_row(utils.t('maint_speed_with_bpm'), str(stats['with_bpm']))
                    table.add_row(utils.t('maint_speed_existing'), str(stats['existing']))
                    table.add_row(utils.t('maint_speed_candidates'), str(stats['candidates']))
                    table.add_row(utils.t('maint_speed_slow'), str(stats['slow']))
                    table.add_row(utils.t('maint_speed_medium'), str(stats['medium']))
                    table.add_row(utils.t('maint_speed_fast'), str(stats['fast']))
                    if stats.get('ambiguous'):
                        table.add_row(utils.t('maint_speed_ambiguous'), str(stats['ambiguous']))
                    console.print(table)

                    if not assignments:
                        console.print(utils.t('maint_speed_nochange'))
                    else:
                        answer = console.input(
                            f"[yellow]{utils.t('maint_speed_confirm', count=len(assignments))}[/yellow]"
                        ).strip().lower()
                        if answer not in ['j', 'ja', 'y', 'yes']:
                            console.print(utils.t('maint_speed_cancel'))
                        else:
                            console.print(utils.t('apply_integrity_check'))
                            integrity_ok, integrity_details = db.check_integrity(db_path)
                            if not integrity_ok:
                                console.print(Panel(
                                    utils.t('apply_integrity_fail', details=integrity_details),
                                    box=box.HEAVY, style='red'
                                ))
                                break
                            console.print(utils.t('apply_integrity_ok'))

                            backup_path = f"{db_path}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                            shutil.copy2(db_path, backup_path)
                            console.print(utils.t('apply_backup', path=backup_path))

                            result = db.apply_speed_groups(db_path, assignments)

                            console.print(utils.t('apply_integrity_check'))
                            post_ok, post_details = db.check_integrity(db_path)
                            if not post_ok:
                                console.print(Panel(
                                    utils.t('apply_integrity_after_fail', backup=backup_path, details=post_details),
                                    box=box.HEAVY, style='red'
                                ))
                                utils.log_change(
                                    'CRITICAL',
                                    f"Integrität nach Geschwindigkeits-Wartung fehlgeschlagen: {post_details}; Backup: {backup_path}"
                                )
                                break
                            console.print(utils.t('apply_integrity_ok'))
                            console.print(utils.t(
                                'maint_speed_done',
                                written=result['written'], skipped=result['skipped_existing']
                            ))
                        
            except sqlite3.OperationalError as e:
                console.print(utils.t('apply_err_lock', err=str(e)))
            except Exception as e:
                utils.log_change('ERROR', f"Wartungsfunktion fehlgeschlagen: {e}")
                console.print(Panel(str(e), box=box.HEAVY, style='red'))
            break
        else:
            continue

def select_language():
    clear_screen()
    console.print(f"[cyan]==================================================[/cyan]")
    console.print(f"[magenta]   mAirList DB Restorer v{utils.APP_VERSION} - Language Setup[/magenta]")
    console.print(f"[cyan]==================================================[/cyan]\n")
    console.print("  [green]1[/green] Deutsch\n  [green]2[/green] English\n  [green]3[/green] Nederlands\n")
    
    while True:
        lang_choice = console.input("[cyan]Select / Auswahl / Keuze [1-3]: [/cyan]").strip()
        if lang_choice == '1': 
            utils.save_language('de')
            break
        elif lang_choice == '2': 
            utils.save_language('en')
            break
        elif lang_choice == '3': 
            utils.save_language('nl')
            break

def _activate_database(db_path):
    """Validate a database and prepare its session files; return a tuple or None."""
    clean = str(db_path or '').strip().strip('"').strip("'")
    if not clean or db.verify_db_compatibility(clean) is None:
        return None
    clean = os.path.abspath(clean)
    utils.save_database_context(clean)
    db_base_name, data_dir = setup_logging(clean)
    fetch_csv = os.path.join(data_dir, f"{db_base_name}_vorschlaege.csv")
    final_csv = os.path.join(data_dir, f"{db_base_name}_restauriert.csv")
    return clean, fetch_csv, final_csv


def run_interactive_menu():
    if not utils.load_language():
        select_language()

    clear_screen()
    check_for_updates(interactive=True)
    perform_migration()
    utils.init_credentials()

    mldbpfad = ""
    fetch_csv = ""
    final_csv = ""
    saved_db = utils.get_last_database()
    if saved_db:
        if os.path.isfile(saved_db):
            clear_screen()
            console.print(f"[cyan]{utils.t('startup_last_db')}[/cyan] {saved_db}")
            answer = console.input(utils.t('startup_keep_db')).strip().lower()
            if answer not in ['n', 'nein', 'no', 'nee']:
                active = _activate_database(saved_db)
                if active:
                    mldbpfad, fetch_csv, final_csv = active
        else:
            console.print(utils.t('startup_last_db_missing'))

    while True:
        clear_screen()
        console.print(f"[cyan]==================================================[/cyan]")
        console.print(f"[magenta]   {utils.t('menu_title')} v{utils.APP_VERSION}[/magenta]\n")
        console.print(f"[magenta]       {utils.t('menu_copyright')}[/magenta]")
        console.print(f"[cyan]==================================================[/cyan]\n")

        if not mldbpfad:
            console.print(f"[yellow] {utils.t('menu_db_none')}[/yellow]")
        else:
            console.print(f"[green] {utils.t('menu_db_act')} {mldbpfad}[/green]")

        console.print(f"\n  [[cyan]0[/cyan]] [bold]{utils.t('menu_opt0')}[/bold]")
        console.print(f"      [dim]{utils.t('menu_desc0')}[/dim]\n")

        console.print(f"[yellow] {utils.t('menu_h1')}[/yellow]")
        for num in ('1', '2', '3'):
            console.print(f"  [[green]{num}[/green]] [bold]{utils.t('menu_opt' + num)}[/bold]")
            console.print(f"      [dim]{utils.t('menu_desc' + num)}[/dim]")
        console.print()

        console.print(f"[yellow] {utils.t('menu_h2')}[/yellow]")
        for num in ('4', '5'):
            console.print(f"  [[green]{num}[/green]] [bold]{utils.t('menu_opt' + num)}[/bold]")
            console.print(f"      [dim]{utils.t('menu_desc' + num)}[/dim]")
        console.print()

        console.print(f"[yellow] {utils.t('menu_h3')}[/yellow]")
        console.print(f"  [[green]6[/green]] [bold]{utils.t('menu_opt6')}[/bold]")
        console.print(f"      [dim]{utils.t('menu_desc6')}[/dim]\n")

        console.print(f"[yellow] {utils.t('menu_h4')}[/yellow]")
        console.print(f"  [[green]7[/green]] [bold]{utils.t('menu_opt7')}[/bold]")
        console.print(f"      [dim]{utils.t('menu_desc7')}[/dim]\n")

        console.print(f"  [[green]8[/green]] {utils.t('menu_opt8')}")
        console.print(f"  [[green]9[/green]] {utils.t('menu_opt9')}")
        console.print(f"\n[cyan]💡 {utils.t('menu_workflow')}[/cyan]\n")

        wahl = console.input(f"[cyan]{utils.t('menu_prompt')} [/cyan]").strip()

        if wahl == '9':
            break

        elif wahl == '8':
            select_language()
            continue

        elif wahl == '0':
            console.print(f"\n[cyan]{utils.t('menu_path_hint1')}[/cyan]")
            console.print(f"[yellow]{utils.t('menu_path_hint2')}[/yellow]")
            selected = console.input(f"{utils.t('menu_path_prompt')}").strip().strip('"').strip("'")
            if selected:
                active = _activate_database(selected)
                if not active:
                    mldbpfad = ""
                    console.input(f"\n[cyan]{utils.t('menu_continue')}[/cyan]")
                    continue
                mldbpfad, fetch_csv, final_csv = active
            continue

        if not mldbpfad:
            console.print(f"\n[bold red]{utils.t('menu_err_db')}[/bold red]")
            console.input(f"\n[cyan]{utils.t('menu_continue')}[/cyan]")
            continue

        if wahl == '1':
            rb_xml = _select_fetch_rekordbox_xml(mldbpfad)
            phase_fetch(mldbpfad, fetch_csv, full=False, no_breaks=False, rekordbox_xml=rb_xml)
        elif wahl == '2':
            rb_xml = _select_fetch_rekordbox_xml(mldbpfad)
            phase_fetch(mldbpfad, fetch_csv, full=False, no_breaks=True, rekordbox_xml=rb_xml)
        elif wahl == '3':
            console.print(f"\n[bold yellow]{utils.t('menu_warn_full')}[/bold yellow]")
            bestaetigung = console.input(f"{utils.t('menu_sure')}").strip().lower()
            if bestaetigung in ['j', 'y', 'ja', 'yes']:
                rb_xml = _select_fetch_rekordbox_xml(mldbpfad)
                phase_fetch(mldbpfad, fetch_csv, full=True, no_breaks=True, rekordbox_xml=rb_xml)
        elif wahl == '4':
            phase_review(fetch_csv, final_csv, auto_hoch=False)
        elif wahl == '5':
            phase_review(fetch_csv, final_csv, auto_hoch=True)
        elif wahl == '6':
            phase_maintenance(mldbpfad)
        elif wahl == '7':
            console.print(f"\n[bold yellow]{utils.t('menu_warn_apply1')}\n{utils.t('menu_warn_apply2')}[/bold yellow]\n")
            phase_apply(mldbpfad, final_csv)
        else:
            console.print(f"[bold red]{utils.t('menu_err')}[/bold red]")

        console.input(f"\n[cyan]{utils.t('menu_continue')}[/cyan]")

def main():
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description=f"mAirList DB Restorer v{utils.APP_VERSION}")
        parser.add_argument('phase', choices=['fetch', 'review', 'apply', 'maintenance', 'check_update'])
        parser.add_argument('--auto-hoch', action='store_true')
        parser.add_argument('--full', action='store_true')
        parser.add_argument('--db', help="Pfad zur mAirList .mldb-Datei")
        parser.add_argument('--lang', choices=['de', 'en', 'nl'], default='de')
        parser.add_argument('--no-breaks', action='store_true', help="Schaltet die 50-Track-Pausen ab")
        parser.add_argument('--rekordbox-xml', help="Optionaler rekordbox-XML-Export als primäre BPM-Quelle")
        args = parser.parse_args()

        utils.save_language(args.lang)
        
        if args.phase == 'check_update':
            check_for_updates()
            return
            
        if not args.db:
            console.print("[red]Fehler: --db Argument fehlt![/red]")
            sys.exit(1)
        
        if db.verify_db_compatibility(args.db) is None:
            sys.exit(1)
        perform_migration()
        db_base_name, data_dir = setup_logging(args.db)
        utils.init_credentials()

        fetch_csv = os.path.join(data_dir, f"{db_base_name}_vorschlaege.csv")
        final_csv = os.path.join(data_dir, f"{db_base_name}_restauriert.csv")

        if args.phase == 'fetch': phase_fetch(args.db, fetch_csv, full=args.full, no_breaks=args.no_breaks, rekordbox_xml=args.rekordbox_xml)
        elif args.phase == 'review': phase_review(fetch_csv, final_csv, auto_hoch=args.auto_hoch)
        elif args.phase == 'maintenance': phase_maintenance(args.db)
        else: phase_apply(args.db, final_csv)
    else:
        run_interactive_menu()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        console.print(f"\n[bold red]Ein unerwarteter Fehler ist aufgetreten:[/bold red]")
        console.print(traceback.format_exc())
        input("\nProgramm wurde unerwartet beendet. Drücke Enter, um das Fenster zu schließen...")
    except KeyboardInterrupt:
        pass