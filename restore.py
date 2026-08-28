"""
==============================================================================
                         mAirList DB Restorer
==============================================================================
 Author          : Myka Vormeng, with Google Gemini
 Purpose         : Automatic completion & repair of local mAirList databases 
                   (.mldb / SQLite)
 License         : Free use for the mAirList community
==============================================================================
"""

import pandas as pd
import requests
import time
import re
import json
import os
import sys
import csv
import sqlite3
import shutil
import argparse
import base64
import difflib
import statistics
import logging
from datetime import datetime
from collections import Counter

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich import box

# Highlighter deaktivieren, damit Wörter wie 'true' oder Zahlen nicht bunt gefärbt werden
console = Console(highlight=False)

CONFIG_FILE = 'config.json'
APP_VERSION = "0.4.19 Beta"

# ---------------------------------------------------------------------------
# Language Dictionary
# ---------------------------------------------------------------------------
CURRENT_LANG = 'de'

T = {
    'de': {
        'setup_title': "[bold cyan]Ersteinrichtung: API-Zugangsdaten[/bold cyan]\nAngaben werden lokal maskiert in 'config.json' gespeichert.",
        'setup_discogs': "[bold yellow]-- Discogs API --[/bold yellow]",
        'setup_mb': "\n[bold yellow]-- MusicBrainz Contact --[/bold yellow]",
        'setup_email': "  Deine Kontakt-E-Mail: ",
        'setup_email_err': "[red]Ungültige E-Mail-Adresse, bitte erneut eingeben.[/red]",
        'setup_saved': "[green]✓ Zugangsdaten sicher gespeichert in '{config_file}'.[/green]\n",
        'ign_current': "\n[cyan]Aktuelle Ordner-Ausnahmen für diese DB:[/cyan] [yellow]{liste}[/yellow]",
        'ign_reset': "Möchtest du diese Liste neu erstellen? [j/N]: ",
        'ign_none': "Keine",
        'ign_setup_title': "\n[bold cyan]Ordner-Ausnahmen für diese Datenbank konfigurieren[/bold cyan]\nHier kannst du Ordner angeben, die ignoriert werden sollen (z.B. Jingles, News).",
        'ign_prompt': "  [cyan]Drag & Drop Ordner hierher[/cyan] ODER tippe [cyan]virtuellen Ordnernamen[/cyan] (Enter = Fertig): ",
        'ign_added_phys': "  [green]✓ Physikalischer Pfad ignoriert:[/green] {path}",
        'ign_added_virt': "  [green]✓ Virtueller/Teil-Ordner ignoriert:[/green] {name}",
        'ign_saved': "[green]✓ Ausnahmen für diese DB in config.json gespeichert![/green]\n",
        'ign_skip_count': "\n[bold green]✓ SUCCESS: {count} ignorierte Elemente (OAD/Jingles/News) erfolgreich übersprungen![/bold green]",
        'fetch_load_prog': "[cyan]Fortschritt geladen aus '{csv}' ({count} Zeilen).[/cyan]",
        'fetch_sync_del': "[yellow]-> {count} Track(s) wurden in mAirList gelöscht und aus CSV entfernt.[/yellow]",
        'fetch_new_tracks': "[green]-> {count} neue Track(s) aus '{db}' ergänzt.[/green]",
        'fetch_reset': "[yellow]-> {count} Track(s) in mAirList zurückgesetzt – werden neu gefetcht![/yellow]",
        'fetch_first': "[cyan]Erster Lauf: Lese direkt aus SQLite-Kopie '{db}'.[/cyan]",
        'fetch_full': "[bold yellow]Vollständige Neuprüfung angefordert (--full)[/bold yellow]",
        'fetch_start': "[bold green]Starte automatischen Fetch[/bold green]\nOffene Tracks: [bold yellow]{offen}[/bold yellow] von [bold]{total}[/bold] Gesamt",
        'fetch_done_already': "[bold green]✓ Alle Tracks sind bereits auf dem neuesten Stand![/bold green]",
        'fetch_progress': "[bold magenta]Fetching Metadaten...",
        'fetch_track_info': "  [dim]ID {id}:[/dim] [bold]{art} - {tit}[/bold] (Jahr: [bold cyan]{jahr}[/bold cyan], Konfidenz: [{c_color}]{conf}[/{c_color}])",
        'fetch_interrupt': "\n[bold yellow]Abruf unterbrochen. Fortschritt sicher gespeichert.[/bold yellow]",
        'fetch_success': "\n[bold green]✓ Fetch erfolgreich abgeschlossen![/bold green] Nächster Schritt: [bold cyan]py restore.py review --db \"{db}\"[/bold cyan]",
        'err_file_not_found': "[bold red][Fehler][/bold red] '{file}' nicht gefunden.",
        'err_need_fetch': " Erst 'fetch' ausführen.",
        'rev_mode': "[bold cyan]Review Modus[/bold cyan]\nOffene Prüfungen: [bold yellow]{todo}[/bold yellow]{auto}\n[dim]Tipp: Tippe '<' oder 'b' und Enter, um einen Track zurückzuspringen![/dim]",
        'rev_auto_active': "\n[green]--auto-hoch aktiv[/green]",
        'rev_row': "[bold white on blue] Zeile {row} (ID: {id}) [/bold white on blue] [bold]{art} - {tit}[/bold]",
        'rev_artist': "  [cyan]Artist[/cyan] -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim]\\[j/Enter/Text][/dim]: ",
        'rev_title': "  [cyan]Title[/cyan]  -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim]\\[j/Enter/Text][/dim]: ",
        'rev_refetch': "  [magenta]⚡ Freitext erkannt! Live Re-Fetch für '{art} - {tit}'...[/magenta]",
        'rev_year_auto': "  [cyan]Jahr[/cyan]   -> [bold green]{sugg}[/bold green] [dim](auto, Konfidenz hoch)[/dim]",
        'rev_year': "  [cyan]Jahr[/cyan]   -> Vorschlag: '[bold green]{sugg}[/bold green]' ({badge}) [dim]\\[j/Enter/Jahr][/dim]: ",
        'rev_genre_auto': "  [cyan]Genre[/cyan]  -> [bold green]{sugg}[/bold green] [dim](auto, Konfidenz hoch)[/dim]",
        'rev_genre': "  [cyan]Genre[/cyan]  -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim]\\[j/Enter/Genre][/dim]: ",
        'rev_album': "  [cyan]Album[/cyan]  -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim]\\[j/Enter/Text][/dim]: ",
        'rev_label': "  [cyan]Label[/cyan]  -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim]\\[j/Enter/Text][/dim]: ",
        'rev_lang':  "  [cyan]Sprache[/cyan]-> Vorschlag: '[bold green]{sugg}[/bold green]' [dim]\\[{hint}][/dim]: ",
        'no_sugg': "- (Kein Vorschlag) -",
        'rev_interim': "[dim]  (Zwischenstand gespeichert)[/dim]",
        'rev_interrupt': "\n\n[bold yellow]Review unterbrochen. Bisherige Entscheidungen sind gespeichert.[/bold yellow]",
        'rev_success': "\n[bold green]✓ Review abgeschlossen![/bold green] Finales Ergebnis in [bold cyan]'{csv}'[/bold cyan].",
        'err_need_fetch_rev': " Erst 'fetch' und 'review' durchführen.",
        'apply_warn': "[bold red]ACHTUNG: Schreibvorgang in .mldb-Datei[/bold red]\nNiemals auf eine aktiv von mAirList geöffnete Datei anwenden!",
        'apply_locked': "[bold red]Datenbank ist aktuell gesperrt![/bold red]\nVermutlich hat mAirList (oder ein anderes Programm) diese Datei\ngerade geöffnet. Schließe das Programm bzw. wähle eine echte\nKopie der Datei aus und versuche es erneut.",
        'apply_confirm': "Ist dies definitiv eine KOPIE? Zum Fortfahren '[bold green]JA[/bold green]' eintippen: ",
        'apply_confirm_word': "JA",
        'apply_abort': "[yellow]Abgebrochen.[/yellow]",
        'apply_backup': "[green]✓ Backup angelegt: {path}[/green]",
        'apply_err_lock': "\n[bold red][Fehler] Datenbank gelockt / Zugriff verweigert:[/bold red] {err}",
        'apply_success': "\n[bold green]✓ Fertig! {count} Zeile(n) in '{db}' erfolgreich aktualisiert.[/bold green]",
        'conf_hoch': "hoch", 'conf_mittel': "mittel", 'conf_niedrig': "niedrig"
    },
    'en': {
        'setup_title': "[bold cyan]Initial Setup: API Credentials[/bold cyan]\nDetails will be safely masked locally in 'config.json'.",
        'setup_discogs': "[bold yellow]-- Discogs API --[/bold yellow]",
        'setup_mb': "\n[bold yellow]-- MusicBrainz Contact --[/bold yellow]",
        'setup_email': "  Your Contact Email: ",
        'setup_email_err': "[red]Invalid email address, please try again.[/red]",
        'setup_saved': "[green]✓ Credentials securely saved in '{config_file}'.[/green]\n",
        'ign_current': "\n[cyan]Current folder exceptions for this DB:[/cyan] [yellow]{liste}[/yellow]",
        'ign_reset': "Do you want to recreate this list? [y/N]: ",
        'ign_none': "None",
        'ign_setup_title': "\n[bold cyan]Configure folder exceptions for this database[/bold cyan]\nSpecify folders to be skipped during fetch (e.g., Jingles, News).",
        'ign_prompt': "  [cyan]Drag & Drop folder here[/cyan] OR type [cyan]virtual folder name[/cyan] (Enter = Done): ",
        'ign_added_phys': "  [green]✓ Physical path ignored:[/green] {path}",
        'ign_added_virt': "  [green]✓ Virtual/Partial folder ignored:[/green] {name}",
        'ign_saved': "[green]✓ Exceptions for this DB saved to config.json![/green]\n",
        'ign_skip_count': "\n[bold green]✓ SUCCESS: Skipped {count} ignored elements (OAD/Jingles/News etc.)![/bold green]",
        'fetch_load_prog': "[cyan]Progress loaded from '{csv}' ({count} rows).[/cyan]",
        'fetch_sync_del': "[yellow]-> {count} track(s) were deleted in mAirList and removed from CSV.[/yellow]",
        'fetch_new_tracks': "[green]-> Added {count} new track(s) from '{db}'.[/green]",
        'fetch_reset': "[yellow]-> {count} track(s) reset in mAirList – will be re-fetched![/yellow]",
        'fetch_first': "[cyan]First run: Reading directly from SQLite copy '{db}'.[/cyan]",
        'fetch_full': "[bold yellow]Full re-check requested (--full)[/bold yellow]",
        'fetch_start': "[bold green]Starting automatic fetch[/bold green]\nPending tracks: [bold yellow]{offen}[/bold yellow] of [bold]{total}[/bold] total",
        'fetch_done_already': "[bold green]✓ All tracks are already up to date![/bold green]",
        'fetch_progress': "[bold magenta]Fetching metadata...",
        'fetch_track_info': "  [dim]ID {id}:[/dim] [bold]{art} - {tit}[/bold] (Year: [bold cyan]{jahr}[/bold cyan], Confidence: [{c_color}]{conf}[/{c_color}])",
        'fetch_interrupt': "\n[bold yellow]Fetch interrupted. Progress safely saved.[/bold yellow]",
        'fetch_success': "\n[bold green]✓ Fetch completed successfully![/bold green] Next step: [bold cyan]py restore.py review --db \"{db}\"[/bold cyan]",
        'err_file_not_found': "[bold red][Error][/bold red] '{file}' not found.",
        'err_need_fetch': " Run 'fetch' first.",
        'rev_mode': "[bold cyan]Review Mode[/bold cyan]\nPending reviews: [bold yellow]{todo}[/bold yellow]{auto}\n[dim]Tip: Type '<' or 'b' and Enter to go back one track![/dim]",
        'rev_auto_active': "\n[green]--auto-hoch active[/green]",
        'rev_row': "[bold white on blue] Row {row} (ID: {id}) [/bold white on blue] [bold]{art} - {tit}[/bold]",
        'rev_artist': "  [cyan]Artist[/cyan] -> Suggestion: '[bold green]{sugg}[/bold green]' [dim]\\[y/Enter/Text][/dim]: ",
        'rev_title': "  [cyan]Title[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim]\\[y/Enter/Text][/dim]: ",
        'rev_refetch': "  [magenta]⚡ Custom text detected! Live re-fetch for '{art} - {tit}'...[/magenta]",
        'rev_year_auto': "  [cyan]Year[/cyan]   -> [bold green]{sugg}[/bold green] [dim](auto, high confidence)[/dim]",
        'rev_year': "  [cyan]Year[/cyan]   -> Suggestion: '[bold green]{sugg}[/bold green]' ({badge}) [dim]\\[y/Enter/Year][/dim]: ",
        'rev_genre_auto': "  [cyan]Genre[/cyan]  -> [bold green]{sugg}[/bold green] [dim](auto, high confidence)[/dim]",
        'rev_genre': "  [cyan]Genre[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim]\\[y/Enter/Genre][/dim]: ",
        'rev_album': "  [cyan]Album[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim]\\[y/Enter/Text][/dim]: ",
        'rev_label': "  [cyan]Label[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim]\\[y/Enter/Text][/dim]: ",
        'rev_lang':  "  [cyan]Lang.[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim]\\[{hint}][/dim]: ",
        'no_sugg': "- (No suggestion) -",
        'rev_interim': "[dim]  (Intermediate progress saved)[/dim]",
        'rev_interrupt': "\n\n[bold yellow]Review interrupted. Previous decisions are saved.[/bold yellow]",
        'rev_success': "\n[bold green]✓ Review completed![/bold green] Final result in [bold cyan]'{csv}'[/bold cyan].",
        'err_need_fetch_rev': " Run 'fetch' and 'review' first.",
        'apply_warn': "[bold red]WARNING: Write operation to .mldb file[/bold red]\nNever apply to a file currently open in mAirList!",
        'apply_locked': "[bold red]Database is currently locked![/bold red]\nmAirList (or another program) likely has this file\nopen right now. Close the program or select a true\ncopy of the file and try again.",
        'apply_confirm': "Is this definitely a COPY? Type '[bold green]YES[/bold green]' to continue: ",
        'apply_confirm_word': "YES",
        'apply_abort': "[yellow]Aborted.[/yellow]",
        'apply_backup': "[green]✓ Backup created: {path}[/green]",
        'apply_err_lock': "\n[bold red][Error] Database locked / Access denied:[/bold red] {err}",
        'apply_success': "\n[bold green]✓ Done! {count} row(s) in '{db}' successfully updated.[/bold green]",
        'conf_hoch': "high", 'conf_mittel': "medium", 'conf_niedrig': "low"
    }
}

