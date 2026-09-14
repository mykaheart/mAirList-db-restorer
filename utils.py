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

APP_VERSION = "0.65.00 BETA"

# --- CONFIG.JSON IN DEN DATA-ORDNER VERSCHIEBEN ---
DATA_DIR = "Data"
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

# Globale Variablen für die Session
CURRENT_LANG = 'de'
DISCOGS_KEY = ""
DISCOGS_SECRET = ""
MB_CONTACT = ""
HEADERS = {}
CUSTOM_LANGS = []
CUSTOM_GENRES = []

MLDB_ATTRIBUTE_FIELDS = [
    'Jahr', 'Genre', 'Album', 'STYLE', 'DISCOGS_RELEASE_ID',
    'Label', 'Labelcode', 'ISRC', 'Sprache', 'Typ', 'BPM', 'RESTAURIERT', 'DOPPELUNG'
]

ITEM_TYPE_MAPPINGS = {
    'de': {
        'Unknown': 'nicht gesetzt', 'Music': 'Musik', 'Voice': 'Moderation',
        'News': 'Nachrichten', 'Weather': 'Wetter', 'Traffic': 'Verkehr',
        'Advertising': 'Werbung', 'Package': 'Beitrag', 'Jingle': 'Jingle',
        'Sound': 'Geräusch', 'Trailer': 'Trailer', 'Promo': 'Promo',
        'Sponsorship': 'Sponsor-Jingle', 'Sweeper': 'Sweeper', 'Drop': 'Drop',
        'StationID': 'Station-ID', 'Bed': 'Bett', 'Instrumental': 'Instrumental',
        'Show': 'Sendung', 'Stream': 'Stream', 'Container': 'Container',
        'Playlist': 'Playlist', 'Command': 'Befehl', 'CartwallPage': 'Cartwall-Seite',
        'Break': 'Unterbrechung', 'Dummy': 'Platzhalter', 'Silence': 'Stille',
        'Error': 'Fehler', 'Other': 'Andere', 'Custom1': 'Benutzerdefiniert 1',
        'Custom2': 'Benutzerdefiniert 2', 'Custom3': 'Benutzerdefiniert 3'
    },
    'en': {
        'Unknown': 'not set', 'Music': 'Music', 'Voice': 'Voice',
        'News': 'News', 'Weather': 'Weather', 'Traffic': 'Traffic',
        'Advertising': 'Advertising', 'Package': 'Package', 'Jingle': 'Jingle',
        'Sound': 'Sound', 'Trailer': 'Trailer', 'Promo': 'Promo',
        'Sponsorship': 'Sponsorship', 'Sweeper': 'Sweeper', 'Drop': 'Drop',
        'StationID': 'Station ID', 'Bed': 'Bed', 'Instrumental': 'Instrumental',
        'Show': 'Show', 'Stream': 'Stream', 'Container': 'Container',
        'Playlist': 'Playlist', 'Command': 'Command', 'CartwallPage': 'Cartwall Page',
        'Break': 'Break', 'Dummy': 'Placeholder', 'Silence': 'Silence',
        'Error': 'Error', 'Other': 'Other', 'Custom1': 'Custom 1',
        'Custom2': 'Custom 2', 'Custom3': 'Custom 3'
    },
    'nl': {
        'Unknown': 'niet ingesteld', 'Music': 'Muziek', 'Voice': 'Presentatie',
        'News': 'Nieuws', 'Weather': 'Weer', 'Traffic': 'Verkeer',
        'Advertising': 'Reclame', 'Package': 'Bijdrage', 'Jingle': 'Jingle',
        'Sound': 'Geluid', 'Trailer': 'Trailer', 'Promo': 'Promo',
        'Sponsorship': 'Sponsor-jingle', 'Sweeper': 'Sweeper', 'Drop': 'Drop',
        'StationID': 'Station-ID', 'Bed': 'Bed', 'Instrumental': 'Instrumentaal',
        'Show': 'Programma', 'Stream': 'Stream', 'Container': 'Container',
        'Playlist': 'Afspeellijst', 'Command': 'Commando', 'CartwallPage': 'Cartwall-pagina',
        'Break': 'Onderbreking', 'Dummy': 'Plaatshouder', 'Silence': 'Stilte',
        'Error': 'Fout', 'Other': 'Anders', 'Custom1': 'Aangepast 1',
        'Custom2': 'Aangepast 2', 'Custom3': 'Aangepast 3'
    }
}

def map_item_type(raw_type, lang=None):
    lang = lang if lang in ITEM_TYPE_MAPPINGS else CURRENT_LANG
    mapping = ITEM_TYPE_MAPPINGS.get(lang, ITEM_TYPE_MAPPINGS['de'])
    return mapping.get(str(raw_type).strip(), '')

