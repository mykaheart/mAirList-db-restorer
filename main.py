import pandas as pd
import os
import sys
import argparse
import logging
import shutil
import sqlite3
import time
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
from rich import box
import requests

import utils
import api
import db

console = Console(highlight=False)

PROPOSAL_COLUMNS = [
    'Artist_Vorschlag', 'Title_Vorschlag', 'Jahr_Vorschlag', 'Jahr_Konfidenz',
    'Genre_Vorschlag', 'Album_Vorschlag', 'STYLE_Vorschlag', 'DISCOGS_RELEASE_ID_Vorschlag',
    'Label_Vorschlag', 'Labelcode_Vorschlag', 'ISRC_Vorschlag', 'Sprache_Vorschlag', 
    'Typ_Vorschlag', 'VORSCHLAG_STATUS',
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

def check_for_updates(interactive=False):
    try:
        url = "https://raw.githubusercontent.com/mykaheart/mAirList-db-restorer/main/utils.py"
        res = requests.get(url, timeout=1.5)
        if res.status_code == 200:
            for line in res.text.splitlines():
                if line.startswith("APP_VERSION ="):
                    remote_version = line.split("=")[1].strip().strip('"').strip("'")
                    
                    # --- SMART VERSION COMPARISON ---
                    # Verwandelt z.B. "0.62.03 Beta" in (0, 62, 3) um es mathematisch zu vergleichen
                    def get_v_tuple(v_str):
                        try:
                            num_part = v_str.split()[0]
                            return tuple(int(x) for x in num_part.split('.'))
                        except Exception:
                            return (0, 0, 0)
                            
                    remote_tuple = get_v_tuple(remote_version)
                    local_tuple = get_v_tuple(utils.APP_VERSION)
                    
                    # Schlägt nur noch an, wenn die Github-Version ECHT größer ist
                    if remote_tuple > local_tuple:
                        console.print(f"[bold yellow]⚡ Update verfügbar! Neue Version {remote_version} wurde veröffentlicht (Du nutzt {utils.APP_VERSION}).[/bold yellow]")
                        console.print(f"[bold cyan]👉 Download als fertige ZIP-Datei (inkl. Handbüchern) hier:[/bold cyan]")
                        console.print(f"[white]https://drive.google.com/file/d/1lV2qG7nSj28BKC2W5FoPn4bgfqqsDjdM/view?usp=sharing[/white]")
                        
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

def setup_logging(db_path):
    data_dir = "Data"
    os.makedirs(data_dir, exist_ok=True)
    db_base_name = os.path.splitext(os.path.basename(db_path))[0]
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    dynamic_log_file = os.path.join(data_dir, f"{db_base_name}_{timestamp_str}.log")
    
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        filename=dynamic_log_file,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8'
    )
    return db_base_name, data_dir

def perform_migration():
    data_dir = "Data"
    os.makedirs(data_dir, exist_ok=True)
    for f in os.listdir('.'):
        if f.endswith('_vorschlaege.csv') or f.endswith('_restauriert.csv') or f.endswith('.log') or f == 'config.json':
            if os.path.isfile(f):
                target_path = os.path.join(data_dir, f)
                try:
                    if not os.path.exists(target_path):
                        shutil.move(f, target_path)
                    else:
                        os.remove(f) 
                except Exception:
                    pass