def t(key, **kwargs):
    return T[CURRENT_LANG][key].format(**kwargs)

# ---------------------------------------------------------------------------
# Logging Helper
# ---------------------------------------------------------------------------
def log_change(action, details):
    logging.info(f"{action.upper()}: {details}")

def clear_input_buffer():
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()
    except Exception:
        pass

# Felder für item_attributes
MLDB_ATTRIBUTE_FIELDS = [
    'Jahr', 'Genre', 'Album', 'STYLE', 'DISCOGS_RELEASE_ID',
    'Label', 'Labelcode', 'ISRC', 'Sprache', 'RESTAURIERT'
]

MB_MIN_INTERVAL = 1.05
DISCOGS_MIN_INTERVAL = 1.0
CURRENT_YEAR = datetime.now().year

DISCOGS_KEY = ""
DISCOGS_SECRET = ""
MB_CONTACT = ""
HEADERS = {}
CUSTOM_LANGS = []

# ---------------------------------------------------------------------------
# Security & Helpers
# ---------------------------------------------------------------------------
def encode_b64(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8') if text else ""

def decode_b64(text):
    try:
        return base64.b64decode(text.encode('utf-8')).decode('utf-8') if text else ""
    except Exception:
        return text

def _is_valid_email(text):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', text.strip()))

def string_similarity(a, b):
    if not a or not b: return 0.0
    return difflib.SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def filter_valid_years(years_list):
    valid = sorted([int(y) for y in years_list if str(y).isdigit() and 1900 <= int(y) <= CURRENT_YEAR])
    if not valid: return ""
    counts = Counter(valid)
    unique_years = sorted(list(set(valid)))
    
    while len(unique_years) > 1:
        if unique_years[1] - unique_years[0] > 8 and counts[unique_years[0]] < 2:
            unique_years.pop(0)
        else: break
    return str(unique_years[0])

def clean_nan(val):
    if pd.isna(val) or str(val).strip().lower() == 'nan':
        return ""
    return str(val).strip()

def init_credentials():
    global DISCOGS_KEY, DISCOGS_SECRET, MB_CONTACT, HEADERS, CUSTOM_LANGS
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception: config = {}

    DISCOGS_KEY = decode_b64(config.get('DISCOGS_KEY', '').strip())
    DISCOGS_SECRET = decode_b64(config.get('DISCOGS_SECRET', '').strip())
    MB_CONTACT = decode_b64(config.get('MB_CONTACT', '').strip())
    CUSTOM_LANGS = config.get('CUSTOM_LANGS', [])

    if DISCOGS_KEY and DISCOGS_SECRET and MB_CONTACT:
        HEADERS = {'User-Agent': f'mAirListDBRestorer/{APP_VERSION} ( {MB_CONTACT} )'}
        return

    console.print(Panel(t('setup_title'), box=box.ROUNDED))

    if not DISCOGS_KEY or not DISCOGS_SECRET:
        console.print(t('setup_discogs'))
        DISCOGS_KEY = input("  Discogs KEY: ").strip()
        DISCOGS_SECRET = input("  Discogs SECRET: ").strip()

    if not MB_CONTACT:
        console.print(t('setup_mb'))
        while True:
            MB_CONTACT = input(t('setup_email')).strip()
            if _is_valid_email(MB_CONTACT): break
            console.print(t('setup_email_err'))

    config_data = {
        'DISCOGS_KEY': encode_b64(DISCOGS_KEY),
        'DISCOGS_SECRET': encode_b64(DISCOGS_SECRET),
        'MB_CONTACT': encode_b64(MB_CONTACT),
        'DB_IGNORES': config.get('DB_IGNORES', {}),
        'CUSTOM_LANGS': CUSTOM_LANGS
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)

    console.print(t('setup_saved', config_file=CONFIG_FILE))
    HEADERS = {'User-Agent': f'mAirListDBRestorer/{APP_VERSION} ( {MB_CONTACT} )'}

def add_custom_lang(lang):
    if lang not in CUSTOM_LANGS:
        CUSTOM_LANGS.append(lang)
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception: pass
        config['CUSTOM_LANGS'] = CUSTOM_LANGS
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)