T = {
    'de': {
        'menu_copyright': "(c) 2026 by Myka Vormeng (Concept)\n           and ChatGPT (Programming)",
        'menu_title': "mAirList Datenbank-Assistent",
        'menu_db_none': "Keine Datenbank ausgewählt – beginne mit Option 0.",
        'menu_db_act': "Aktive Datenbank:",
        'menu_opt0': "Datenbank-Kopie auswählen oder wechseln",
        'menu_desc0': "Wähle die .mldb-Kopie, mit der der Restorer arbeiten soll.",
        'menu_h1': "--- SCHRITT 1: METADATEN SUCHEN ---",
        'menu_opt1': "Neue/unbearbeitete Tracks suchen",
        'menu_desc1': "Lädt Vorschläge in Blöcken à 50; jederzeit fortsetzbar.",
        'menu_opt2': "Alle offenen Tracks ohne Pause suchen",
        'menu_desc2': "Wie Option 1, läuft aber bis zum Ende durch – ideal über Nacht.",
        'menu_opt3': "Alle Tracks komplett neu prüfen",
        'menu_desc3': "Ignoriert den Restauriert-Status und holt für jeden Track neue Vorschläge.",
        'menu_h2': "--- SCHRITT 2: VORSCHLÄGE PRÜFEN ---",
        'menu_opt4': "Alle Vorschläge selbst kontrollieren",
        'menu_desc4': "Jeden gefundenen Wert einzeln ansehen, übernehmen oder ändern.",
        'menu_opt5': "Prüfung mit Automatik",
        'menu_desc5': "Sichere Jahr-/Genre-Treffer automatisch; alles andere bleibt kontrollierbar.",
        'menu_h3': "--- OPTIONAL: DATENBANK / DATEIEN PFLEGEN ---",
        'menu_opt6': "Wartungswerkzeuge öffnen",
        'menu_desc6': "Genres/Schreibweisen bereinigen, Dopplungen markieren oder geprüfte Tags schreiben.",
        'menu_h4': "--- SCHRITT 3: GEPRÜFTE ÄNDERUNGEN SPEICHERN ---",
        'menu_opt7': "Geprüfte Änderungen in die Datenbank-Kopie schreiben",
        'menu_desc7': "Zeigt zuerst eine Zusammenfassung, erstellt ein Backup und speichert danach.",
        'menu_opt8': "Sprache ändern / Change Language",
        'menu_opt9': "Programm beenden",
        'menu_workflow': "Empfohlener Ablauf: 1 suchen → 4/5 prüfen → 7 speichern",
        'menu_prompt': "Auswahl [0-9]:",
        'menu_err': "Ungültige Auswahl. Bitte erneut versuchen.",
        'menu_err_db': "Fehler: Keine Datenbank ausgewählt! Bitte wähle zuerst Option 0.",
        'db_invalid_file': "Fehler: Die ausgewählte Datei ist keine lesbare mAirList-.mldb-Datenbank oder ihre Schema-Version konnte nicht ermittelt werden.",
        'db_read_error': "Die mAirList-Datenbank konnte nicht vollständig gelesen werden: {details}",
        'db_incompatible': "Inkompatible Datenbank!\n\nSchema-Version: [bold yellow]{version}[/bold yellow]\nUnterstützt: [bold green]{supported}[/bold green]\nRestorer-Version: {app_version}",
        'menu_path_hint1': "Hinweis: Bitte den Pfad zu einer KOPIE deiner Datenbank angeben.",
        'menu_path_hint2': "(Tipp: Einfach die .mldb-Datei in dieses Fenster ziehen und Enter drücken)",
        'menu_path_prompt': "Pfad: ",
        'menu_warn_full': "ACHTUNG: Dies ruft ALLE Tracks erneut ab, auch bereits verarbeitete.",
        'menu_sure': "Wirklich fortfahren? [j/N]: ",
        'menu_warn_apply1': "ACHTUNG: Dieser Vorgang schreibt alle geprüften Werte in die oben",
        'menu_warn_apply2': "ausgewählte .mldb-Datei. Nutze hierfür IMMER EINE KOPIE!",
        'menu_continue': "Drücke Enter, um ins Hauptmenü zurückzukehren...",
        'setup_title': "[bold cyan]Ersteinrichtung: API-Zugangsdaten[/bold cyan]\nAngaben werden lokal im 'Data'-Ordner gespeichert.",
        'setup_discogs': "[bold yellow]-- Discogs API --[/bold yellow]",
        'setup_mb': "\n[bold yellow]-- MusicBrainz Contact --[/bold yellow]",
        'setup_email': "  Deine Kontakt-E-Mail: ",
        'setup_email_err': "[red]Ungültige E-Mail-Adresse, bitte erneut eingeben.[/red]",
        'setup_saved': "[green]✓ Zugangsdaten lokal gespeichert in '{config_file}'.[/green]\n",
        'ign_current': "\n[cyan]Aktuelle Ordner-Ausnahmen für diese DB:[/cyan] [yellow]{liste}[/yellow]",
        'ign_reset': "Möchtest du diese Liste neu erstellen? [j/N]: ",
        'ign_none': "Keine",
        'ign_setup_title': "\n[bold cyan]Ordner-Ausnahmen für diese Datenbank konfigurieren[/bold cyan]\nHier kannst du Ordner angeben, die ignoriert werden sollen (z.B. Jingles, News).",
        'ign_prompt': "  [cyan]Drag & Drop Ordner hierher[/cyan] ODER tippe [cyan]virtuellen Ordnernamen[/cyan] (Enter = Fertig): ",
        'ign_added_phys': "  [green]✓ Physikalischer Pfad ignoriert:[/green] {path}",
        'ign_added_virt': "  [green]✓ Virtueller/Teil-Ordner ignoriert:[/green] {name}",
        'ign_saved': "[green]✓ Ausnahmen für diese DB gespeichert![/green]\n",
        'ign_skip_count': "\n[bold green]✓ SUCCESS: {count} ignorierte Elemente (OAD/Jingles/News) erfolgreich übersprungen![/bold green]",
        'fetch_load_prog': "[cyan]Fortschritt geladen aus '{csv}' ({count} Zeilen).[/cyan]",
        'fetch_sync_del': "[yellow]-> {count} Track(s) wurden in mAirList gelöscht und aus CSV entfernt.[/yellow]",
        'fetch_new_tracks': "[green]-> {count} neue Track(s) aus '{db}' ergänzt.[/green]",
        'fetch_reset': "[yellow]-> {count} Track(s) in mAirList zurückgesetzt – werden neu gefetcht![/yellow]",
        'fetch_first': "[cyan]Erster Lauf: Lese direkt aus SQLite-Kopie '{db}'.[/cyan]",
        'fetch_bpm_rb_prompt': "rekordbox XML für BPM (optional; Enter = {default}, '-' = ohne XML): ",
        'fetch_bpm_rb_none': "ohne XML",
        'fetch_bpm_rb_missing': "[yellow]rekordbox XML nicht gefunden: {path} – Fetch läuft mit Datei-Tags/API-Fallback weiter.[/yellow]",
        'fetch_bpm_rb_invalid': "[yellow]rekordbox XML konnte nicht gelesen werden ({details}) – Fetch läuft mit Datei-Tags/API-Fallback weiter.[/yellow]",
        'fetch_bpm_rb_loaded': "[green]✓ BPM-Quelle rekordbox XML:[/green] {entries} Einträge, {valid} mit gültigem BPM.",
        'fetch_full': "[bold yellow]Vollständige Neuprüfung angefordert (--full)[/bold yellow]",
        'fetch_start': "[bold green]Starte automatischen Fetch[/bold green]\nOffene Tracks: [bold yellow]{offen}[/bold yellow] von [bold]{total}[/bold] Gesamt",
        'fetch_done_already': "[bold green]✓ Alle Tracks sind bereits auf dem neuesten Stand![/bold green]",
        'fetch_progress': "[bold magenta]Fetching Metadaten...",
        'fetch_track_info': "  [dim]ID {id}:[/dim] [bold]{art} - {tit}[/bold] (Jahr: [bold cyan]{jahr}[/bold cyan], Konfidenz: [{c_color}]{conf}[/{c_color}])",
        'fetch_track_retry': "[bold yellow]⚠ ID {id}: vorübergehender API-/Netzwerkfehler – automatischer Wiederholungsversuch {retry}/{max_retry} in {delay} s.[/bold yellow]",
        'fetch_track_error': "[bold yellow]⚠ ID {id}: API-/Netzwerkfehler trotz automatischer Wiederholungen. Track bleibt offen und wird beim nächsten Abruf erneut versucht.[/bold yellow]",
        'fetch_done_with_errors': "\n[bold yellow]⚠ Abruf beendet, aber {count} Track(s) konnten trotz automatischer Wiederholungen wegen API-/Netzwerkfehlern nicht abgeschlossen werden. Sie bleiben offen und werden beim nächsten Abruf erneut versucht.[/bold yellow]",
        'fetch_interrupt': "\n[bold yellow]Abruf unterbrochen. Fortschritt sicher gespeichert.[/bold yellow]",
        'fetch_success': "\n[bold green]✓ Fetch erfolgreich abgeschlossen![/bold green] Nächster Schritt: [bold cyan]Option [4] oder [5] im Hauptmenü (Review)[/bold cyan]",
        'fetch_paused_review': "\n[bold cyan]Abruf nach diesem Block pausiert.[/bold cyan] Du kannst die geladenen Tracks jetzt mit Option 4 oder 5 prüfen. Option 1 setzt den Abruf später fort.",
        'fetch_chunk_pause': "\n[bold yellow]☕ {count} Tracks geladen![/bold yellow]\nMöchtest du diese jetzt kontrollieren (Review)? \n[dim]Tipp: Du kannst den Fetch später im Hauptmenü (Option 1) jederzeit fortsetzen.[/dim]",
        'fetch_chunk_prompt': "Tippe [cyan]'r'[/cyan] für Review oder [green]Enter[/green], um weitere 50 Tracks zu laden: ",
        'err_file_not_found': "[bold red][Fehler][/bold red] '{file}' nicht gefunden.",
        'err_need_fetch': " Erst 'fetch' ausführen.",
        'rev_mode': "[bold cyan]Review Modus[/bold cyan]\nOffene Prüfungen: [bold yellow]{todo}[/bold yellow]{auto}\n[dim]Tipp: Tippe '<' oder 'b' und Enter, um einen Track zurückzuspringen![/dim]",
        'rev_auto_active': "\n[green]--auto-hoch aktiv[/green]",
        'rev_row': "[bold white on blue] Zeile {row} (ID: {id}) [/bold white on blue] [bold]{art} - {tit}[/bold]",
        'rev_artist': "  [cyan]Artist[/cyan] -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Vorschlag / [yellow]o[/yellow]=Orig / Text][/dim]: ",
        'rev_title': "  [cyan]Title[/cyan]  -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Vorschlag / [yellow]o[/yellow]=Orig / Text][/dim]: ",
        'rev_refetch': "  [magenta]⚡ Freitext erkannt! Live Re-Fetch für '{art} - {tit}'...[/magenta]",
        'rev_year_auto': "  [cyan]Jahr[/cyan]   -> [bold green]{sugg}[/bold green] [dim](auto, Orig: '{orig}')[/dim]",
        'rev_year': "  [cyan]Jahr[/cyan]   -> Vorschlag: '[bold green]{sugg}[/bold green]' ({badge}) [dim](Orig: '{orig}') \\[[green]Enter[/green]=Vorschlag / [yellow]o[/yellow]=Orig / Jahr][/dim]: ",
        'rev_genre_auto': "  [cyan]Genre[/cyan]  -> [bold green]{sugg}[/bold green] [dim](auto, Orig: '{orig}')[/dim]",
        'rev_genre': "  [cyan]Genre[/cyan]  -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Vorschlag / [yellow]o[/yellow]=Orig / {hint}][/dim]: ",
        'rev_album': "  [cyan]Album[/cyan]  -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Vorschlag / [yellow]o[/yellow]=Orig / Text][/dim]: ",
        'rev_label': "  [cyan]Label[/cyan]  -> Vorschlag: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Vorschlag / [yellow]o[/yellow]=Orig / Text][/dim]: ",
        'rev_lang':  "  [cyan]Sprache[/cyan]-> Vorschlag: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Vorschlag / [yellow]o[/yellow]=Orig / {hint}][/dim]: ",
        'rev_bpm_auto': "  [cyan]BPM[/cyan]     -> [bold green]{sugg}[/bold green] [dim](automatisch aus {source}; vorhandene BPM werden geschützt)[/dim]",
        'no_sugg': "- (Kein Vorschlag) -",
        'rev_interim': "[dim]  (Zwischenstand gespeichert)[/dim]",
        'rev_interrupt': "\n\n[bold yellow]Review unterbrochen. Bisherige Entscheidungen sind gespeichert.[/bold yellow]",
        'rev_success': "\n[bold green]✓ Review abgeschlossen![/bold green] Finales Ergebnis in [bold cyan]'{csv}'[/bold cyan]. Nächster Schritt: [bold cyan]Option [7] im Hauptmenü (Speichern)[/bold cyan]",
        'err_need_fetch_rev': " Erst 'fetch' und 'review' durchführen.",
        'apply_warn': "[bold red]ACHTUNG: Schreibvorgang in .mldb-Datei[/bold red]\nNiemals auf eine aktiv von mAirList geöffnete Datei anwenden!",
        'apply_locked': "[bold red]Datenbank ist aktuell gesperrt![/bold red]\nVermutlich hat mAirList (oder ein anderes Programm) diese Datei\ngerade geöffnet. Schließe das Programm bzw. wähle eine echte\nKopie der Datei aus und versuche es erneut.",
        'apply_confirm': "Ist dies definitiv eine KOPIE? Zum Fortfahren '[bold green]JA[/bold green]' eintippen: ",
        'apply_confirm_word': "JA",
        'apply_abort': "[yellow]Abgebrochen.[/yellow]",
        'apply_backup': "[green]✓ Backup angelegt: {path}[/green]",
        'apply_backup_clean': "[dim]✓ Alte Backups aufgeräumt (die neuesten 5 wurden behalten).[/dim]",
        'apply_err_lock': "\n[bold red][Fehler] Datenbank gelockt / Zugriff verweigert:[/bold red] {err}",
        'apply_success': "\n[bold green]✓ Fertig! {count} Zeile(n) in '{db}' erfolgreich aktualisiert.[/bold green]",
        'apply_no_new': "\n[yellow]Keine neuen Daten zum Speichern vorhanden. (Alle Einträge in der CSV sind in der DB bereits als 'RESTAURIERT' markiert).[/yellow]",
        'apply_integrity_check': "[cyan]Prüfe Datenbank-Integrität...[/cyan]",
        'apply_integrity_ok': "[green]✓ Datenbank-Integrität: OK[/green]",
        'apply_integrity_fail': "[bold red]⛔ Datenbank-Integritätsprüfung fehlgeschlagen:[/bold red] {details}\nEs werden keine Änderungen geschrieben.\n\n[dim]Hinweis: Die Inkonsistenz war bereits vor diesem Schreibvorgang vorhanden; der Restorer hat nichts verändert. Meldungen wie 'wrong # of entries in index ...' betreffen in der Regel SQLite-Indizes. Der Restorer repariert solche Datenbankstrukturen bewusst nicht automatisch.[/dim]",
        'apply_integrity_after_fail': "[bold red]⛔ WARNUNG: Integritätsprüfung nach dem Schreiben fehlgeschlagen![/bold red]\nBackup: {backup}\nDetails: {details}",
        'apply_summary_title': "Änderungen vor dem Speichern",
        'apply_summary_field': "Feld",
        'apply_summary_count': "Änderungen",
        'apply_summary_total': "Geprüfte Tracks, die geschrieben werden",
        'apply_summary_force': "Davon bewusst komplett neu geprüft (Voll-Abruf)",
        'apply_summary_restored': "Tracks werden als RESTAURIERT markiert",
        'conf_hoch': "hoch", 'conf_mittel': "mittel", 'conf_niedrig': "niedrig",
        'maint_title': "\n[bold cyan]=== WARTUNGS-MENÜ ===[/bold cyan]",
        'maint_warn': "[bold red]ACHTUNG: WARTUNG KANN DATENBANK ODER AUDIODATEIEN DIREKT VERÄNDERN![/bold red]\nBitte arbeite mit einer Datenbank-Kopie und sichere Dateien vor dem Tagger.",
        'maint_opt1': "  [[green]1[/green]] Genres standardisieren",
        'maint_opt2': "  [[green]2[/green]] Groß-/Kleinschreibung & Apostrophe korrigieren (Artist/Title)",
        'maint_opt3': "  [[green]3[/green]] Datei-Tagger + mAirList-Metadatensicherung",
        'maint_opt4': "  [[green]4[/green]] ALLE Wartungsaufgaben (1-2) nacheinander ausführen",
        'maint_opt5': "  [[green]5[/green]] Dopplungs-Kandidaten markieren / Status aktualisieren",
        'maint_opt6': "  [[green]6[/green]] Fehlende BPM ergänzen (rekordbox XML / Datei-Tags / MusicBrainz + AcousticBrainz)",
        'maint_opt0': "  [[green]0[/green]] Zurück ins Hauptmenü",
        'maint_prompt': "Auswahl [0-6]: ",
        'tagger_mode_title': "[bold cyan]Datei-Tagger[/bold cyan]",
        'tagger_mode_desc': "[dim]1 schreibt nur portable Audio-Tags. 2 sichert zusätzlich mAirList-Cues, Pegelanalyse und Normalisierung (MP3/AIFF eingebettet, FLAC/Ogg als .mmd).[/dim]",
        'tagger_mode_prompt': "Modus [1=Tags / 2=Tags+mAirList / 0=Abbruch]: ",
        'tagger_mode_invalid': "[red]Bitte 0, 1 oder 2 wählen.[/red]",
        'tagger_path_intro': "[cyan]=== Lokale Pfad-Zuordnung ===[/cyan]\nDa mAirList Storage Locations nutzt, können in der DB relative Pfade stehen. Füge die lokalen Basisordner hinzu; Enter startet.",
        'tagger_path_prompt': "Basis-Ordner (optional, Enter = starten): ",
        'tagger_path_added': "[green]✓ Ordner hinzugefügt:[/green] {path}",
        'tagger_path_invalid': "[red]Ordner existiert nicht oder ist ungültig.[/red]",
        'tagger_working': "[magenta]Lese Dateien und schreibe Tags...[/magenta]",
        'tagger_diag_title': "Tagger-Diagnose",
        'tagger_diag_total': "Tracks in Datenbank mit Pfad",
        'tagger_diag_missing': "Pfade/Dateien nicht gefunden",
        'tagger_diag_unsupported': "Nicht unterstütztes Format",
        'tagger_diag_perfect': "Tags/Metadaten waren bereits perfekt",
        'tagger_diag_updated': "Dateien erfolgreich aktualisiert",
        'tagger_diag_embedded': "mAirList-Blöcke eingebettet",
        'tagger_diag_sidecar': "mAirList-.mmd geschrieben/aktualisiert",
        'maint_bpm_intro': "[cyan]Suche fehlende BPM-Werte...[/cyan]\n[dim]Vorhandene BPM werden niemals überschrieben. Priorität: rekordbox XML per exaktem Dateipfad, danach Datei-Tag, danach MusicBrainz + AcousticBrainz als Fallback.[/dim]",
        'maint_bpm_rb_prompt': "rekordbox XML (optional, Enter = ohne XML): ",
        'maint_bpm_rb_invalid': "[red]rekordbox XML wurde nicht gefunden oder ist ungültig.[/red]",
        'maint_bpm_rb_loaded': "[green]✓ rekordbox XML geladen:[/green] {entries} Einträge, {valid} mit gültigem BPM.",
        'maint_bpm_rb': "Treffer aus rekordbox XML",
        'maint_bpm_rb_unmatched': "Nicht aus rekordbox übernommen (Fallback)",
        'maint_bpm_rb_conflicts': "Vorhandene BPM mit deutlicher rekordbox-Abweichung",
        'maint_bpm_source_rb': "rekordbox XML",
        'maint_bpm_path_intro': "[cyan]Optionale lokale Pfad-Zuordnung[/cyan]\nFalls mAirList relative Speicherort-Pfade nutzt, kannst du hier Basisordner hinzufügen. Enter ohne Eingabe startet die Prüfung.",
        'maint_bpm_path_prompt': "Basis-Ordner (optional, Enter = weiter): ",
        'maint_bpm_path_added': "[green]✓ Ordner hinzugefügt:[/green] {path}",
        'maint_bpm_path_invalid': "[red]Ordner existiert nicht oder ist ungültig.[/red]",
        'maint_bpm_summary_title': "BPM-Prüfung",
        'maint_bpm_missing': "Tracks ohne BPM",
        'maint_bpm_existing': "Bereits mit BPM",
        'maint_bpm_file': "Treffer aus Datei-Tag",
        'maint_bpm_ab': "Treffer aus AcousticBrainz",
        'maint_bpm_nomatch': "Kein sicherer BPM-Treffer",
        'maint_bpm_errors': "API-/Lesefehler",
        'maint_bpm_diag_title': "BPM-Diagnose",
        'maint_bpm_diag_kind': "Grund",
        'maint_bpm_diag_file_unreachable': "Audiodatei nicht erreichbar (Tag-Prüfung übersprungen)",
        'maint_bpm_diag_file_read': "Audiodatei/Tags nicht lesbar",
        'maint_bpm_diag_mb_nomatch': "MusicBrainz: kein eindeutiges Recording",
        'maint_bpm_diag_mb_network': "MusicBrainz: Netzwerk/Timeout",
        'maint_bpm_diag_mb_rate': "MusicBrainz: Rate Limit (429)",
        'maint_bpm_diag_mb_server': "MusicBrainz: Serverfehler (5xx)",
        'maint_bpm_diag_mb_http': "MusicBrainz: sonstiger HTTP-Fehler",
        'maint_bpm_diag_mb_other': "MusicBrainz: sonstiger API-Fehler",
        'maint_bpm_diag_ab_nodata': "AcousticBrainz: kein Datensatz",
        'maint_bpm_diag_ab_nobpm': "AcousticBrainz: Datensatz ohne nutzbares BPM",
        'maint_bpm_diag_ab_ambiguous': "AcousticBrainz: kein sicherer BPM-Konsens",
        'maint_bpm_diag_ab_network': "AcousticBrainz: Netzwerk/Timeout",
        'maint_bpm_diag_ab_rate': "AcousticBrainz: Rate Limit (429)",
        'maint_bpm_diag_ab_server': "AcousticBrainz: Serverfehler (5xx)",
        'maint_bpm_diag_ab_http': "AcousticBrainz: sonstiger HTTP-Fehler",
        'maint_bpm_diag_ab_other': "AcousticBrainz: sonstiger API-Fehler",
        'maint_bpm_review_saved': "[green]✓ Vollständige BPM-Review-Liste gespeichert: {path}[/green]",
        'maint_bpm_preview': "Gefundene BPM-Vorschläge",
        'maint_bpm_source_file': "Datei-Tag",
        'maint_bpm_source_ab': "AcousticBrainz ({agree}/{total})",
        'maint_bpm_nochange': "[yellow]Keine fehlenden BPM konnten sicher ergänzt werden. Es wurde nichts geschrieben.[/yellow]",
        'maint_bpm_confirm': "{count} BPM-Wert(e) in die Datenbank schreiben? [j/N]: ",
        'maint_bpm_cancel': "[yellow]BPM-Übernahme abgebrochen. Die Datenbank wurde nicht verändert.[/yellow]",
        'maint_bpm_done': "[bold green]✓ BPM ergänzt:[/bold green] {written} Wert(e) geschrieben, {skipped} inzwischen vorhandene BPM übersprungen.",
        'maint_dup_scan': "[cyan]Prüfe die Datenbank auf aktuelle Dopplungs-Kandidaten...[/cyan]",
        'maint_dup_summary_title': "Dopplungsprüfung",
        'maint_dup_groups': "Gefundene Gruppen",
        'maint_dup_items': "Betroffene Elemente",
        'maint_dup_new': "Neu als DOPPELUNG markiert",
        'maint_dup_still': "Weiterhin markiert",
        'maint_dup_removed': "Erledigte Markierungen entfernt",
        'maint_dup_nochange': "[green]✓ Der DOPPELUNG-Status ist bereits aktuell. Es wurde nichts geschrieben.[/green]",
        'maint_dup_done': "[bold green]✓ Dopplungsstatus aktualisiert:[/bold green] {new} neu/geändert, {still} weiterhin markiert, {removed} erledigte Markierung(en) entfernt. [dim]Es wurden keine Elemente gelöscht.[/dim]",
        'maint_done_case': "[bold green]✓ Fertig! {count} Tracks (Artist/Title) korrigiert.[/bold green]",
        'maint_done_tags': "[bold green]✓ Fertig! {count} Audio-Dateien (FLAC/AIFF/MP3) wurden erfolgreich getaggt.[/bold green]",
        'std_done': "[bold green]✓ Fertig! {count} unsaubere Genres wurden erfolgreich ueberschrieben.[/bold green]",
        'maint_no_changes': "[yellow]Keine Änderungen nötig für diesen Schritt.[/yellow]"
    },
    'en': {
        'menu_copyright': "(c) 2026 by Myka Vormeng (Concept)\n           and ChatGPT (Programming)",
        'menu_title': "mAirList Database Assistant",
        'menu_db_none': "No database selected – start with option 0.",
        'menu_db_act': "Active Database:",
        'menu_opt0': "Select or change the database copy",
        'menu_desc0': "Choose the .mldb copy the Restorer should work with.",
        'menu_h1': "--- STEP 1: SEARCH FOR METADATA ---",
        'menu_opt1': "Search new/unprocessed tracks",
        'menu_desc1': "Fetches suggestions in batches of 50; resumable at any time.",
        'menu_opt2': "Search all pending tracks without pauses",
        'menu_desc2': "Same as option 1, but runs to the end – ideal overnight.",
        'menu_opt3': "Re-check every track from scratch",
        'menu_desc3': "Ignores the restored flag and fetches fresh suggestions for every track.",
        'menu_h2': "--- STEP 2: REVIEW SUGGESTIONS ---",
        'menu_opt4': "Review every suggestion yourself",
        'menu_desc4': "Inspect each found value and accept, keep the original, or edit it.",
        'menu_opt5': "Review with automatic assistance",
        'menu_desc5': "Auto-accepts safe Year/Genre matches; everything else stays reviewable.",
        'menu_h3': "--- OPTIONAL: MAINTAIN DATABASE / FILES ---",
        'menu_opt6': "Open maintenance tools",
        'menu_desc6': "Clean genres/text, mark duplicate candidates, or write verified audio tags.",
        'menu_h4': "--- STEP 3: SAVE VERIFIED CHANGES ---",
        'menu_opt7': "Write verified changes to the database copy",
        'menu_desc7': "Shows a summary first, creates a backup, then writes the changes.",
        'menu_opt8': "Change Language / Sprache ändern",
        'menu_opt9': "Exit program",
        'menu_workflow': "Recommended workflow: 1 search → 4/5 review → 7 save",
        'menu_prompt': "Choice [0-9]:",
        'menu_err': "Invalid choice. Please try again.",
        'menu_err_db': "Error: No database selected! Please choose Option 0 first.",
        'db_invalid_file': "Error: The selected file is not a readable mAirList .mldb database, or its schema version could not be determined.",
        'db_read_error': "The mAirList database could not be read completely: {details}",
        'db_incompatible': "Incompatible database!\n\nSchema version: [bold yellow]{version}[/bold yellow]\nSupported: [bold green]{supported}[/bold green]\nRestorer version: {app_version}",
        'menu_path_hint1': "Note: Please provide the path to a COPY of your database.",
        'menu_path_hint2': "(Tip: Just drag and drop the .mldb file into this window and press Enter)",
        'menu_path_prompt': "Path: ",
        'menu_warn_full': "WARNING: This will re-fetch ALL tracks, including already processed ones.",
        'menu_sure': "Really continue? [y/N]: ",
        'menu_warn_apply1': "WARNING: This operation writes all verified values to the",
        'menu_warn_apply2': "selected .mldb file. ALWAYS USE A COPY for this!",
        'menu_continue': "Press Enter to return to the main menu...",
        'setup_title': "[bold cyan]Initial Setup: API Credentials[/bold cyan]\nDetails are stored locally in the 'Data' folder (Base64-obfuscated, not encrypted).",
        'setup_discogs': "[bold yellow]-- Discogs API --[/bold yellow]",
        'setup_mb': "\n[bold yellow]-- MusicBrainz Contact --[/bold yellow]",
        'setup_email': "  Your Contact Email: ",
        'setup_email_err': "[red]Invalid email address, please try again.[/red]",
        'setup_saved': "[green]✓ Credentials stored locally in '{config_file}'.[/green]\n",
        'ign_current': "\n[cyan]Current folder exceptions for this DB:[/cyan] [yellow]{liste}[/yellow]",
        'ign_reset': "Do you want to recreate this list? [y/N]: ",
        'ign_none': "None",
        'ign_setup_title': "\n[bold cyan]Configure folder exceptions for this database[/bold cyan]\nSpecify folders to be skipped during fetch (e.g., Jingles, News).",
        'ign_prompt': "  [cyan]Drag & Drop folder here[/cyan] OR type [cyan]virtual folder name[/cyan] (Enter = Done): ",
        'ign_added_phys': "  [green]✓ Physical path ignored:[/green] {path}",
        'ign_added_virt': "  [green]✓ Virtual/Partial folder ignored:[/green] {name}",
        'ign_saved': "[green]✓ Exceptions for this DB saved![/green]\n",
        'ign_skip_count': "\n[bold green]✓ SUCCESS: Skipped {count} ignored elements (OAD/Jingles/News etc.)![/bold green]",
        'fetch_load_prog': "[cyan]Progress loaded from '{csv}' ({count} rows).[/cyan]",
        'fetch_sync_del': "[yellow]-> {count} track(s) were deleted in mAirList and removed from CSV.[/yellow]",
        'fetch_new_tracks': "[green]-> Added {count} new track(s) from '{db}'.[/green]",
        'fetch_reset': "[yellow]-> {count} track(s) reset in mAirList – will be re-fetched![/yellow]",
        'fetch_first': "[cyan]First run: Reading directly from SQLite copy '{db}'.[/cyan]",
        'fetch_bpm_rb_prompt': "rekordbox XML for BPM (optional; Enter = {default}, '-' = no XML): ",
        'fetch_bpm_rb_none': "no XML",
        'fetch_bpm_rb_missing': "[yellow]rekordbox XML not found: {path} – Fetch continues with file tags/API fallback.[/yellow]",
        'fetch_bpm_rb_invalid': "[yellow]rekordbox XML could not be read ({details}) – Fetch continues with file tags/API fallback.[/yellow]",
        'fetch_bpm_rb_loaded': "[green]✓ BPM source rekordbox XML:[/green] {entries} entries, {valid} with valid BPM.",
        'fetch_full': "[bold yellow]Full re-check requested (--full)[/bold yellow]",
        'fetch_start': "[bold green]Starting automatic fetch[/bold green]\nPending tracks: [bold yellow]{offen}[/bold yellow] of [bold]{total}[/bold] total",
        'fetch_done_already': "[bold green]✓ All tracks are already up to date![/bold green]",
        'fetch_progress': "[bold magenta]Fetching metadata...",
        'fetch_track_info': "  [dim]ID {id}:[/dim] [bold]{art} - {tit}[/bold] (Year: [bold cyan]{jahr}[/bold cyan], Confidence: [{c_color}]{conf}[/{c_color}])",
        'fetch_track_retry': "[bold yellow]⚠ ID {id}: temporary API/network error – automatic retry {retry}/{max_retry} in {delay} s.[/bold yellow]",
        'fetch_track_error': "[bold yellow]⚠ ID {id}: API/network error persisted after automatic retries. Track stays pending and will be retried on the next fetch.[/bold yellow]",
        'fetch_done_with_errors': "\n[bold yellow]⚠ Fetch finished, but {count} track(s) still could not be completed after automatic retries because of API/network errors. They remain pending and will be retried on the next fetch.[/bold yellow]",
        'fetch_interrupt': "\n[bold yellow]Fetch interrupted. Progress safely saved.[/bold yellow]",
        'fetch_success': "\n[bold green]✓ Fetch completed successfully![/bold green] Next step: [bold cyan]Option [4] or [5] in the main menu (Review)[/bold cyan]",
        'fetch_paused_review': "\n[bold cyan]Fetch paused after this batch.[/bold cyan] You can review the loaded tracks with option 4 or 5 now. Option 1 resumes the fetch later.",
        'fetch_chunk_pause': "\n[bold yellow]☕ {count} tracks fetched![/bold yellow]\nDo you want to review them now?\n[dim]Tip: You can safely resume the fetch process later from the main menu (Option 1).[/dim]",
        'fetch_chunk_prompt': "Type [cyan]'r'[/cyan] for Review or [green]Enter[/green] for the next 50 tracks: ",
        'err_file_not_found': "[bold red][Error][/bold red] '{file}' not found.",
        'err_need_fetch': " Run 'fetch' first.",
        'rev_mode': "[bold cyan]Review Mode[/bold cyan]\nPending reviews: [bold yellow]{todo}[/bold yellow]{auto}\n[dim]Tip: Type '<' or 'b' and Enter to go back one track![/dim]",
        'rev_auto_active': "\n[green]--auto-hoch active[/green]",
        'rev_row': "[bold white on blue] Row {row} (ID: {id}) [/bold white on blue] [bold]{art} - {tit}[/bold]",
        'rev_artist': "  [cyan]Artist[/cyan] -> Suggestion: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Suggest / [yellow]o[/yellow]=Orig / Text][/dim]: ",
        'rev_title': "  [cyan]Title[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Suggest / [yellow]o[/yellow]=Orig / Text][/dim]: ",
        'rev_refetch': "  [magenta]⚡ Custom text detected! Live re-fetch for '{art} - {tit}'...[/magenta]",
        'rev_year_auto': "  [cyan]Year[/cyan]   -> [bold green]{sugg}[/bold green] [dim](auto, Orig: '{orig}')[/dim]",
        'rev_year': "  [cyan]Year[/cyan]   -> Suggestion: '[bold green]{sugg}[/bold green]' ({badge}) [dim](Orig: '{orig}') \\[[green]Enter[/green]=Suggest / [yellow]o[/yellow]=Orig / Year][/dim]: ",
        'rev_genre_auto': "  [cyan]Genre[/cyan]  -> [bold green]{sugg}[/bold green] [dim](auto, Orig: '{orig}')[/dim]",
        'rev_genre': "  [cyan]Genre[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Suggest / [yellow]o[/yellow]=Orig / {hint}][/dim]: ",
        'rev_album': "  [cyan]Album[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Suggest / [yellow]o[/yellow]=Orig / Text][/dim]: ",
        'rev_label': "  [cyan]Label[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Suggest / [yellow]o[/yellow]=Orig / Text][/dim]: ",
        'rev_lang':  "  [cyan]Lang.[/cyan]  -> Suggestion: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Suggest / [yellow]o[/yellow]=Orig / {hint}][/dim]: ",
        'rev_bpm_auto': "  [cyan]BPM[/cyan]     -> [bold green]{sugg}[/bold green] [dim](automatic from {source}; existing BPM is protected)[/dim]",
        'no_sugg': "- (No suggestion) -",
        'rev_interim': "[dim]  (Intermediate progress saved)[/dim]",
        'rev_interrupt': "\n\n[bold yellow]Review interrupted. Previous decisions are saved.[/bold yellow]",
        'rev_success': "\n[bold green]✓ Review completed![/bold green] Final result in [bold cyan]'{csv}'[/bold cyan]. Next step: [bold cyan]Option [7] in the main menu (Apply)[/bold cyan]",
        'err_need_fetch_rev': " Run 'fetch' and 'review' first.",
        'apply_warn': "[bold red]WARNING: Write operation to .mldb file[/bold red]\nNever apply to a file currently open in mAirList!",
        'apply_locked': "[bold red]Database is currently locked![/bold red]\nmAirList (or another program) likely has this file\nopen right now. Close the program or select a true\ncopy of the file and try again.",
        'apply_confirm': "Is this definitely a COPY? Type '[bold green]YES[/bold green]' to continue: ",
        'apply_confirm_word': "YES",
        'apply_abort': "[yellow]Aborted.[/yellow]",
        'apply_backup': "[green]✓ Backup created: {path}[/green]",
        'apply_backup_clean': "[dim]✓ Cleaned up old backups (keeping the latest 5).[/dim]",
        'apply_err_lock': "\n[bold red][Error] Database locked / Access denied:[/bold red] {err}",
        'apply_success': "\n[bold green]✓ Done! {count} row(s) in '{db}' successfully updated.[/bold green]",
        'apply_no_new': "\n[yellow]No new data to apply. (All entries in the CSV are already marked as 'RESTAURIERT' in the database).[/yellow]",
        'apply_integrity_check': "[cyan]Checking database integrity...[/cyan]",
        'apply_integrity_ok': "[green]✓ Database integrity: OK[/green]",
        'apply_integrity_fail': "[bold red]⛔ Database integrity check failed:[/bold red] {details}\nNo changes will be written.\n\n[dim]Note: The inconsistency already existed before this write operation; the Restorer has not changed anything. Messages such as 'wrong # of entries in index ...' usually concern SQLite indexes. The Restorer deliberately does not repair such database structures automatically.[/dim]",
        'apply_integrity_after_fail': "[bold red]⛔ WARNING: Integrity check failed after writing![/bold red]\nBackup: {backup}\nDetails: {details}",
        'apply_summary_title': "Changes before saving",
        'apply_summary_field': "Field",
        'apply_summary_count': "Changes",
        'apply_summary_total': "Verified tracks to be written",
        'apply_summary_force': "Deliberately re-checked via Full Fetch",
        'apply_summary_restored': "Tracks will be marked RESTAURIERT",
        'conf_hoch': "high", 'conf_mittel': "medium", 'conf_niedrig': "low",
        'maint_title': "\n[bold cyan]=== MAINTENANCE MENU ===[/bold cyan]",
        'maint_warn': "[bold red]WARNING: MAINTENANCE CAN MODIFY THE DATABASE OR AUDIO FILES DIRECTLY![/bold red]\nUse a database copy and back up files before running the tagger.",
        'maint_opt1': "  [[green]1[/green]] Standardize Genres",
        'maint_opt2': "  [[green]2[/green]] Fix Case & Apostrophes (Artist/Title)",
        'maint_opt3': "  [[green]3[/green]] File tagger + mAirList metadata backup",
        'maint_opt4': "  [[green]4[/green]] Execute ALL maintenance tasks (1-2) sequentially",
        'maint_opt5': "  [[green]5[/green]] Mark duplicate candidates / refresh status",
        'maint_opt6': "  [[green]6[/green]] Fill missing BPM (rekordbox XML / file tags / MusicBrainz + AcousticBrainz)",
        'maint_opt0': "  [[green]0[/green]] Back / Cancel",
        'maint_prompt': "Choice [0-6]: ",
        'tagger_mode_title': "[bold cyan]File tagger[/bold cyan]",
        'tagger_mode_desc': "[dim]1 writes portable audio tags only. 2 also backs up mAirList cues, level analysis and normalization (embedded in MP3/AIFF, .mmd sidecar for FLAC/Ogg).[/dim]",
        'tagger_mode_prompt': "Mode [1=Tags / 2=Tags+mAirList / 0=Cancel]: ",
        'tagger_mode_invalid': "[red]Please choose 0, 1 or 2.[/red]",
        'tagger_path_intro': "[cyan]=== Local path mapping ===[/cyan]\nBecause mAirList uses Storage Locations, the DB may contain relative paths. Add local base folders; press Enter to start.",
        'tagger_path_prompt': "Base folder (optional, Enter = start): ",
        'tagger_path_added': "[green]✓ Folder added:[/green] {path}",
        'tagger_path_invalid': "[red]Folder does not exist or is invalid.[/red]",
        'tagger_working': "[magenta]Reading files and writing tags...[/magenta]",
        'tagger_diag_title': "Tagger diagnostics",
        'tagger_diag_total': "Database tracks with a path",
        'tagger_diag_missing': "Paths/files not found",
        'tagger_diag_unsupported': "Unsupported format",
        'tagger_diag_perfect': "Tags/metadata already perfect",
        'tagger_diag_updated': "Files successfully updated",
        'tagger_diag_embedded': "mAirList blocks embedded",
        'tagger_diag_sidecar': "mAirList .mmd written/updated",
        'maint_bpm_intro': "[cyan]Searching for missing BPM values...[/cyan]\n[dim]Existing BPM values are never overwritten. Priority: rekordbox XML by exact file path, then file tag, then MusicBrainz + AcousticBrainz as fallback.[/dim]",
        'maint_bpm_rb_prompt': "rekordbox XML (optional, Enter = no XML): ",
        'maint_bpm_rb_invalid': "[red]rekordbox XML was not found or is invalid.[/red]",
        'maint_bpm_rb_loaded': "[green]✓ rekordbox XML loaded:[/green] {entries} entries, {valid} with valid BPM.",
        'maint_bpm_rb': "Matches from rekordbox XML",
        'maint_bpm_rb_unmatched': "Not filled from rekordbox (fallback)",
        'maint_bpm_rb_conflicts': "Existing BPM with material rekordbox difference",
        'maint_bpm_source_rb': "rekordbox XML",
        'maint_bpm_path_intro': "[cyan]Optional local path mapping[/cyan]\nIf mAirList uses relative storage-location paths, add base folders here. Press Enter with no input to start.",
        'maint_bpm_path_prompt': "Base folder (optional, Enter = continue): ",
        'maint_bpm_path_added': "[green]✓ Folder added:[/green] {path}",
        'maint_bpm_path_invalid': "[red]Folder does not exist or is invalid.[/red]",
        'maint_bpm_summary_title': "BPM scan",
        'maint_bpm_missing': "Tracks without BPM",
        'maint_bpm_existing': "Already have BPM",
        'maint_bpm_file': "Matches from file tags",
        'maint_bpm_ab': "Matches from AcousticBrainz",
        'maint_bpm_nomatch': "No safe BPM match",
        'maint_bpm_errors': "API/read errors",
        'maint_bpm_diag_title': "BPM diagnostics",
        'maint_bpm_diag_kind': "Reason",
        'maint_bpm_diag_file_unreachable': "Audio file unavailable (tag check skipped)",
        'maint_bpm_diag_file_read': "Audio file/tags unreadable",
        'maint_bpm_diag_mb_nomatch': "MusicBrainz: no unambiguous recording",
        'maint_bpm_diag_mb_network': "MusicBrainz: network/timeout",
        'maint_bpm_diag_mb_rate': "MusicBrainz: rate limit (429)",
        'maint_bpm_diag_mb_server': "MusicBrainz: server error (5xx)",
        'maint_bpm_diag_mb_http': "MusicBrainz: other HTTP error",
        'maint_bpm_diag_mb_other': "MusicBrainz: other API error",
        'maint_bpm_diag_ab_nodata': "AcousticBrainz: no dataset entry",
        'maint_bpm_diag_ab_nobpm': "AcousticBrainz: dataset has no usable BPM",
        'maint_bpm_diag_ab_ambiguous': "AcousticBrainz: no safe BPM consensus",
        'maint_bpm_diag_ab_network': "AcousticBrainz: network/timeout",
        'maint_bpm_diag_ab_rate': "AcousticBrainz: rate limit (429)",
        'maint_bpm_diag_ab_server': "AcousticBrainz: server error (5xx)",
        'maint_bpm_diag_ab_http': "AcousticBrainz: other HTTP error",
        'maint_bpm_diag_ab_other': "AcousticBrainz: other API error",
        'maint_bpm_review_saved': "[green]✓ Complete BPM review list saved: {path}[/green]",
        'maint_bpm_preview': "BPM proposals found",
        'maint_bpm_source_file': "File tag",
        'maint_bpm_source_ab': "AcousticBrainz ({agree}/{total})",
        'maint_bpm_nochange': "[yellow]No missing BPM values could be filled safely. Nothing was written.[/yellow]",
        'maint_bpm_confirm': "Write {count} BPM value(s) to the database? [y/N]: ",
        'maint_bpm_cancel': "[yellow]BPM write cancelled. The database was not changed.[/yellow]",
        'maint_bpm_done': "[bold green]✓ BPM updated:[/bold green] {written} value(s) written, {skipped} BPM value(s) that appeared meanwhile were skipped.",
        'maint_dup_scan': "[cyan]Scanning the database for current duplicate candidates...[/cyan]",
        'maint_dup_summary_title': "Duplicate scan",
        'maint_dup_groups': "Candidate groups found",
        'maint_dup_items': "Affected items",
        'maint_dup_new': "Newly marked DOPPELUNG",
        'maint_dup_still': "Still marked",
        'maint_dup_removed': "Resolved flags removed",
        'maint_dup_nochange': "[green]✓ The DOPPELUNG status is already current. Nothing was written.[/green]",
        'maint_dup_done': "[bold green]✓ Duplicate status updated:[/bold green] {new} new/changed, {still} still marked, {removed} resolved flag(s) removed. [dim]No items were deleted.[/dim]",
        'maint_done_case': "[bold green]✓ Done! Corrected {count} tracks (Artist/Title).[/bold green]",
        'maint_done_tags': "[bold green]✓ Done! Successfully tagged {count} audio files (FLAC/AIFF/MP3).[/bold green]",
        'std_done': "[bold green]✓ Done! {count} unstandardized genres successfully updated.[/bold green]",
        'maint_no_changes': "[yellow]No changes needed.[/yellow]"
    },
    'nl': {
        'menu_copyright': "(c) 2026 by Myka Vormeng (Concept)\n           and ChatGPT (Programming)",
        'menu_title': "mAirList Database Assistent",
        'menu_db_none': "Geen database geselecteerd – begin met optie 0.",
        'menu_db_act': "Actieve database:",
        'menu_opt0': "Databasekopie selecteren of wijzigen",
        'menu_desc0': "Kies de .mldb-kopie waarmee de Restorer moet werken.",
        'menu_h1': "--- STAP 1: METADATA ZOEKEN ---",
        'menu_opt1': "Nieuwe/onbewerkte tracks zoeken",
        'menu_desc1': "Haalt suggesties op in blokken van 50; altijd hervatbaar.",
        'menu_opt2': "Alle openstaande tracks zonder pauze zoeken",
        'menu_desc2': "Zoals optie 1, maar loopt tot het einde door – ideaal 's nachts.",
        'menu_opt3': "Alle tracks volledig opnieuw controleren",
        'menu_desc3': "Negeert de hersteld-status en haalt voor elke track nieuwe suggesties op.",
        'menu_h2': "--- STAP 2: SUGGESTIES CONTROLEREN ---",
        'menu_opt4': "Alle suggesties zelf controleren",
        'menu_desc4': "Bekijk elke gevonden waarde en accepteer, behoud of wijzig deze.",
        'menu_opt5': "Controle met automatische hulp",
        'menu_desc5': "Accepteert veilige Jaar/Genre-matches automatisch; de rest blijft controleerbaar.",
        'menu_h3': "--- OPTIONEEL: DATABASE / BESTANDEN ONDERHOUDEN ---",
        'menu_opt6': "Onderhoudstools openen",
        'menu_desc6': "Genres/tekst opschonen, dubbelen markeren of gecontroleerde audiotags schrijven.",
        'menu_h4': "--- STAP 3: GECONTROLEERDE WIJZIGINGEN OPSLAAN ---",
        'menu_opt7': "Gecontroleerde wijzigingen naar de databasekopie schrijven",
        'menu_desc7': "Toont eerst een overzicht, maakt een back-up en schrijft daarna.",
        'menu_opt8': "Taal wijzigen / Change Language",
        'menu_opt9': "Programma afsluiten",
        'menu_workflow': "Aanbevolen volgorde: 1 zoeken → 4/5 controleren → 7 opslaan",
        'menu_prompt': "Keuze [0-9]:",
        'menu_err': "Ongeldige keuze. Probeer het opnieuw.",
        'menu_err_db': "Fout: Geen database geselecteerd! Kies eerst optie 0.",
        'db_invalid_file': "Fout: Het geselecteerde bestand is geen leesbare mAirList-.mldb-database, of de schemaversie kon niet worden bepaald.",
        'db_read_error': "De mAirList-database kon niet volledig worden gelezen: {details}",
        'db_incompatible': "Incompatibele database!\n\nSchemaversie: [bold yellow]{version}[/bold yellow]\nOndersteund: [bold green]{supported}[/bold green]\nRestorer-versie: {app_version}",
        'menu_path_hint1': "Let op: Geef het pad op naar een KOPIE van je database.",
        'menu_path_hint2': "(Tip: Sleep het .mldb bestand gewoon in dit venster en druk op Enter)",
        'menu_path_prompt': "Pad: ",
        'menu_warn_full': "WAARSCHUWING: Dit haalt ALLE tracks opnieuw op, inclusief reeds verwerkte tracks.",
        'menu_sure': "Weet je het zeker? [j/N]: ",
        'menu_warn_apply1': "WAARSCHUWING: Dit proces schrijft alle gecontroleerde waarden naar het",
        'menu_warn_apply2': "bovenstaande .mldb bestand. Gebruik hiervoor ALTIJD EEN KOPIE!",
        'menu_continue': "Druk op Enter om terug te keren naar het hoofdmenu...",
        'setup_title': "[bold cyan]Eerste installatie: API-gegevens[/bold cyan]\nGegevens worden lokaal opgeslagen in de map 'Data'.",
        'setup_discogs': "[bold yellow]-- Discogs API --[/bold yellow]",
        'setup_mb': "\n[bold yellow]-- MusicBrainz Contact --[/bold yellow]",
        'setup_email': "  Jouw contact e-mail: ",
        'setup_email_err': "[red]Ongeldig e-mailadres, probeer het opnieuw.[/red]",
        'setup_saved': "[green]✓ Inloggegevens lokaal opgeslagen in '{config_file}'.[/green]\n",
        'ign_current': "\n[cyan]Huidige map-uitzonderingen voor deze DB:[/cyan] [yellow]{liste}[/yellow]",
        'ign_reset': "Wil je deze lijst opnieuw aanmaken? [j/N]: ",
        'ign_none': "Geen",
        'ign_setup_title': "\n[bold cyan]Map-uitzonderingen configureren[/bold cyan]\nGeef mappen op die genegeerd moeten worden (bijv. Jingles, News).",
        'ign_prompt': "  [cyan]Sleep map hierheen[/cyan] OF typ [cyan]virtuele mapnaam[/cyan] (Enter = Klaar): ",
        'ign_added_phys': "  [green]✓ Fysiek pad genegeerd:[/green] {path}",
        'ign_added_virt': "  [green]✓ Virtuele/gedeeltelijke map genegeerd:[/green] {name}",
        'ign_saved': "[green]✓ Uitzonderingen opgeslagen in config.json![/green]\n",
        'ign_skip_count': "\n[bold green]✓ SUCCES: {count} genegeerde elementen (OAD/Jingles/News) succesvol overgeslagen![/bold green]",
        'fetch_load_prog': "[cyan]Voortgang geladen uit '{csv}' ({count} rijen).[/cyan]",
        'fetch_sync_del': "[yellow]-> {count} track(s) zijn verwijderd in mAirList en uit CSV gehaald.[/yellow]",
        'fetch_new_tracks': "[green]-> {count} nieuwe track(s) uit '{db}' toegevoegd.[/green]",
        'fetch_reset': "[yellow]-> {count} track(s) gereset in mAirList – worden opnieuw opgehaald![/yellow]",
        'fetch_first': "[cyan]Eerste run: Lezen direct uit SQLite-kopie '{db}'.[/cyan]",
        'fetch_bpm_rb_prompt': "rekordbox XML voor BPM (optioneel; Enter = {default}, '-' = zonder XML): ",
        'fetch_bpm_rb_none': "zonder XML",
        'fetch_bpm_rb_missing': "[yellow]rekordbox XML niet gevonden: {path} – Fetch gaat verder met bestandstags/API-fallback.[/yellow]",
        'fetch_bpm_rb_invalid': "[yellow]rekordbox XML kon niet worden gelezen ({details}) – Fetch gaat verder met bestandstags/API-fallback.[/yellow]",
        'fetch_bpm_rb_loaded': "[green]✓ BPM-bron rekordbox XML:[/green] {entries} items, {valid} met geldige BPM.",
        'fetch_full': "[bold yellow]Volledige hercontrole aangevraagd (--full)[/bold yellow]",
        'fetch_start': "[bold green]Start automatische fetch[/bold green]\nOpenstaande tracks: [bold yellow]{offen}[/bold yellow] van [bold]{total}[/bold] totaal",
        'fetch_done_already': "[bold green]✓ Alle tracks zijn al up-to-date![/bold green]",
        'fetch_progress': "[bold magenta]Metadata ophalen...",
        'fetch_track_info': "  [dim]ID {id}:[/dim] [bold]{art} - {tit}[/bold] (Jaar: [bold cyan]{jahr}[/bold cyan], Betrouwbaarheid: [{c_color}]{conf}[/{c_color}])",
        'fetch_track_retry': "[bold yellow]⚠ ID {id}: tijdelijke API-/netwerkfout – automatische herpoging {retry}/{max_retry} over {delay} s.[/bold yellow]",
        'fetch_track_error': "[bold yellow]⚠ ID {id}: API-/netwerkfout bleef bestaan na automatische herpogingen. Track blijft open en wordt bij de volgende fetch opnieuw geprobeerd.[/bold yellow]",
        'fetch_done_with_errors': "\n[bold yellow]⚠ Ophalen voltooid, maar {count} track(s) konden ondanks automatische herpogingen door API-/netwerkfouten niet worden afgerond. Ze blijven open en worden bij de volgende fetch opnieuw geprobeerd.[/bold yellow]",
        'fetch_interrupt': "\n[bold yellow]Ophalen onderbroken. Voortgang veilig opgeslagen.[/bold yellow]",
        'fetch_success': "\n[bold green]✓ Fetch succesvol voltooid![/bold green] Volgende stap: [bold cyan]Optie [4] of [5] in het hoofdmenu (Review)[/bold cyan]",
        'fetch_paused_review': "\n[bold cyan]Ophalen na dit blok gepauzeerd.[/bold cyan] Je kunt de geladen tracks nu met optie 4 of 5 controleren. Optie 1 hervat het ophalen later.",
        'fetch_chunk_pause': "\n[bold yellow]☕ {count} tracks opgehaald![/bold yellow]\nWil je deze nu controleren (Review)?\n[dim]Tip: Je kunt de fetch later altijd hervatten via optie 1 in het hoofdmenu.[/dim]",
        'fetch_chunk_prompt': "Typ [cyan]'r'[/cyan] voor Review of [green]Enter[/green] voor de volgende 50 tracks: ",
        'err_file_not_found': "[bold red][Fout][/bold red] '{file}' niet gevonden.",
        'err_need_fetch': " Voer eerst 'fetch' uit.",
        'rev_mode': "[bold cyan]Review Modus[/bold cyan]\nOpenstaande controles: [bold yellow]{todo}[/bold yellow]{auto}\n[dim]Tip: Typ '<' of 'b' en Enter om een track terug te gaan![/dim]",
        'rev_auto_active': "\n[green]--auto-hoch actief[/green]",
        'rev_row': "[bold white on blue] Rij {row} (ID: {id}) [/bold white on blue] [bold]{art} - {tit}[/bold]",
        'rev_artist': "  [cyan]Artiest[/cyan] -> Suggestie: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Sugg / [yellow]o[/yellow]=Orig / Tekst][/dim]: ",
        'rev_title': "  [cyan]Titel[/cyan]   -> Suggestie: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Sugg / [yellow]o[/yellow]=Orig / Tekst][/dim]: ",
        'rev_refetch': "  [magenta]⚡ Eigen tekst gedetecteerd! Live Re-Fetch voor '{art} - {tit}'...[/magenta]",
        'rev_year_auto': "  [cyan]Jaar[/cyan]    -> [bold green]{sugg}[/bold green] [dim](auto, Orig: '{orig}')[/dim]",
        'rev_year': "  [cyan]Jaar[/cyan]    -> Suggestie: '[bold green]{sugg}[/bold green]' ({badge}) [dim](Orig: '{orig}') \\[[green]Enter[/green]=Sugg / [yellow]o[/yellow]=Orig / Jaar][/dim]: ",
        'rev_genre_auto': "  [cyan]Genre[/cyan]   -> [bold green]{sugg}[/bold green] [dim](auto, Orig: '{orig}')[/dim]",
        'rev_genre': "  [cyan]Genre[/cyan]   -> Suggestie: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Sugg / [yellow]o[/yellow]=Orig / {hint}][/dim]: ",
        'rev_album': "  [cyan]Album[/cyan]   -> Suggestie: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Sugg / [yellow]o[/yellow]=Orig / Tekst][/dim]: ",
        'rev_label': "  [cyan]Label[/cyan]   -> Suggestie: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Sugg / [yellow]o[/yellow]=Orig / Tekst][/dim]: ",
        'rev_lang':  "  [cyan]Taal[/cyan]    -> Suggestie: '[bold green]{sugg}[/bold green]' [dim](Orig: '{orig}') \\[[green]Enter[/green]=Sugg / [yellow]o[/yellow]=Orig / {hint}][/dim]: ",
        'rev_bpm_auto': "  [cyan]BPM[/cyan]     -> [bold green]{sugg}[/bold green] [dim](automatisch uit {source}; bestaande BPM wordt beschermd)[/dim]",
        'no_sugg': "- (Geen suggestie) -",
        'rev_interim': "[dim]  (Tussenstand opgeslagen)[/dim]",
        'rev_interrupt': "\n\n[bold yellow]Review onderbroken. Eerdere beslissingen zijn opgeslagen.[/bold yellow]",
        'rev_success': "\n[bold green]✓ Review voltooid![/bold green] Eindresultaat in [bold cyan]'{csv}'[/bold cyan]. Volgende stap: [bold cyan]Optie [7] in het hoofdmenu (Opslaan)[/bold cyan]",
        'err_need_fetch_rev': " Voer eerst 'fetch' en 'review' uit.",
        'apply_warn': "[bold red]WAARSCHUWING: Schrijfactie naar .mldb bestand[/bold red]\nNooit toepassen op een bestand dat momenteel open is in mAirList!",
        'apply_locked': "[bold red]Database is momenteel vergrendeld![/bold red]\nWaarschijnlijk heeft mAirList (of een ander programma) dit bestand\nmomenteel geopend. Sluit het programma of selecteer een echte\nkopie van het bestand en probeer het opnieuw.",
        'apply_confirm': "Is dit definitief een KOPIE? Typ '[bold green]JA[/bold green]' om door te gaan: ",
        'apply_confirm_word': "JA",
        'apply_abort': "[yellow]Geannuleerd.[/yellow]",
        'apply_backup': "[green]✓ Back-up aangemaakt: {path}[/green]",
        'apply_backup_clean': "[dim]✓ Oude back-ups opgeschoond (de laatste 5 zijn bewaard).[/dim]",
        'apply_err_lock': "\n[bold red][Fout] Database vergrendeld / Toegang geweigerd:[/bold red] {err}",
        'apply_success': "\n[bold green]✓ Klaar! {count} rij(en) in '{db}' succesvol bijgewerkt.[/bold green]",
        'apply_no_new': "\n[yellow]Geen nieuwe gegevens om op te slaan. (Alle vermeldingen in de CSV zijn al gemarkeerd als 'RESTAURIERT' in de database).[/yellow]",
        'apply_integrity_check': "[cyan]Database-integriteit controleren...[/cyan]",
        'apply_integrity_ok': "[green]✓ Database-integriteit: OK[/green]",
        'apply_integrity_fail': "[bold red]⛔ Database-integriteitscontrole mislukt:[/bold red] {details}\nEr worden geen wijzigingen geschreven.\n\n[dim]Opmerking: De inconsistentie bestond al vóór deze schrijfactie; de Restorer heeft niets gewijzigd. Meldingen zoals 'wrong # of entries in index ...' hebben doorgaans betrekking op SQLite-indexen. De Restorer herstelt zulke databasestructuren bewust niet automatisch.[/dim]",
        'apply_integrity_after_fail': "[bold red]⛔ WAARSCHUWING: Integriteitscontrole na het schrijven mislukt![/bold red]\nBack-up: {backup}\nDetails: {details}",
        'apply_summary_title': "Wijzigingen vóór opslaan",
        'apply_summary_field': "Veld",
        'apply_summary_count': "Wijzigingen",
        'apply_summary_total': "Gecontroleerde tracks die worden geschreven",
        'apply_summary_force': "Bewust volledig opnieuw gecontroleerd (Full Fetch)",
        'apply_summary_restored': "Tracks worden als RESTAURIERT gemarkeerd",
        'conf_hoch': "hoog", 'conf_mittel': "gemiddeld", 'conf_niedrig': "laag",
        'maint_title': "\n[bold cyan]=== ONDERHOUDSMENU ===[/bold cyan]",
        'maint_warn': "[bold red]WAARSCHUWING: ONDERHOUD KAN DE DATABASE OF AUDIOBESTANDEN DIRECT WIJZIGEN![/bold red]\nGebruik een databasekopie en maak een bestandsback-up vóór de tagger.",
        'maint_opt1': "  [[green]1[/green]] Genres standaardiseren",
        'maint_opt2': "  [[green]2[/green]] Hoofdletters/kleine letters & apostrofs corrigeren (Artist/Title)",
        'maint_opt3': "  [[green]3[/green]] Bestandstagger + mAirList-metadataback-up",
        'maint_opt4': "  [[green]4[/green]] ALLE onderhoudstaken (1-2) achter elkaar uitvoeren",
        'maint_opt5': "  [[green]5[/green]] Dubbele kandidaten markeren / status bijwerken",
        'maint_opt6': "  [[green]6[/green]] Ontbrekende BPM aanvullen (rekordbox XML / bestandstags / MusicBrainz + AcousticBrainz)",
        'maint_opt0': "  [[green]0[/green]] Terug / Annuleren",
        'maint_prompt': "Keuze [0-6]: ",
        'tagger_mode_title': "[bold cyan]Bestandstagger[/bold cyan]",
        'tagger_mode_desc': "[dim]1 schrijft alleen draagbare audiotags. 2 maakt daarnaast een back-up van mAirList-cues, niveaumeting en normalisatie (ingebed in MP3/AIFF, .mmd naast FLAC/Ogg).[/dim]",
        'tagger_mode_prompt': "Modus [1=Tags / 2=Tags+mAirList / 0=Annuleren]: ",
        'tagger_mode_invalid': "[red]Kies 0, 1 of 2.[/red]",
        'tagger_path_intro': "[cyan]=== Lokale padtoewijzing ===[/cyan]\nOmdat mAirList Storage Locations gebruikt, kan de database relatieve paden bevatten. Voeg lokale basismappen toe; Enter start.",
        'tagger_path_prompt': "Basismap (optioneel, Enter = starten): ",
        'tagger_path_added': "[green]✓ Map toegevoegd:[/green] {path}",
        'tagger_path_invalid': "[red]Map bestaat niet of is ongeldig.[/red]",
        'tagger_working': "[magenta]Bestanden lezen en tags schrijven...[/magenta]",
        'tagger_diag_title': "Tagger-diagnose",
        'tagger_diag_total': "Databasetracks met pad",
        'tagger_diag_missing': "Paden/bestanden niet gevonden",
        'tagger_diag_unsupported': "Niet-ondersteund formaat",
        'tagger_diag_perfect': "Tags/metadata waren al correct",
        'tagger_diag_updated': "Bestanden succesvol bijgewerkt",
        'tagger_diag_embedded': "mAirList-blokken ingebed",
        'tagger_diag_sidecar': "mAirList .mmd geschreven/bijgewerkt",
        'maint_bpm_intro': "[cyan]Zoeken naar ontbrekende BPM-waarden...[/cyan]\n[dim]Bestaande BPM-waarden worden nooit overschreven. Prioriteit: rekordbox XML via exact bestandspad, daarna bestandstag, daarna MusicBrainz + AcousticBrainz als fallback.[/dim]",
        'maint_bpm_rb_prompt': "rekordbox XML (optioneel, Enter = zonder XML): ",
        'maint_bpm_rb_invalid': "[red]rekordbox XML is niet gevonden of ongeldig.[/red]",
        'maint_bpm_rb_loaded': "[green]✓ rekordbox XML geladen:[/green] {entries} items, {valid} met geldige BPM.",
        'maint_bpm_rb': "Treffers uit rekordbox XML",
        'maint_bpm_rb_unmatched': "Niet uit rekordbox overgenomen (fallback)",
        'maint_bpm_rb_conflicts': "Bestaande BPM met duidelijke rekordbox-afwijking",
        'maint_bpm_source_rb': "rekordbox XML",
        'maint_bpm_path_intro': "[cyan]Optionele lokale padtoewijzing[/cyan]\nAls mAirList relatieve opslaglocatiepaden gebruikt, kun je hier basismappen toevoegen. Druk Enter zonder invoer om te starten.",
        'maint_bpm_path_prompt': "Basismap (optioneel, Enter = verder): ",
        'maint_bpm_path_added': "[green]✓ Map toegevoegd:[/green] {path}",
        'maint_bpm_path_invalid': "[red]Map bestaat niet of is ongeldig.[/red]",
        'maint_bpm_summary_title': "BPM-controle",
        'maint_bpm_missing': "Tracks zonder BPM",
        'maint_bpm_existing': "Hebben al BPM",
        'maint_bpm_file': "Treffers uit bestandstag",
        'maint_bpm_ab': "Treffers uit AcousticBrainz",
        'maint_bpm_nomatch': "Geen veilige BPM-treffer",
        'maint_bpm_errors': "API-/leesfouten",
        'maint_bpm_diag_title': "BPM-diagnose",
        'maint_bpm_diag_kind': "Reden",
        'maint_bpm_diag_file_unreachable': "Audiobestand niet bereikbaar (tagcontrole overgeslagen)",
        'maint_bpm_diag_file_read': "Audiobestand/tags niet leesbaar",
        'maint_bpm_diag_mb_nomatch': "MusicBrainz: geen eenduidige opname",
        'maint_bpm_diag_mb_network': "MusicBrainz: netwerk/time-out",
        'maint_bpm_diag_mb_rate': "MusicBrainz: rate limit (429)",
        'maint_bpm_diag_mb_server': "MusicBrainz: serverfout (5xx)",
        'maint_bpm_diag_mb_http': "MusicBrainz: andere HTTP-fout",
        'maint_bpm_diag_mb_other': "MusicBrainz: andere API-fout",
        'maint_bpm_diag_ab_nodata': "AcousticBrainz: geen datasetrecord",
        'maint_bpm_diag_ab_nobpm': "AcousticBrainz: dataset zonder bruikbare BPM",
        'maint_bpm_diag_ab_ambiguous': "AcousticBrainz: geen veilige BPM-consensus",
        'maint_bpm_diag_ab_network': "AcousticBrainz: netwerk/time-out",
        'maint_bpm_diag_ab_rate': "AcousticBrainz: rate limit (429)",
        'maint_bpm_diag_ab_server': "AcousticBrainz: serverfout (5xx)",
        'maint_bpm_diag_ab_http': "AcousticBrainz: andere HTTP-fout",
        'maint_bpm_diag_ab_other': "AcousticBrainz: andere API-fout",
        'maint_bpm_review_saved': "[green]✓ Volledige BPM-reviewlijst opgeslagen: {path}[/green]",
        'maint_bpm_preview': "Gevonden BPM-voorstellen",
        'maint_bpm_source_file': "Bestandstag",
        'maint_bpm_source_ab': "AcousticBrainz ({agree}/{total})",
        'maint_bpm_nochange': "[yellow]Er konden geen ontbrekende BPM-waarden veilig worden aangevuld. Er is niets geschreven.[/yellow]",
        'maint_bpm_confirm': "{count} BPM-waarde(n) naar de database schrijven? [j/N]: ",
        'maint_bpm_cancel': "[yellow]BPM-overname geannuleerd. De database is niet gewijzigd.[/yellow]",
        'maint_bpm_done': "[bold green]✓ BPM aangevuld:[/bold green] {written} waarde(n) geschreven, {skipped} inmiddels aanwezige BPM-waarde(n) overgeslagen.",
        'maint_dup_scan': "[cyan]Database controleren op actuele dubbele kandidaten...[/cyan]",
        'maint_dup_summary_title': "Controle op dubbelen",
        'maint_dup_groups': "Gevonden kandidaatgroepen",
        'maint_dup_items': "Betrokken items",
        'maint_dup_new': "Nieuw als DOPPELUNG gemarkeerd",
        'maint_dup_still': "Nog steeds gemarkeerd",
        'maint_dup_removed': "Afgehandelde markeringen verwijderd",
        'maint_dup_nochange': "[green]✓ De DOPPELUNG-status is al actueel. Er is niets geschreven.[/green]",
        'maint_dup_done': "[bold green]✓ Dubbele status bijgewerkt:[/bold green] {new} nieuw/gewijzigd, {still} nog gemarkeerd, {removed} afgehandelde markering(en) verwijderd. [dim]Er zijn geen items verwijderd.[/dim]",
        'maint_done_case': "[bold green]✓ Klaar! {count} tracks (Artiest/Titel) gecorrigeerd.[/bold green]",
        'maint_done_tags': "[bold green]✓ Klaar! {count} audiobestanden (FLAC/AIFF/MP3) succesvol getagd.[/bold green]",
        'std_done': "[bold green]✓ Klaar! {count} ongestandaardiseerde genres succesvol bijgewerkt.[/bold green]",
        'maint_no_changes': "[yellow]Geen wijzigingen nodig.[/yellow]"
    }
}

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
    # Lyrics/Songtext are not used by the Restorer and can make session files huge.
    # Keep them untouched in mAirList, but never copy them into the CSV workspace.
    drop_names = {'lyrics', 'songtext', 'songtexte', 'song text'}
    drop_cols = [c for c in df.columns if str(c).strip().lower() in drop_names]
    out_df = df.drop(columns=drop_cols, errors='ignore')

    directory = os.path.dirname(os.path.abspath(filepath)) or '.'
    os.makedirs(directory, exist_ok=True)
    temp_path = os.path.join(directory, f".{os.path.basename(filepath)}.tmp-{os.getpid()}")

    try:
        with open(temp_path, 'w', encoding='utf-8-sig', newline='') as handle:
            out_df.to_csv(handle, index=False, quoting=csv.QUOTE_ALL)
            handle.flush()
            os.fsync(handle.fileno())
        # Atomic replacement: either the old complete file or the new complete file exists.
        os.replace(temp_path, filepath)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

