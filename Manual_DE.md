# 📖 Handbuch: mAirList DB Restorer

Willkommen beim offiziellen Handbuch für den **mAirList DB Restorer**! Dieses Tool wurde entwickelt, um dir hunderte Stunden mühsamer Handarbeit im Cue-Editor zu ersparen, indem es fehlende Metadaten (Jahre, Genres, Alben, Labels) vollautomatisch über die APIs von MusicBrainz und Discogs sucht und ergänzt.

Damit alles reibungslos funktioniert, führe bitte einmalig die folgende kurze Einrichtung durch.

---

## 1. Vorbereitung & Installation

Da es sich bei diesem Tool um ein Python-Skript handelt, benötigt dein Computer die entsprechende Umgebung, um es ausführen zu können. Die Einrichtung dauert nur etwa 5 Minuten.

### Schritt 1.1: Python installieren
1. Lade dir die aktuellste Version von **Python** für Windows herunter: [python.org/downloads](https://www.python.org/downloads/)
2. Starte die heruntergeladene `.exe`-Datei.
3. ⚠️ **EXTREM WICHTIG:** Bevor du im Installationsfenster auf "Install Now" klickst, musst du ganz unten zwingend das Häkchen bei **"Add Python to PATH"** (oder "Add python.exe to PATH") setzen! Fehlt dieses Häkchen, wird das Skript später nicht starten.
4. Klicke auf "Install Now" und warte, bis die Installation abgeschlossen ist.

### Schritt 1.2: Benötigte Bibliotheken installieren
Das Skript greift auf externe Bibliotheken zurück (z.B. für das bunte Terminal-Menü oder den CSV-Export). Diese müssen einmalig installiert werden.
1. Drücke auf deiner Tastatur die `Windows-Taste + R`.
2. Tippe `cmd` in das kleine Fenster ein und drücke `Enter`. (Die schwarze Windows-Eingabeaufforderung öffnet sich).
3. Kopiere den folgenden Befehl, füge ihn in das schwarze Fenster ein und drücke `Enter`:
   `pip install pandas requests rich`
4. Windows lädt nun die benötigten Pakete herunter. Sobald der Vorgang fertig ist, kannst du das Fenster schließen.

### Schritt 1.3: Discogs API-Keys generieren
Um auf die riesige Datenbank von Discogs zugreifen zu dürfen, benötigt das Skript einen (kostenlosen) API-Schlüssel.
1. Erstelle dir einen kostenlosen Account auf [discogs.com](https://www.discogs.com) (falls du noch keinen hast) und logge dich ein.
2. Klicke oben rechts auf dein Profilbild und wähle **Einstellungen** (Settings).
3. Gehe im linken Menü ganz unten auf **Entwickler** (Developers).
4. Klicke auf den Button **"Create an App"** (oder Generate Token).
5. Gib einen beliebigen Namen für die App ein (z.B. "mAirList Restorer").
6. Du erhältst nun zwei wichtige kryptische Zeichenketten: Den **Consumer Key** und das **Consumer Secret**.
7. Kopiere dir diese beiden Werte. Beim allerersten Start der `Restore.bat` wird dich das Skript danach fragen und sie sicher und maskiert abspeichern.

---

## 2. Die goldene Regel: Backups! 🛡️

Das Wichtigste beim Arbeiten mit Datenbanken ist die Datensicherheit. Der mAirList DB Restorer greift tief in die Struktur ein und schreibt Metadaten vollautomatisch um.

⚠️ **Arbeite NIEMALS mit der aktiven Datenbank-Datei (`.mldb`), die mAirList in diesem Moment geöffnet hat!**

Wenn mAirList läuft, sperrt (lockt) es die Datenbank-Datei. Wenn das Python-Skript nun versucht, gleichzeitig neue Genres oder Jahreszahlen in diese Datei zu schreiben, kann die Datenbank im schlimmsten Fall irreparabel beschädigt werden. 

### Der sichere Workflow:
1. Schließe mAirList oder öffne den Windows-Explorer und navigiere zu dem Ordner, in dem deine `.mldb`-Datei liegt.
2. Kopiere die Datei (z.B. `Archiv.mldb`) und füge sie an einem sicheren Ort, wie deinem **Desktop**, wieder ein.
3. Starte die `Restore_2.bat`.
4. Wenn dich das Skript nach dem Pfad zur Datenbank fragt, **tippe ihn nicht mühsam ein**!
5. 💡 **Pro-Tipp:** Klicke die kopierte `.mldb`-Datei auf deinem Desktop einfach an, halte die Maustaste gedrückt und **ziehe die Datei per Drag & Drop direkt in das schwarze Konsolen-Fenster**. Drücke `Enter`. Der Pfad ist nun perfekt hinterlegt!
6. Wenn du mit dem Tool fertig bist und alle neuen Metadaten in der Kopie gespeichert hast, schließt du mAirList, ersetzt die alte Datei durch deine neue, bearbeitete Kopie und startest mAirList neu.