def setup_ignored_folders(db_path):
    db_abs = os.path.abspath(db_path)
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception: pass

    db_ignores_dict = config.get('DB_IGNORES', {})

    if db_abs in db_ignores_dict:
        current_ignores = db_ignores_dict[db_abs]
        disp_list = ", ".join(current_ignores) if current_ignores else t('ign_none')
        console.print(t('ign_current', liste=disp_list))
        clear_input_buffer()
        ans = console.input(f"[yellow]{t('ign_reset')}[/yellow]").strip().lower()
        if ans not in ['j', 'ja', 'y', 'yes']:
            return current_ignores

    console.print(t('ign_setup_title'))
    ignored = []
    while True:
        clear_input_buffer()
        inp = console.input(t('ign_prompt')).strip().strip('"').strip("'")
        if not inp:
            break
        ignored.append(inp)
        if '\\' in inp or '/' in inp:
            console.print(t('ign_added_phys', path=inp))
        else:
            console.print(t('ign_added_virt', name=inp))

    db_ignores_dict[db_abs] = ignored
    config['DB_IGNORES'] = db_ignores_dict

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

    console.print(t('ign_saved'))
    return ignored

# ---------------------------------------------------------------------------
# Rate-Limiter & HTTP
# ---------------------------------------------------------------------------
_last_mb_request = 0.0
_last_discogs_request = 0.0

def _wait(min_interval, last_time):
    elapsed = time.time() - last_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    return time.time()

def mb_get(url, params, timeout=5):
    global _last_mb_request
    _last_mb_request = _wait(MB_MIN_INTERVAL, _last_mb_request)
    res = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
    _last_mb_request = time.time()
    return res

def discogs_get(url, params, timeout=5):
    global _last_discogs_request
    _last_discogs_request = _wait(DISCOGS_MIN_INTERVAL, _last_discogs_request)
    res = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
    _last_discogs_request = time.time()
    return res