def get_best_duration(dur, tot_dur):
    try:
        d1 = float(dur) if pd.notna(dur) and str(dur).strip() else 0.0
        d2 = float(tot_dur) if pd.notna(tot_dur) and str(tot_dur).strip() else 0.0
        best = max(d1, d2)
        if best > 100000:
            best = best / 10000000.0
        return best
    except:
        return 0.0

def load_language():
    global CURRENT_LANG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                saved_lang = config.get('LANG')
                if saved_lang in ['de', 'en', 'nl']:
                    CURRENT_LANG = saved_lang
                    return True
        except Exception:
            pass
    return False

def save_language(lang):
    global CURRENT_LANG
    CURRENT_LANG = lang
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception: pass
    config['LANG'] = lang
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def init_credentials():
    global DISCOGS_KEY, DISCOGS_SECRET, MB_CONTACT, HEADERS, CUSTOM_LANGS, CUSTOM_GENRES
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
    CUSTOM_GENRES = config.get('CUSTOM_GENRES', [])

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

    config_data = config.copy()
    config_data['DISCOGS_KEY'] = encode_b64(DISCOGS_KEY)
    config_data['DISCOGS_SECRET'] = encode_b64(DISCOGS_SECRET)
    config_data['MB_CONTACT'] = encode_b64(MB_CONTACT)
    config_data['DB_IGNORES'] = config.get('DB_IGNORES', {})
    config_data['CUSTOM_LANGS'] = CUSTOM_LANGS
    config_data['CUSTOM_GENRES'] = CUSTOM_GENRES
    if 'LANG' not in config_data: config_data['LANG'] = CURRENT_LANG
    
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

