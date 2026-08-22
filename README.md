================================================================================
mAirList DB Restorer v0.4 — Metadaten-Reparatur-Tool / Metadata Repair Tool
================================================================================

DEUTSCH
--------------------------------------------------------------------------------
mAirList DB Restorer v0.4
Ein Metadaten-Reparatur-Tool für die mAirList-Community

Jeder, der eine Musikdatenbank pflegt, kennt das Problem: Fehlende Jahreszahlen,
leere Genre-Felder, unvollständige Labelcodes oder fehlende Alben. Der mAirList
DB Restorer nimmt dir diese mühsame Handarbeit ab.

Das Tool analysiert deine lokale mAirList SQLite-Datenbank (.mldb), sucht über
die APIs von MusicBrainz und Discogs nach den fehlenden Metadaten und schreibt
die korrigierten Werte sicher in die Datenbank zurück.

Features (Kurzüberblick)
- Smart Cleaning: Bereinigung von Artist- und Title-Strings (Standardisierung von ft./feat.).
- Intelligentes Matching: Levenshtein-basierte Ähnlichkeitsprüfung zur Vermeidung falscher Zuordnungen.
- Ausreißer-Filter: Median-/Lücken-Logik zum Ignorieren offensichtlicher Jahreszahlen-Ausreißer.
- OAD-Schutz: Ordner/Dateien mit "OAD" werden ignoriert (z. B. Jingle-Pakete).
- Maskierte Konfiguration: API-Keys werden lokal base64-kodiert in config.json gespeichert
  (Hinweis: Base64 ist keine Verschlüsselung — nur eine leichte Maskierung).

Voraussetzungen & Installation
1. Installiere Python (https://www.python.org/downloads/). Bei Windows: "Add Python to PATH" aktivieren.
2. Öffne die Eingabeaufforderung und installiere benötigte Bibliotheken:
   pip install pandas requests rich

Discogs API-Zugang
1. Erstelle einen Account auf discogs.com.
2. Unter Settings → Developers eine App/Token anlegen und Consumer Key + Consumer Secret notieren.

Workflow (Bedienung)
WICHTIG: Arbeite niemals an der .mldb-Datei, die gerade von mAirList geöffnet ist. Erstelle immer eine KOPIE der .mldb-Datei und arbeite mit dieser Kopie!

Start: Restore.bat ausführen. Beim ersten Start fragt das Skript nach Discogs-Keys und einer Kontakt-E-Mail für MusicBrainz. Danach erscheint das Hauptmenü.

Menü (Kurz)
- [0] Aktive Datenbank auswählen / wechseln
- [1] Smart-Abruf — Neue Tracks laden / Abbruch fortsetzen
- [2] Voll-Abruf — Alle Tracks komplett neu laden (Reset)
- [3] Kontrolle — Alle Vorschläge manuell prüfen
- [4] Kontrolle (automatisch) — Sichere Treffer automatisch übernehmen
- [5] Speichern — Geprüfte Werte in .mldb-Kopie schreiben
- [6] Beenden

Ablauf
1) fetch (Metadaten laden): Das Skript liest die DB-Kopie ein, holt Vorschläge von MusicBrainz/Discogs und speichert Fortschritt in einer CSV (fortsetzbar).
2) review (Daten kontrollieren): Vorschläge manuell prüfen, annehmen (j), ablehnen (Enter) oder bearbeiten (eigener Text). Bei Freitext wird live neu gefetcht.
3) apply (In mAirList speichern): Änderungen in die ausgewählte .mldb-Kopie schreiben — es wird ein Backup erstellt. Nur anwenden, wenn die Datei wirklich eine Kopie ist und mAirList geschlossen ist.

Das "RESTAURIERT"-Flag
Beim Schreiben setzt das Skript das Item-Attribut RESTAURIERT = "JA". Solche Tracks werden bei späteren Durchläufen übersprungen. Möchtest du einen Track erneut verarbeiten, entferne das Attribut in mAirList.

Dateien im Repository (Beispiel)
- Restore.bat — Batch-Starter für Windows
- restore.py — Hauptskript (CLI, Rich-UI, Logging)
- LIESMICH.txt — (original, DE)
- config.json — wird beim ersten Start angelegt (base64-kodierte Keys)