# ---------------------------------------------------------------------------
# Genre-Normalisierung & Cleaning
# ---------------------------------------------------------------------------
ALLOWED_GENRES = [
    "Big Room", "Blues", "Classic Rock", "Country", "Dance", "Dancehall", "Dance-Pop",
    "Deep House", "Deutsch-Hiphop", "Deutsch-Pop", "Deutsch-Rock", "Dubstep", "EDM",
    "Eurodance", "Funk", "Future House", "Gothic Rock", "Hard Rock", "Hardstyle",
    "Hiphop", "House", "Indie Rock", "Industrial", "Jazz", "Metal", "Oldies",
    "Pop", "Pop-Rock", "Progressive House", "Psytrance", "Punk Rock", "R and B",
    "Rap", "Reggae", "Rock", "Rock n Roll", "Schlager", "Slap House", "Soul",
    "Synth-Pop", "Tech House", "Techno", "Trance", "Trap", "Tropical House"
]

GENRE_SYNONYMS = {
    "euro house": "Eurodance", "synth-pop": "Synth-Pop", "synthpop": "Synth-Pop",
    "hip hop": "Hiphop", "hip-hop": "Hiphop", "r&b": "R and B", "r&b / soul": "R and B",
    "rock & roll": "Rock n Roll", "rock 'n' roll": "Rock n Roll", "pop rock": "Pop-Rock",
    "indie": "Indie Rock", "edm": "EDM", "electronic": "Dance"
}

COMPILATION_KEYWORDS = [
    'compilation', 'best of', 'greatest hits', 'essential', 'collection',
    'various', 'remix', 'live', 'anthology', 'singles', 'ultimate', 'hit mix', 'bravo',
    'soundtrack', 'o.s.t.', 'ost', 'the dome', 'now that'
]

LABEL_CODE_CACHE = {}

# VIP Dictionary für Härtefälle wie Duran Duran Duran
ARTIST_FIXES = {
    "ac, dc": "AC/DC", "ac dc": "AC/DC", "ac-dc": "AC/DC", "acdc": "AC/DC",
    "a-ha": "a-ha", "a ha": "a-ha", "aha": "a-ha",
    "b-52s": "The B-52's", "b 52s": "The B-52's", "b-52's": "The B-52's", "the b-52s": "The B-52's",
    "duran duran": "Duran Duran", "duran duran duran": "Duran Duran"
}

def contains_non_latin(text):
    if not text: return False
    return bool(re.search(r'[\u0400-\u04FF\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AF\u0600-\u06FF]', text))

def capitalize_smart(text):
    if text.lower() in ARTIST_FIXES: return ARTIST_FIXES[text.lower()]
    words = text.split(' ')
    cap_words = []
    for w in words:
        wl = w.lower()
        if wl in ['feat.', 'ft.', 'featuring']: cap_words.append('feat.')
        elif wl in ['and', '&']: cap_words.append('&')
        elif w == '': cap_words.append(w)
        elif w == w.lower() and not any(ch.isdigit() for ch in w): cap_words.append(w[0].upper() + w[1:])
        else: cap_words.append(w)
    return " ".join(cap_words)

def clean_artist_base(artist_raw):
    if pd.isna(artist_raw) or not str(artist_raw).strip(): return ""
    text = str(artist_raw).strip()
    if text.lower() in ARTIST_FIXES: return ARTIST_FIXES[text.lower()]
    text = re.sub(r'\b(featuring|feat\.|feat|ft\.|ft)\b', 'feat.', text, flags=re.IGNORECASE)
    text = re.sub(r'feat\.\.', 'feat.', text)
    return capitalize_smart(re.sub(r'\s+', ' ', text))

def clean_title_base(title_raw):
    if pd.isna(title_raw) or not str(title_raw).strip(): return ""
    text = str(title_raw).strip()
    text = re.sub(r'\b(featuring|feat\.|feat|ft\.|ft)\b', 'feat.', text, flags=re.IGNORECASE)
    text = re.sub(r'feat\.\.', 'feat.', text)
    return capitalize_smart(re.sub(r'\s+', ' ', text))

def get_pure_search_title(title):
    return re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip()

def is_valid_album(album_name):
    if not album_name or contains_non_latin(album_name): return False
    return not any(kw in album_name.lower() for kw in COMPILATION_KEYWORDS)

def extract_label_code_from_string(text):
    if not text or pd.isna(text): return ""
    match = re.search(r'LC[- ]?(\d{4,5})', str(text), flags=re.IGNORECASE)
    return f"LC{match.group(1).zfill(5)}" if match else ""

def fetch_label_code_from_musicbrainz(label_name):
    if not label_name: return ""
    clean_label = label_name.split('/')[0].strip()
    if clean_label in LABEL_CODE_CACHE: return LABEL_CODE_CACHE[clean_label]
    try:
        res = mb_get("https://musicbrainz.org/ws/2/label/", {'query': f'label:"{clean_label}"', 'fmt': 'json', 'limit': 3})
        if res.status_code == 200:
            for l in res.json().get('labels', []):
                code = l.get('label-code')
                if code:
                    flc = f"LC{str(code).zfill(5)}"
                    LABEL_CODE_CACHE[clean_label] = flc
                    return flc
    except Exception: pass
    return ""

def fetch_label_code_from_discogs_release(release_id):
    if not release_id: return ""
    try:
        res = discogs_get(f"https://api.discogs.com/releases/{release_id}", {'key': DISCOGS_KEY, 'secret': DISCOGS_SECRET})
        if res.status_code == 200:
            for l in res.json().get('labels', []):
                lc = extract_label_code_from_string(l.get('catno', '')) or extract_label_code_from_string(l.get('name', ''))
                if lc: return lc
    except Exception: pass
    return ""

def suggest_artist_spelling(artist):
    if not artist: return None
    main_artist = artist.split('feat.')[0].strip() if 'feat.' in artist else artist
    
    if main_artist.lower() in ARTIST_FIXES:
        res_art = ARTIST_FIXES[main_artist.lower()]
        if 'feat.' in artist: return f"{res_art} feat.{artist.split('feat.')[1]}"
        return res_art
        
    try:
        res = mb_get("https://musicbrainz.org/ws/2/artist/", {'query': main_artist, 'fmt': 'json', 'limit': 5})
        if res.status_code == 200:
            for top_match in res.json().get('artists', []):
                score = int(top_match.get('score', 0))
                official_name = top_match.get('name', '')
                if score >= 90 and official_name and string_similarity(main_artist, official_name) >= 0.7:
                    if official_name.lower() != main_artist.lower():
                        if 'feat.' in artist: return f"{official_name} feat.{artist.split('feat.')[1]}"
                        return official_name
    except Exception: pass
    return None

def suggest_title_spelling(artist, title):
    if not title or not artist: return None
    try:
        search_title = get_pure_search_title(title)
        res = mb_get("https://musicbrainz.org/ws/2/recording/",
                      {'query': f'artist:"{artist}" AND recording:"{search_title}"', 'fmt': 'json', 'limit': 3})
        if res.status_code == 200:
            recordings = res.json().get('recordings', [])
            if recordings:
                official_title = recordings[0].get('title', '')
                if official_title and official_title.lower() != title.lower():
                    return official_title
    except Exception: pass
    return None