def add_custom_genre(genre):
    """Remember a manually entered genre for numeric Review shortcuts.

    Custom choices deliberately do not extend ALLOWED_GENRES or GENRE_SYNONYMS;
    they are a user-interface memory only.
    """
    global CUSTOM_GENRES
    value = str(genre or '').strip()
    if not value:
        return
    existing = {str(v).strip().casefold() for v in GENRE_QUICK_CHOICES + CUSTOM_GENRES}
    if value.casefold() in existing:
        return
    CUSTOM_GENRES.append(value)
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass
    config['CUSTOM_GENRES'] = CUSTOM_GENRES
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def get_genre_quick_map():
    """Return stable numeric shortcuts: 1=Rock, 2=Pop, then core/custom genres."""
    values = []
    seen = set()
    for genre in GENRE_QUICK_CHOICES + CUSTOM_GENRES:
        value = str(genre or '').strip()
        if not value or value.casefold() in seen:
            continue
        seen.add(value.casefold())
        values.append(value)
    return {str(i + 1): value for i, value in enumerate(values)}

def canonical_genre_choice(value):
    """Reuse the existing capitalization of a standard/custom quick genre when possible."""
    text = str(value or '').strip()
    if not text:
        return ''
    for genre in GENRE_QUICK_CHOICES + CUSTOM_GENRES:
        if str(genre).casefold() == text.casefold():
            return str(genre)
    return text

