import pandas as pd
import re
import json
import os
import csv
import base64
import difflib
import logging
from datetime import datetime
from collections import Counter

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console(highlight=False)

APP_VERSION = "0.5.0 Beta"
CONFIG_FILE = 'config.json'

# Globale Variablen für die Session
CURRENT_LANG = 'de'
DISCOGS_KEY = ""
DISCOGS_SECRET = ""
MB_CONTACT = ""
HEADERS = {}
CUSTOM_LANGS = []

MLDB_ATTRIBUTE_FIELDS = [
    'Jahr', 'Genre', 'Album', 'STYLE', 'DISCOGS_RELEASE_ID',
    'Label', 'Labelcode', 'ISRC', 'Sprache', 'RESTAURIERT'
]

# ---------------------------------------------------------------------------
# Language Dictionary
# ---------------------------------------------------------------------------
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
        'fetch_success': "\n[bold green]✓ Fetch erfolgreich abgeschlossen![/bold green] Nächster Schritt: [bold cyan]py main.py review --db \"{db}\"[/bold cyan]",
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
        'conf_hoch': "hoch", 'conf_mittel': "mittel", 'conf_niedrig': "niedrig",
        'std_start': "\n[bold cyan]Starte Genre-Standardisierung in der gesamten Datenbank...[/bold cyan]",
        'std_done': "[bold green]✓ Fertig! {count} unsaubere Genres wurden erfolgreich ueberschrieben.[/bold green]",
        'std_no_changes': "[yellow]Keine Aenderungen noetig. Alle Genres der DB sind bereits standardisiert![/yellow]"
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
        'fetch_success': "\n[bold green]✓ Fetch completed successfully![/bold green] Next step: [bold cyan]py main.py review --db \"{db}\"[/bold cyan]",
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
        'conf_hoch': "high", 'conf_mittel': "medium", 'conf_niedrig': "low",
        'std_start': "\n[bold cyan]Starting genre standardization across the entire database...[/bold cyan]",
        'std_done': "[bold green]✓ Done! {count} unstandardized genres successfully updated.[/bold green]",
        'std_no_changes': "[yellow]No changes needed. All DB genres are already standardized![/yellow]"
    }
}

# ---------------------------------------------------------------------------
# Basis-Hilfsfunktionen
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
    current_year = datetime.now().year
    valid = sorted([int(y) for y in years_list if str(y).isdigit() and 1900 <= int(y) <= current_year])
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

def save_safe_csv(df, filepath):
    if 'LYRICS' in df.columns:
        df['LYRICS'] = df['LYRICS'].fillna('').astype(str)
        df['LYRICS'] = df['LYRICS'].str.replace(r'[\r\n]+', ' ', regex=True)
        df['LYRICS'] = df['LYRICS'].str.replace(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', regex=True)
    df.to_csv(filepath, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)

# ---------------------------------------------------------------------------
# Konfiguration & Setup
# ---------------------------------------------------------------------------
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
    global CUSTOM_LANGS
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
# Cleaning & Genre-Dictionaries
# ---------------------------------------------------------------------------
ALLOWED_GENRES = [
    "Pop", "EDM", "Blues", "Hiphop", "Rap", "Rock", "Classic Rock", 
    "R and B", "Soul", "Reggae"
]

GENRE_SYNONYMS = {
    "house": "EDM", "deep house": "EDM", "techno": "EDM", "trance": "EDM", 
    "eurodance": "EDM", "dubstep": "EDM", "dance": "EDM", "dance-pop": "EDM", 
    "slap house": "EDM", "big room": "EDM", "future house": "EDM", "hardstyle": "EDM", 
    "progressive house": "EDM", "psytrance": "EDM", "tech house": "EDM", 
    "trap": "EDM", "tropical house": "EDM", "electronic": "EDM", "euro house": "EDM",
    "hard rock": "Rock", "indie rock": "Rock", "punk rock": "Rock", 
    "gothic rock": "Rock", "alternative rock": "Rock", "pop-rock": "Rock", 
    "metal": "Rock", "heavy metal": "Rock", "nu metal": "Rock", "industrial": "Rock", 
    "rock n roll": "Rock", "rock & roll": "Rock", "rock 'n' roll": "Rock", "deutsch-rock": "Rock",
    "synth-pop": "Pop", "synthpop": "Pop", "deutsch-pop": "Pop", "indie pop": "Pop",
    "hip hop": "Hiphop", "hip-hop": "Hiphop", "deutsch-hiphop": "Hiphop",
    "r&b": "R and B", "r&b / soul": "R and B",
    "dancehall": "Reggae"
}

COMPILATION_KEYWORDS = [
    'compilation', 'best of', 'greatest hits', 'essential', 'collection',
    'various', 'remix', 'live', 'anthology', 'singles', 'ultimate', 'hit mix', 'bravo',
    'soundtrack', 'o.s.t.', 'ost', 'the dome', 'now that'
]

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

def t(key, **kwargs):
    return T[CURRENT_LANG][key].format(**kwargs)