def fetch_musicbrainz_details(artist, title):
    years, isrc, orig_album, fallback_album = [], None, None, None
    best_score = 0
    try:
        res = mb_get("https://musicbrainz.org/ws/2/recording/",
                      {'query': f'artist:"{artist}" AND recording:"{get_pure_search_title(title)}"',
                       'fmt': 'json', 'limit': 10, 'inc': 'isrcs+releases'})
        if res.status_code == 200:
            recordings = res.json().get('recordings', [])
            if recordings: best_score = int(recordings[0].get('score', 0))
            relevant = [r for r in recordings if int(r.get('score', 0)) >= max(best_score - 10, 50)]
            for rec in relevant:
                if not isrc and rec.get('isrcs'): isrc = rec.get('isrcs')[0]
                if rec.get('first-release-date', '')[:4]: years.append(rec.get('first-release-date')[:4])
                for rel in sorted(rec.get('releases', []), key=lambda x: x.get('date', '9999') if x.get('date') else '9999'):
                    if rel.get('date', '')[:4]: years.append(rel.get('date')[:4])
                    rel_title = rel.get('title', '')
                    if rel_title and not contains_non_latin(rel_title):
                        if not fallback_album: fallback_album = rel_title
                        if not orig_album and is_valid_album(rel_title): orig_album = rel_title
    except Exception: pass

    confidence = "hoch" if best_score >= 90 else ("mittel" if best_score >= 70 else "niedrig")
    year = filter_valid_years(years)
    return year, confidence, isrc, (orig_album or fallback_album or "")

def map_to_allowed_genre(discogs_genres, discogs_styles):
    candidates = (discogs_styles or []) + (discogs_genres or [])
    for item in candidates:
        i_low = item.strip().lower()
        for allowed in ALLOWED_GENRES:
            if allowed.lower() == i_low: return allowed
        if i_low in GENRE_SYNONYMS and GENRE_SYNONYMS[i_low] in ALLOWED_GENRES: return GENRE_SYNONYMS[i_low]
    for item in candidates:
        for allowed in ALLOWED_GENRES:
            if allowed.lower() in item.lower(): return allowed
    return None

def fetch_discogs_details(artist, title):
    years, mapped_genre, discogs_id, styles_list = [], None, "", []
    label, label_code, orig_album, fallback_album = "", "", "", ""
    confidence = "niedrig"
    try:
        pure_title = get_pure_search_title(title)
        res = discogs_get("https://api.discogs.com/database/search",
                           {'artist': artist, 'track': pure_title, 'key': DISCOGS_KEY, 'secret': DISCOGS_SECRET, 'per_page': 15}, timeout=8)
        results = res.json().get('results', []) if res.status_code == 200 else []

        if not results:
            res_fb = discogs_get("https://api.discogs.com/database/search",
                                 {'q': f"{artist} {pure_title}", 'key': DISCOGS_KEY, 'secret': DISCOGS_SECRET, 'per_page': 15}, timeout=8)
            results = res_fb.json().get('results', []) if res_fb.status_code == 200 else []

        if results:
            search_list = sorted([r for r in results if str(r.get('year', '')).isdigit()], key=lambda x: int(x.get('year'))) or results
            for r in search_list:
                if str(r.get('year', '')).isdigit() and int(r.get('year')) > 1900:
                    years.append(str(r.get('year')))
                rel_title = r.get('title', '').split(' - ', 1)[1] if ' - ' in r.get('title', '') else r.get('title', '')
                if rel_title and not contains_non_latin(rel_title):
                    if not fallback_album: fallback_album = rel_title
                    if not orig_album and is_valid_album(rel_title): orig_album = rel_title
            
            best = search_list[0]
            discogs_id = str(best.get('id', ''))
            styles_list = best.get('style', [])
            mapped_genre = map_to_allowed_genre(best.get('genre', []), styles_list)
            labels = best.get('label', [])
            label = labels[0] if labels else ""
            label_code = extract_label_code_from_string(label) or extract_label_code_from_string(best.get('catno', ''))
            
            if not label_code and label: label_code = fetch_label_code_from_musicbrainz(label)
            if not label_code and discogs_id: label_code = fetch_label_code_from_discogs_release(discogs_id)
            
            best_title = best.get('title', '').lower()
            sim_score = string_similarity(pure_title, best_title)
            if pure_title.lower() in best_title or sim_score >= 0.8:
                confidence = "hoch"
            elif results and sim_score >= 0.5:
                confidence = "mittel"
    except Exception: pass
    return {
        'years': years, 'genre': mapped_genre, 'discogs_id': discogs_id,
        'style': ", ".join(styles_list) if styles_list else "", 'label': label,
        'label_code': label_code, 'album': orig_album or fallback_album or "",
        'confidence': confidence,
    }