def get_saved_ignored_folders(db_path):
    """Return the stored ignore list for a database without prompting the user."""
    db_abs = os.path.abspath(db_path)
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        values = config.get('DB_IGNORES', {}).get(db_abs, [])
        return values if isinstance(values, list) else []
    except Exception:
        return []



def get_saved_rekordbox_xml(db_path):
    """Return the per-database rekordbox XML path stored in config.json."""
    db_abs = os.path.abspath(db_path)
    if not os.path.exists(CONFIG_FILE):
        return ''
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        value = config.get('DB_REKORDBOX_XML', {}).get(db_abs, '')
        return str(value or '').strip()
    except Exception:
        return ''


def save_rekordbox_xml(db_path, xml_path):
    """Persist the preferred rekordbox XML path for one database."""
    db_abs = os.path.abspath(db_path)
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            config = {}
    mapping = config.get('DB_REKORDBOX_XML', {})
    if not isinstance(mapping, dict):
        mapping = {}
    clean = str(xml_path or '').strip()
    if clean:
        mapping[db_abs] = clean
    else:
        mapping.pop(db_abs, None)
    config['DB_REKORDBOX_XML'] = mapping
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

GENRE_QUICK_CHOICES = [
    "Rock", "Pop", "EDM", "Classic Rock", "Pop-Rock", "Blues",
    "Hiphop", "Rap", "R and B", "Soul", "Reggae"
]