def phase_fetch(db_path, fetch_csv, full=False, no_breaks=False):
    db.verify_db_compatibility(db_path)
    if db.is_db_locked(db_path):
        console.print(Panel(utils.t('apply_locked'), box=box.HEAVY, style="red"))
        return

    ignored_folders = utils.setup_ignored_folders(db_path)
    input_df = db.load_dataframe_from_mldb(db_path, ignored_folders)
    
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

    if 'RESTAURIERT' in input_df.columns:
        db_restauriert = input_df.set_index('ID')['RESTAURIERT'].to_dict()
        
        if 'RESTAURIERT' in df.columns:
            reset_count = 0
            for idx, row in df.iterrows():
                item_id = str(row.get('ID', ''))
                old_val = str(row.get('RESTAURIERT', '')).strip().upper()
                new_val = str(db_restauriert.get(item_id, '')).strip().upper()
                
                if old_val == 'JA' and new_val != 'JA':
                    df.at[idx, 'VORSCHLAG_STATUS'] = ''
                    if 'REVIEW_STATUS' in df.columns:
                        df.at[idx, 'REVIEW_STATUS'] = ''
                        
                    db_row = input_df[input_df['ID'] == item_id]
                    if not db_row.empty:
                        df.at[idx, 'Artist'] = db_row.iloc[0].get('Artist', '')
                        df.at[idx, 'Title'] = db_row.iloc[0].get('Title', '')
                    reset_count += 1
                    
            if reset_count > 0:
                console.print(utils.t('fetch_reset', count=reset_count))
                
        df['RESTAURIERT'] = df['ID'].map(db_restauriert).fillna('')

    if not full:
        already_done = df['RESTAURIERT'].astype(str).str.upper() == 'JA'
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

                    art_sugg = api.suggest_artist_spelling(c_art) or c_art
                    tit_sugg = api.suggest_title_spelling(art_sugg, c_tit, local_dur) or c_tit

                    with ThreadPoolExecutor(max_workers=2) as executor:
                        future_mb = executor.submit(api.fetch_musicbrainz_details, art_sugg, tit_sugg, None, None, local_dur)
                        future_discogs = executor.submit(api.fetch_discogs_details, art_sugg, tit_sugg, None, None)
                        
                        mb_year, mb_conf, isrc, mb_album, mb_lang = future_mb.result()
                        discogs_res = future_discogs.result()

                    all_years = [mb_year] if mb_year else []
                    all_years += [y for y in discogs_res['years']]
                    oldest_year = utils.filter_valid_years(all_years)

                    conf_rank = {'hoch': 2, 'mittel': 1, 'niedrig': 0}
                    rank_to_conf = {2: 'hoch', 1: 'mittel', 0: 'niedrig'}
                    best_rank = max(conf_rank.get(mb_conf, 0), conf_rank.get(discogs_res['confidence'], 0))
                    combined_conf = rank_to_conf[best_rank] if oldest_year else 'niedrig'

                    df.at[idx, 'Artist_Vorschlag'] = api.suggest_artist_spelling(c_art) or ''
                    df.at[idx, 'Title_Vorschlag'] = api.suggest_title_spelling(art_sugg, c_tit, local_dur) or ''
                    df.at[idx, 'Jahr_Vorschlag'] = oldest_year
                    df.at[idx, 'Jahr_Konfidenz'] = combined_conf
                    df.at[idx, 'Genre_Vorschlag'] = discogs_res['genre'] or ''
                    df.at[idx, 'Album_Vorschlag'] = discogs_res['album'] or mb_album or ''
                    df.at[idx, 'STYLE_Vorschlag'] = discogs_res['style']
                    df.at[idx, 'DISCOGS_RELEASE_ID_Vorschlag'] = discogs_res['discogs_id']
                    df.at[idx, 'Label_Vorschlag'] = discogs_res['label']
                    df.at[idx, 'Labelcode_Vorschlag'] = discogs_res['label_code']
                    df.at[idx, 'ISRC_Vorschlag'] = isrc or ''
                    df.at[idx, 'Sprache_Vorschlag'] = mb_lang or ''
                    
                    current_typ = str(row.get('Typ', '')).strip()
                    if not current_typ:
                        raw_type = str(row.get('ItemType', '')).strip()
                        df.at[idx, 'Typ_Vorschlag'] = utils.ITEM_TYPE_MAPPING.get(raw_type, '')
                    else:
                        df.at[idx, 'Typ_Vorschlag'] = ''
                        
                    df.at[idx, 'VORSCHLAG_STATUS'] = 'FERTIG'

                    conf_color = "green" if combined_conf == "hoch" else ("yellow" if combined_conf == "mittel" else "red")
                    locale_conf = utils.t(f"conf_{combined_conf}")
                    progress.console.print(utils.t('fetch_track_info', id=row.get('ID'), art=art_sugg, tit=tit_sugg, jahr=oldest_year or '?', c_color=conf_color, conf=locale_conf))
                
                except Exception as e:
                    utils.log_change("ERROR", f"Track ID {row.get('ID')} gecrasht: {str(e)}")
                    progress.console.print(f"[bold red]Fehler bei Track ID {row.get('ID')}: {e} -> Wird übersprungen![/bold red]")

                processed_counter += 1
                progress.update(task, advance=1)
                if processed_counter % 20 == 0: utils.save_safe_csv(df, fetch_csv)

                if not no_breaks and processed_counter % 50 == 0 and processed_counter < offen:
                    utils.save_safe_csv(df, fetch_csv)
                    progress.stop()
                    console.print(utils.t('fetch_chunk_pause', count=processed_counter))
                    ans = console.input(utils.t('fetch_chunk_prompt')).strip().lower()
                    if ans == 'r':
                        break
                    progress.start()

        except KeyboardInterrupt:
            console.print(utils.t('fetch_interrupt'))
            utils.save_safe_csv(df, fetch_csv)
            return

    utils.save_safe_csv(df, fetch_csv)
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
                    df.at[idx, 'Label_Vorschlag'] = discogs_res['label'] or ''
                    df.at[idx, 'Labelcode_Vorschlag'] = discogs_res['label_code'] or ''
                    df.at[idx, 'ISRC_Vorschlag'] = isrc or ''
                    df.at[idx, 'STYLE_Vorschlag'] = discogs_res['style'] or ''
                    df.at[idx, 'DISCOGS_RELEASE_ID_Vorschlag'] = discogs_res['discogs_id'] or ''
                    if mb_lang: df.at[idx, 'Sprache_Vorschlag'] = mb_lang

                genre_sugg = utils.clean_nan(df.at[idx, 'Genre_Vorschlag'])
                if genre_sugg:
                    if auto_hoch and konf == 'hoch' and not custom_refetch_needed:
                        df.at[idx, 'Genre'] = genre_sugg
                        console.print(utils.t('rev_genre_auto', sugg=genre_sugg, orig=orig_genre))
                    else:
                        inp = ask_input(utils.t('rev_genre', sugg=genre_sugg, orig=orig_genre))
                        if inp.lower() in ['', 'j', 'ja', 'y', 'yes']: df.at[idx, 'Genre'] = genre_sugg
                        elif inp.lower() == 'o': df.at[idx, 'Genre'] = orig_genre
                        elif inp and inp.lower() not in ['n', 'nein']: df.at[idx, 'Genre'] = inp

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