def save_safe_csv(df, filepath):
    if 'LYRICS' in df.columns:
        df['LYRICS'] = df['LYRICS'].fillna('').astype(str)
        df['LYRICS'] = df['LYRICS'].str.replace(r'[\r\n]+', ' ', regex=True)
        df['LYRICS'] = df['LYRICS'].str.replace(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', regex=True)
    df.to_csv(filepath, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)

PROPOSAL_COLUMNS = [
    'Artist_Vorschlag', 'Title_Vorschlag', 'Jahr_Vorschlag', 'Jahr_Konfidenz',
    'Genre_Vorschlag', 'Album_Vorschlag', 'STYLE_Vorschlag', 'DISCOGS_RELEASE_ID_Vorschlag',
    'Label_Vorschlag', 'Labelcode_Vorschlag', 'ISRC_Vorschlag', 'Sprache_Vorschlag', 'VORSCHLAG_STATUS',
]

# ---------------------------------------------------------------------------
# MLDB SQLite Logic
# ---------------------------------------------------------------------------
def load_dataframe_from_mldb(db_path, ignored_folders=None):
    if not os.path.exists(db_path): raise FileNotFoundError(t('err_file_not_found', file=db_path))
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
        console.print(t('ign_skip_count', count=skipped_count))

    if not attrs.empty:
        attrs['ID'] = attrs['ID'].astype(str)
        pivot = attrs.pivot_table(index='ID', columns='name', values='value', aggfunc='first').reset_index()
        df = items.merge(pivot, on='ID', how='left')
    else:
        df = items.copy()
        
    for col in MLDB_ATTRIBUTE_FIELDS:
        if col not in df.columns: df[col] = ''
    return df

def is_db_locked(db_path, timeout=1.0):
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        conn.execute("BEGIN IMMEDIATE")
        conn.rollback()
        conn.close()
        return False
    except sqlite3.OperationalError: return True
    except Exception: return False

def apply_dataframe_to_mldb(df, db_path, mark_restauriert=True):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    updated = 0
    try:
        for _, row in df.iterrows():
            item_id = row.get('ID')
            if pd.isna(item_id) or not str(item_id).strip(): continue
            item_id = int(item_id)
            
            cur.execute("SELECT 1 FROM items WHERE idx = ?", (item_id,))
            if not cur.fetchone(): continue 
            
            title, artist = row.get('Title', ''), row.get('Artist', '')
            if pd.notna(title) or pd.notna(artist):
                cur.execute("UPDATE items SET title = COALESCE(?, title), artist = COALESCE(?, artist) WHERE idx = ?",
                            (title if pd.notna(title) and str(title).strip() else None,
                             artist if pd.notna(artist) and str(artist).strip() else None, item_id))
            for field in MLDB_ATTRIBUTE_FIELDS:
                value = row.get(field, '')
                if pd.notna(value) and str(value).strip():
                    cur.execute("INSERT OR REPLACE INTO item_attributes (item, name, value) VALUES (?, ?, ?)",
                                (item_id, field, str(value).strip()))
            if mark_restauriert:
                cur.execute("INSERT OR REPLACE INTO item_attributes (item, name, value) VALUES (?, 'RESTAURIERT', 'JA')", (item_id,))
            
            log_change("APPLY", f"ID {item_id}: {artist} - {title}")
            updated += 1
        conn.commit()
    finally:
        conn.close()
    return updated

# ---------------------------------------------------------------------------
# PHASE 1: fetch
# ---------------------------------------------------------------------------
def phase_fetch(db_path, fetch_csv, full=False):
    if is_db_locked(db_path):
        console.print(Panel(t('apply_locked'), box=box.HEAVY, style="red"))
        sys.exit(1)

    ignored_folders = setup_ignored_folders(db_path)
    input_df = load_dataframe_from_mldb(db_path, ignored_folders)
    
    if os.path.exists(fetch_csv):
        df = pd.read_csv(fetch_csv, dtype=str)
        console.print(t('fetch_load_prog', csv=fetch_csv, count=len(df)))
        
        if 'ID' in df.columns and 'ID' in input_df.columns:
            db_ids = set(input_df['ID'].dropna().astype(str))
            csv_ids = set(df['ID'].dropna().astype(str))
            deleted_ids = csv_ids - db_ids
            if deleted_ids:
                console.print(t('fetch_sync_del', count=len(deleted_ids)))
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
            console.print(t('fetch_new_tracks', count=len(new_rows), db=db_path))
            df = pd.concat([df, new_rows], ignore_index=True, sort=False)
            
        db_restauriert = input_df.set_index('ID')['RESTAURIERT'].to_dict()
        db_artists = input_df.set_index('ID')['Artist'].to_dict()
        db_titles = input_df.set_index('ID')['Title'].to_dict()
        
        reset_count = 0
        for idx, row in df.iterrows():
            item_id = str(row.get('ID'))
            if item_id in db_restauriert:
                db_status = str(db_restauriert[item_id]).strip().upper()
                csv_review = str(row.get('REVIEW_STATUS', '')).strip().upper()
                if db_status != 'JA' and csv_review == 'JA':
                    df.at[idx, 'VORSCHLAG_STATUS'] = ''
                    df.at[idx, 'REVIEW_STATUS'] = ''
                    df.at[idx, 'Artist'] = db_artists.get(item_id, row.get('Artist'))
                    df.at[idx, 'Title'] = db_titles.get(item_id, row.get('Title'))
                    reset_count += 1
                    
        if reset_count > 0: console.print(t('fetch_reset', count=reset_count))

    else:
        console.print(t('fetch_first', db=db_path))
        df = input_df.copy()

    for col in PROPOSAL_COLUMNS + MLDB_ATTRIBUTE_FIELDS:
        if col not in df.columns: df[col] = ''

    if 'RESTAURIERT' in df.columns:
        already_done = df['RESTAURIERT'].astype(str).str.upper() == 'JA'
        df.loc[already_done & (df['VORSCHLAG_STATUS'] != 'FERTIG'), 'VORSCHLAG_STATUS'] = 'FERTIG'

    if full:
        console.print(t('fetch_full'))
        df['VORSCHLAG_STATUS'] = ''
        if 'REVIEW_STATUS' in df.columns: df['REVIEW_STATUS'] = ''

    todo_mask = (df['VORSCHLAG_STATUS'] != 'FERTIG')
    offen = todo_mask.sum()
    total = len(df)
    
    console.print(Panel(t('fetch_start', offen=offen, total=total), box=box.ROUNDED))
    log_change("FETCH_START", f"Pending: {offen}, Total: {total}")

    if offen == 0:
        console.print(t('fetch_done_already'))
        return

    processed_counter = 0
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bold green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TextColumn("•"),
        TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"), TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task(t('fetch_progress'), total=offen)

        try:
            for idx, row in df.iterrows():
                if str(row.get('VORSCHLAG_STATUS', '')).strip().upper() == 'FERTIG': continue

                try:
                    raw_artist, raw_title = row.get('Artist', ''), row.get('Title', '')
                    c_art, c_tit = clean_artist_base(raw_artist), clean_title_base(raw_title)

                    art_sugg = suggest_artist_spelling(c_art) or c_art
                    tit_sugg = suggest_title_spelling(art_sugg, c_tit) or c_tit

                    mb_year, mb_conf, isrc, mb_album = fetch_musicbrainz_details(art_sugg, tit_sugg)
                    discogs_res = fetch_discogs_details(art_sugg, tit_sugg)

                    all_years = [mb_year] if mb_year else []
                    all_years += [y for y in discogs_res['years']]
                    oldest_year = filter_valid_years(all_years)

                    conf_rank = {'hoch': 2, 'mittel': 1, 'niedrig': 0}
                    rank_to_conf = {2: 'hoch', 1: 'mittel', 0: 'niedrig'}
                    best_rank = max(conf_rank.get(mb_conf, 0), conf_rank.get(discogs_res['confidence'], 0))
                    combined_conf = rank_to_conf[best_rank] if oldest_year else 'niedrig'

                    df.at[idx, 'Artist_Vorschlag'] = suggest_artist_spelling(c_art) or ''
                    df.at[idx, 'Title_Vorschlag'] = suggest_title_spelling(art_sugg, c_tit) or ''
                    df.at[idx, 'Jahr_Vorschlag'] = oldest_year
                    df.at[idx, 'Jahr_Konfidenz'] = combined_conf
                    df.at[idx, 'Genre_Vorschlag'] = discogs_res['genre'] or ''
                    df.at[idx, 'Album_Vorschlag'] = discogs_res['album'] or mb_album or ''
                    df.at[idx, 'STYLE_Vorschlag'] = discogs_res['style']
                    df.at[idx, 'DISCOGS_RELEASE_ID_Vorschlag'] = discogs_res['discogs_id']
                    df.at[idx, 'Label_Vorschlag'] = discogs_res['label']
                    df.at[idx, 'Labelcode_Vorschlag'] = discogs_res['label_code']
                    df.at[idx, 'ISRC_Vorschlag'] = isrc or ''
                    df.at[idx, 'Sprache_Vorschlag'] = ''
                    df.at[idx, 'VORSCHLAG_STATUS'] = 'FERTIG'

                    conf_color = "green" if combined_conf == "hoch" else ("yellow" if combined_conf == "mittel" else "red")
                    locale_conf = t(f"conf_{combined_conf}")
                    progress.console.print(t('fetch_track_info', id=row.get('ID'), art=art_sugg, tit=tit_sugg, jahr=oldest_year or '?', c_color=conf_color, conf=locale_conf))
                
                except Exception as e:
                    log_change("ERROR", f"Track ID {row.get('ID')} gecrasht: {str(e)}")
                    progress.console.print(f"[bold red]Fehler bei Track ID {row.get('ID')}: {e} -> Wird übersprungen![/bold red]")

                processed_counter += 1
                progress.update(task, advance=1)
                if processed_counter % 20 == 0: save_safe_csv(df, fetch_csv)

        except KeyboardInterrupt:
            console.print(t('fetch_interrupt'))
            save_safe_csv(df, fetch_csv)
            sys.exit(0)

    save_safe_csv(df, fetch_csv)
    console.print(t('fetch_success', db=db_path))

# ---------------------------------------------------------------------------
# PHASE 2: review
# ---------------------------------------------------------------------------
class StepBackException(Exception):
    pass

def ask_input(prompt_text):
    clear_input_buffer()
    val = console.input(prompt_text).strip()
    if val.lower() == 'b' or val == '<':
        raise StepBackException()
    return val

def phase_review(fetch_csv, final_csv, auto_hoch=False):
    try: df = pd.read_csv(fetch_csv, dtype=str)
    except FileNotFoundError:
        console.print(t('err_file_not_found', file=fetch_csv) + t('err_need_fetch'))
        sys.exit(1)

    if 'REVIEW_STATUS' not in df.columns: df['REVIEW_STATUS'] = ''
    for col in MLDB_ATTRIBUTE_FIELDS:
        if col not in df.columns: df[col] = ''

    todo = df[(df['VORSCHLAG_STATUS'] == 'FERTIG') & (df['REVIEW_STATUS'] != 'JA')]
    auto_txt = t('rev_auto_active') if auto_hoch else ""
    console.print(Panel(t('rev_mode', todo=len(todo), auto=auto_txt), box=box.ROUNDED))

    reviewed_counter = 0
    todo_indices = list(todo.index)
    i = 0

    try:
        while i < len(todo_indices):
            idx = todo_indices[i]
            row = df.loc[idx]
            artist, title = row.get('Artist', ''), row.get('Title', '')

            console.print(f"\n[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
            console.print(t('rev_row', row=idx+1, id=row.get('ID'), art=artist, tit=title))
            custom_text_entered = False

            try:
                # 1. Artist
                art_sugg = clean_nan(row.get('Artist_Vorschlag'))
                if art_sugg:
                    inp = ask_input(t('rev_artist', sugg=art_sugg))
                    if inp.lower() in ['j', 'ja', 'y', 'yes']: df.at[idx, 'Artist'] = art_sugg
                    elif inp and inp.lower() not in ['n', 'nein']: 
                        df.at[idx, 'Artist'] = inp
                        custom_text_entered = True

                # 2. Title
                tit_sugg = clean_nan(row.get('Title_Vorschlag'))
                if tit_sugg:
                    inp = ask_input(t('rev_title', sugg=tit_sugg))
                    if inp.lower() in ['j', 'ja', 'y', 'yes']: df.at[idx, 'Title'] = tit_sugg
                    elif inp and inp.lower() not in ['n', 'nein']:
                        df.at[idx, 'Title'] = inp
                        custom_text_entered = True

                # Re-Fetch
                if custom_text_entered:
                    updated_art, updated_tit = df.at[idx, 'Artist'], df.at[idx, 'Title']
                    console.print(t('rev_refetch', art=updated_art, tit=updated_tit))
                    
                    c_art, c_tit = clean_artist_base(updated_art), clean_title_base(updated_tit)
                    mb_year, mb_conf, isrc, mb_album = fetch_musicbrainz_details(c_art, c_tit)
                    discogs_res = fetch_discogs_details(c_art, c_tit)

                    all_years = [mb_year] if mb_year else []
                    all_years += [y for y in discogs_res['years']]
                    oldest_year = filter_valid_years(all_years)

                    conf_rank = {'hoch': 2, 'mittel': 1, 'niedrig': 0}
                    rank_to_conf = {2: 'hoch', 1: 'mittel', 0: 'niedrig'}
                    best_rank = max(conf_rank.get(mb_conf, 0), conf_rank.get(discogs_res['confidence'], 0))
                    
                    df.at[idx, 'Jahr_Vorschlag'] = oldest_year
                    df.at[idx, 'Jahr_Konfidenz'] = rank_to_conf[best_rank] if oldest_year else 'niedrig'
                    df.at[idx, 'Genre_Vorschlag'] = discogs_res['genre'] or ''
                    df.at[idx, 'Album_Vorschlag'] = discogs_res['album'] or mb_album or ''
                    df.at[idx, 'STYLE_Vorschlag'] = discogs_res['style'] or ''
                    df.at[idx, 'DISCOGS_RELEASE_ID_Vorschlag'] = discogs_res['discogs_id'] or ''
                    df.at[idx, 'Label_Vorschlag'] = discogs_res['label'] or ''
                    df.at[idx, 'Labelcode_Vorschlag'] = discogs_res['label_code'] or ''
                    df.at[idx, 'ISRC_Vorschlag'] = isrc or ''

                # 3. Jahr
                jahr_sugg = clean_nan(df.at[idx, 'Jahr_Vorschlag'])
                konf = clean_nan(df.at[idx, 'Jahr_Konfidenz']) or 'niedrig'
                conf_badge = f"[green]{t('conf_hoch')}[/green]" if konf == "hoch" else (f"[yellow]{t('conf_mittel')}[/yellow]" if konf == "mittel" else f"[red]{t('conf_niedrig')}[/red]")
                
                if jahr_sugg:
                    if auto_hoch and konf == 'hoch':
                        df.at[idx, 'Jahr'] = jahr_sugg
                        console.print(t('rev_year_auto', sugg=jahr_sugg))
                    else:
                        inp = ask_input(t('rev_year', sugg=jahr_sugg, badge=conf_badge))
                        if inp.lower() in ['j', 'ja', 'y', 'yes']: df.at[idx, 'Jahr'] = jahr_sugg
                        elif inp and inp.lower() not in ['n', 'nein']: df.at[idx, 'Jahr'] = inp

                # 4. Genre
                genre_sugg = clean_nan(df.at[idx, 'Genre_Vorschlag'])
                if genre_sugg:
                    if auto_hoch and konf == 'hoch':
                        df.at[idx, 'Genre'] = genre_sugg
                        console.print(t('rev_genre_auto', sugg=genre_sugg))
                    else:
                        inp = ask_input(t('rev_genre', sugg=genre_sugg))
                        if inp.lower() in ['j', 'ja', 'y', 'yes']: df.at[idx, 'Genre'] = genre_sugg
                        elif inp and inp.lower() not in ['n', 'nein']: df.at[idx, 'Genre'] = inp

                # 5. Album
                album_sugg = clean_nan(df.at[idx, 'Album_Vorschlag'] if 'Album_Vorschlag' in df.columns else row.get('Album_Vorschlag'))
                disp_album = album_sugg if album_sugg else t('no_sugg')
                inp = ask_input(t('rev_album', sugg=disp_album))
                if inp.lower() in ['j', 'ja', 'y', 'yes']:
                    if album_sugg: df.at[idx, 'Album'] = album_sugg
                elif inp and inp.lower() not in ['n', 'nein']: df.at[idx, 'Album'] = inp

                # 6. Label
                label_sugg = clean_nan(df.at[idx, 'Label_Vorschlag'] if 'Label_Vorschlag' in df.columns else row.get('Label_Vorschlag'))
                disp_label = label_sugg if label_sugg else t('no_sugg')
                inp = ask_input(t('rev_label', sugg=disp_label))
                if inp.lower() in ['j', 'ja', 'y', 'yes']:
                    if label_sugg: df.at[idx, 'Label'] = label_sugg
                elif inp and inp.lower() not in ['n', 'nein']: df.at[idx, 'Label'] = inp

                # 7. Sprache & Dynamisches Menu
                lang_sugg = clean_nan(df.at[idx, 'Sprache_Vorschlag'] if 'Sprache_Vorschlag' in df.columns else row.get('Sprache_Vorschlag'))
                disp_lang = lang_sugg if lang_sugg else t('no_sugg')
                
                lang_map = {'1': 'Englisch' if CURRENT_LANG == 'de' else 'English',
                            '2': 'Deutsch' if CURRENT_LANG == 'de' else 'German'}
                nxt_idx = 3
                for cl in CUSTOM_LANGS:
                    lang_map[str(nxt_idx)] = cl
                    nxt_idx += 1
                    
                hint_parts = ["j", "Enter"]
                for k, v in lang_map.items(): hint_parts.append(f"{k}={v}")
                hint_parts.append("Text")
                hint_str = "/".join(hint_parts)
                
                inp = ask_input(t('rev_lang', sugg=disp_lang, hint=hint_str))
                
                if inp.lower() in ['j', 'ja', 'y', 'yes']:
                    if lang_sugg: df.at[idx, 'Sprache'] = lang_sugg
                elif inp in lang_map:
                    df.at[idx, 'Sprache'] = lang_map[inp]
                elif inp and inp.lower() not in ['n', 'nein']: 
                    df.at[idx, 'Sprache'] = inp
                    if inp not in CUSTOM_LANGS and inp not in [lang_map['1'], lang_map['2']]:
                        add_custom_lang(inp)

                # Restliche Attribute (Style, Discogs-ID, Labelcode, ISRC)
                for target_col, sugg_col in [
                    ('STYLE', 'STYLE_Vorschlag'), ('DISCOGS_RELEASE_ID', 'DISCOGS_RELEASE_ID_Vorschlag'),
                    ('Labelcode', 'Labelcode_Vorschlag'), ('ISRC', 'ISRC_Vorschlag'),
                ]:
                    s_val = clean_nan(df.at[idx, sugg_col] if sugg_col in df.columns else row.get(sugg_col))
                    if s_val: df.at[idx, target_col] = s_val

            except StepBackException:
                if i > 0:
                    i -= 1
                    console.print("[yellow]⏪ Okay, einen Track zurück...[/yellow]")
                else:
                    console.print("[yellow]⚠️ Das ist bereits der erste Track! Weiter zurück geht's nicht.[/yellow]")
                continue

            df.at[idx, 'REVIEW_STATUS'] = 'JA'
            log_change("REVIEW_OK", f"ID {row.get('ID')}: {df.at[idx, 'Artist']} - {df.at[idx, 'Title']}")
            reviewed_counter += 1
            if reviewed_counter % 10 == 0:
                save_safe_csv(df, fetch_csv)
                console.print(t('rev_interim'))
            
            i += 1 # Nächster Track

    except KeyboardInterrupt:
        console.print(t('rev_interrupt'))
        save_safe_csv(df, fetch_csv)
        sys.exit(0)

    save_safe_csv(df, fetch_csv)
    save_safe_csv(df, final_csv)
    console.print(t('rev_success', csv=final_csv))

# ---------------------------------------------------------------------------
# PHASE 3: apply
# ---------------------------------------------------------------------------
def phase_apply(db_path, final_csv):
    if not os.path.exists(db_path):
        console.print(t('err_file_not_found', file=db_path))
        sys.exit(1)
    if not os.path.exists(final_csv):
        console.print(t('err_file_not_found', file=final_csv) + t('err_need_fetch_rev'))
        sys.exit(1)

    console.print(Panel(t('apply_warn'), box=box.HEAVY))

    if is_db_locked(db_path):
        console.print(Panel(t('apply_locked'), box=box.HEAVY, style="red"))
        sys.exit(1)

    clear_input_buffer()
    confirm_word = t('apply_confirm_word')
    confirm = console.input(t('apply_confirm')).strip()
    if confirm.lower() not in [confirm_word.lower(), 'j', 'ja', 'y', 'yes']:
        console.print(t('apply_abort'))
        sys.exit(0)

    backup_path = f"{db_path}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    console.print(t('apply_backup', path=backup_path))

    df = pd.read_csv(final_csv, dtype=str)
    if 'REVIEW_STATUS' in df.columns:
        df = df[df['REVIEW_STATUS'] == 'JA']

    try:
        updated = apply_dataframe_to_mldb(df, db_path)
    except sqlite3.OperationalError as e:
        console.print(t('apply_err_lock', err=str(e)))
        sys.exit(1)

    console.print(t('apply_success', count=updated, db=db_path))

def main():
    global CURRENT_LANG
    parser = argparse.ArgumentParser(description=f"mAirList DB Restorer v{APP_VERSION}")
    parser.add_argument('phase', choices=['fetch', 'review', 'apply'])
    parser.add_argument('--auto-hoch', action='store_true')
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--db', required=True, help="Pfad zur mAirList .mldb-Datei")
    parser.add_argument('--lang', choices=['de', 'en'], default='de')
    args = parser.parse_args()

    CURRENT_LANG = args.lang
    
    # NEU: Dynamischer Log-Datei-Name mit DB-Namen und Timestamp
    db_base_name = os.path.splitext(os.path.basename(args.db))[0]
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    dynamic_log_file = f"{db_base_name}_{timestamp_str}.log"
    
    logging.basicConfig(
        filename=dynamic_log_file,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8'
    )
    
    init_credentials()

    fetch_csv = f"{db_base_name}_vorschlaege.csv"
    final_csv = f"{db_base_name}_restauriert.csv"

    if args.phase == 'fetch': phase_fetch(args.db, fetch_csv, full=args.full)
    elif args.phase == 'review': phase_review(fetch_csv, final_csv, auto_hoch=args.auto_hoch)
    else: phase_apply(args.db, final_csv)

if __name__ == '__main__':
    main()