ALLOWED_GENRES = [
    "Pop", "EDM", "Blues", "Hiphop", "Rap", "Rock", "Classic Rock", 
    "Pop-Rock", "R and B", "Soul", "Reggae"
]

GENRE_SYNONYMS = {
    "house": "EDM", "deep house": "EDM", "techno": "EDM", "trance": "EDM", 
    "eurodance": "EDM", "dubstep": "EDM", "dance": "EDM", "dance-pop": "EDM", 
    "slap house": "EDM", "big room": "EDM", "future house": "EDM", "hardstyle": "EDM", 
    "progressive house": "EDM", "psytrance": "EDM", "tech house": "EDM", 
    "trap": "EDM", "tropical house": "EDM", "electronic": "EDM", "euro house": "EDM",
    "hard rock": "Rock", "indie rock": "Rock", "punk rock": "Rock", 
    "gothic rock": "Rock", "alternative rock": "Rock", 
    "metal": "Rock", "heavy metal": "Rock", "nu metal": "Rock", "industrial": "Rock", 
    "rock n roll": "Rock", "rock & roll": "Rock", "rock 'n' roll": "Rock", "deutsch-rock": "Rock",
    "pop rock": "Pop-Rock", "pop/rock": "Pop-Rock", "pop-rock": "Pop-Rock",
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
        if wl in ['feat.', 'ft.', 'featuring']: 
            cap_words.append('feat.')
        elif wl in ['and', '&']: 
            cap_words.append('&')
        elif w == '': 
            cap_words.append(w)
        elif w == w.lower() and not any(ch.isdigit() for ch in w):
            if len(w) > 1 and not w[0].isalpha():
                cap_words.append(w[0] + w[1].upper() + w[2:])
            else:
                cap_words.append(w[0].upper() + w[1:])
        else: 
            cap_words.append(w)
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