def phase_apply(db_path, final_csv):
    db.verify_db_compatibility(db_path)
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
    except Exception:
        pass

    df = pd.read_csv(final_csv, dtype=str)
    if 'REVIEW_STATUS' in df.columns:
        df = df[df['REVIEW_STATUS'] == 'JA']

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
            df = df[~df['ID'].astype(str).isin(already_restored_ids)]
        conn.close()
    except Exception:
        pass

    if df.empty:
        console.print(utils.t('apply_no_new'))
    else:
        try:
            updated = db.apply_dataframe_to_mldb(df, db_path)
            console.print(utils.t('apply_success', count=updated, db=db_path))
        except sqlite3.OperationalError as e:
            console.print(utils.t('apply_err_lock', err=str(e)))
            return

    try:
        df_full = pd.read_csv(final_csv, dtype=str)
        if 'REVIEW_STATUS' in df_full.columns:
            df_full.loc[df_full['REVIEW_STATUS'] == 'JA', 'RESTAURIERT'] = 'JA'
            utils.save_safe_csv(df_full, final_csv)
            
        fetch_csv = final_csv.replace('_restauriert.csv', '_vorschlaege.csv')
        if os.path.exists(fetch_csv):
            df_fetch = pd.read_csv(fetch_csv, dtype=str)
            if 'REVIEW_STATUS' in df_fetch.columns:
                df_fetch.loc[df_fetch['REVIEW_STATUS'] == 'JA', 'RESTAURIERT'] = 'JA'
                utils.save_safe_csv(df_fetch, fetch_csv)
    except Exception:
        pass

def phase_maintenance(db_path):
    db.verify_db_compatibility(db_path)
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
        console.print(utils.t('maint_opt0'))
        
        choice = console.input(f"\n[cyan]{utils.t('maint_prompt')}[/cyan]").strip()
        
        if choice == '0':
            break
        elif choice in ['1', '2', '3', '4']:
            do_genres = choice in ['1', '4']
            do_case   = choice in ['2', '4']
            do_tags   = choice == '3'
            
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
                    console.print("[magenta]Lese Dateien und schreibe Tags... (Das kann je nach Archivgröße dauern)[/magenta]")
                    count = db.run_maintenance_file_tagger(db_path)
                    if count > 0: console.print(utils.t('maint_done_tags', count=count))
                    else: console.print(utils.t('maint_no_changes'))
                        
            except sqlite3.OperationalError as e:
                console.print(utils.t('apply_err_lock', err=str(e)))
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