Sicherheitshinweise
- Base64 kodiert, aber verschlüsselt nicht: Teile config.json nicht unbedacht.
- Vor jeglichen Schreiboperationen stets ein vollständiges Backup der Original-.mldb anlegen.
- Bei Verbreitung eines Windows-Executables empfiehlt sich Code-Signing, damit Defender/SmartScreen weniger Warnungen anzeigen.

--------------------------------------------------------------------------------
ENGLISH
--------------------------------------------------------------------------------
mAirList DB Restorer v0.4
A metadata repair tool for the mAirList community

Anyone who maintains a music database knows the problem: missing release years,
empty genre fields, incomplete label codes, or missing album titles. The mAirList
DB Restorer automates this tedious work.

The tool analyzes your local mAirList SQLite database (.mldb), queries the
MusicBrainz and Discogs APIs for missing metadata, and safely writes the
verified values back to the database.

Features (Short overview)
- Smart Cleaning: Cleans artist and title strings and standardizes feature notations (ft./feat.).
- Intelligent Matching: Uses Levenshtein-like similarity checks to avoid wrong matches.
- Outlier Filter: Rejects obviously wrong release years via median/gap logic.
- OAD protection: Ignores folders/files named "OAD" (e.g., jingle packages remain untouched).
- Masked configuration: API keys are stored base64-encoded in config.json
  (Note: base64 is NOT encryption — only mild obfuscation).

Requirements & Installation
1. Install Python (https://www.python.org/downloads/). On Windows, check "Add Python to PATH".
2. Open a command prompt and install required libraries:
   pip install pandas requests rich

Discogs API credentials
1. Create an account at discogs.com
2. Under Settings → Developers create an app/token and copy your Consumer Key and Consumer Secret.

Workflow (Usage)
IMPORTANT: Never operate on the .mldb file that mAirList currently has open. Always create a COPY of the .mldb file and work on that copy!

Start: Run Restore.bat. On first run the script asks for Discogs keys and a MusicBrainz contact email. Afterwards the main menu appears.

Menu (Short)
- [0] Select / change active database
- [1] Smart fetch — Load new tracks / resume
- [2] Full fetch — Re-fetch all tracks (reset)
- [3] Review — Manually inspect all proposals
- [4] Review (auto) — Auto-accept high-confidence matches
- [5] Apply — Write approved values into the .mldb copy
- [6] Exit

Process
1) fetch: Reads DB copy, retrieves metadata suggestions from MusicBrainz/Discogs, and saves progress to a CSV (resumable).
2) review: Manually inspect suggestions; accept with "j" (yes), reject with Enter, or input custom text. Custom edits trigger a live re-fetch.
3) apply: Writes changes into the chosen .mldb copy — a backup will be created. Only run this when you are sure the file is a copy and mAirList is closed.

The "RESTAURIERT" flag
When applying, the script sets the item attribute RESTAURIERT = "JA". Those tracks are skipped on future runs. To reprocess, remove the attribute in mAirList.

Repository files (example)
- Restore.bat — Windows batch starter
- restore.py — Main script (CLI with rich + logging)
- LIESMICH.txt — original German README
- config.json — created on first run (base64-encoded creds)

Security notes
- Base64 is obfuscation, not encryption: do not share config.json carelessly.
- Always back up the original .mldb before writing changes.
- Consider code signing if you distribute a Windows executable to reduce SmartScreen warnings.

--------------------------------------------------------------------------------
Quick start (example)
1. Copy your .mldb to the Desktop (or another safe location).
2. Place Restore.bat and restore.py in the same folder as the copy.
3. Run Restore.bat and follow the setup prompts.
4. Use menu steps 1 → 3 → 5 (fetch → review → apply), always working on a copy.

License & attribution
This tool is intended for free use by the mAirList community. Please include your own license file (e.g. MIT) in the repo if you want to make the exact licensing explicit.

Contact / Support
For API issues use your MusicBrainz contact email and Discogs developer settings. For script issues, open an issue in this repository and include your restored log file (restorer.log) and a brief description of the problem.

================================================================================
Version: v0.4
Maintainer: Myka Vormeng
================================================================================