def run_interactive_menu():
    if not utils.load_language():
        select_language()

    clear_screen()
    check_for_updates(interactive=True)
    perform_migration()
    utils.init_credentials()

    mldbpfad = ""
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

        console.print(f"\n  [[cyan]0[/cyan]] {utils.t('menu_opt0')}\n")
        
        console.print(f"[yellow] {utils.t('menu_h1')}[/yellow]")
        console.print(f"  [[green]1[/green]] {utils.t('menu_opt1')}")
        console.print(f"  [[green]2[/green]] {utils.t('menu_opt2')}")
        console.print(f"  [[green]3[/green]] {utils.t('menu_opt3')}\n")
        
        console.print(f"[yellow] {utils.t('menu_h2')}[/yellow]")
        console.print(f"  [[green]4[/green]] {utils.t('menu_opt4')}")
        console.print(f"  [[green]5[/green]] {utils.t('menu_opt5')}\n")
        
        console.print(f"[yellow] {utils.t('menu_h3')}[/yellow]")
        console.print(f"  [[green]6[/green]] {utils.t('menu_opt6')}\n")
        
        console.print(f"[yellow] {utils.t('menu_h4')}[/yellow]")
        console.print(f"  [[green]7[/green]] {utils.t('menu_opt7')}\n")
        
        console.print(f"  [[green]8[/green]] {utils.t('menu_opt8')}")
        console.print(f"  [[green]9[/green]] {utils.t('menu_opt9')}\n")

        wahl = console.input(f"[cyan]{utils.t('menu_prompt')} [/cyan]").strip()

        if wahl == '9':
            break

        elif wahl == '8':
            select_language()
            continue

        elif wahl == '0':
            console.print(f"\n[cyan]{utils.t('menu_path_hint1')}[/cyan]")
            console.print(f"[yellow]{utils.t('menu_path_hint2')}[/yellow]")
            mldbpfad = console.input(f"{utils.t('menu_path_prompt')}").strip().strip('"').strip("'")
            if mldbpfad:
                db_base_name, data_dir = setup_logging(mldbpfad)
                fetch_csv = os.path.join(data_dir, f"{db_base_name}_vorschlaege.csv")
                final_csv = os.path.join(data_dir, f"{db_base_name}_restauriert.csv")
            continue

        if not mldbpfad:
            console.print(f"\n[bold red]{utils.t('menu_err_db')}[/bold red]")
            console.input(f"\n[cyan]{utils.t('menu_continue')}[/cyan]")
            continue

        if wahl == '1':
            phase_fetch(mldbpfad, fetch_csv, full=False, no_breaks=False)
        elif wahl == '2':
            phase_fetch(mldbpfad, fetch_csv, full=False, no_breaks=True)
        elif wahl == '3':
            console.print(f"\n[bold yellow]{utils.t('menu_warn_full')}[/bold yellow]")
            bestaetigung = console.input(f"{utils.t('menu_sure')}").strip().lower()
            if bestaetigung in ['j', 'y', 'ja', 'yes']:
                phase_fetch(mldbpfad, fetch_csv, full=True, no_breaks=True)
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
        args = parser.parse_args()

        utils.save_language(args.lang)
        
        if args.phase == 'check_update':
            check_for_updates()
            return
            
        if not args.db:
            console.print("[red]Fehler: --db Argument fehlt![/red]")
            sys.exit(1)
        
        db.verify_db_compatibility(args.db)
        perform_migration()
        db_base_name, data_dir = setup_logging(args.db)
        utils.init_credentials()

        fetch_csv = os.path.join(data_dir, f"{db_base_name}_vorschlaege.csv")
        final_csv = os.path.join(data_dir, f"{db_base_name}_restauriert.csv")

        if args.phase == 'fetch': phase_fetch(args.db, fetch_csv, full=args.full, no_breaks=args.no_breaks)
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