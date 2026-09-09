# 📖 Handbuch: mAirList DB Restorer

Willkommen beim offiziellen Handbuch für den **mAirList DB Restorer**! Dieses Tool wurde entwickelt, um dir hunderte Stunden mühsamer Handarbeit im Cue-Editor zu ersparen, indem es fehlende Metadaten (Jahre, Genres, Alben, Labels) vollautomatisch über die APIs von MusicBrainz und Discogs sucht und ergänzt.

Dank der "All-in-One"-Architektur ist das Programm sofort startklar – ohne komplizierte Installation! Damit alles reibungslos funktioniert, führe bitte einmalig die folgende kurze Einrichtung durch.

---

## 1. Vorbereitung & Installation

Das Tool ist eine komplett eigenständige Anwendung (`.exe`). Du musst weder Python noch irgendwelche Code-Bibliotheken installieren. Lade dir einfach die aktuelle ZIP-Datei herunter, entpacke sie an einem Ort deiner Wahl und starte die Datei **`mAirList-DB-Restorer.exe`**.

### Schritt 1.1: Discogs API-Keys generieren
Um auf die riesige Datenbank von Discogs zugreifen zu dürfen, benötigt das Skript einen kostenlosen API-Schlüssel.
1. Erstelle dir einen kostenlosen Account auf [discogs.com](https://www.discogs.com) (falls du noch keinen hast) und logge dich ein.
2. Klicke oben rechts auf dein Profilbild und wähle **Einstellungen** (Settings).
3. Gehe im linken Menü ganz unten auf **Entwickler** (Developers).
4. Klicke auf den Button **"Create an App"** (oder Generate Token).
5. Gib einen beliebigen Namen für die App ein (z. B. "mAirList Restorer").
6. Du erhältst nun zwei wichtige kryptische Zeichenketten: Den **Consumer Key** und das **Consumer Secret**.
7. Kopiere dir diese beiden Werte. Beim allerersten Start der `.exe` wird dich das Programm danach fragen und sie lokal im `Data`-Ordner speichern. Die Werte werden dort lediglich Base64-verschleiert und nicht kryptografisch verschlüsselt.

---

## 2. Die goldene Regel: Backups! 🛡️

Das Wichtigste beim Arbeiten mit Datenbanken ist die Datensicherheit. Der mAirList DB Restorer greift tief in die Struktur ein und schreibt Metadaten vollautomatisch um.

⚠️ **Arbeite NIEMALS mit der aktiven Datenbank-Datei (`.mldb`), die mAirList in diesem Moment geöffnet hat!**
Wenn mAirList läuft, sperrt (lockt) es die Datenbank-Datei. Wenn das Tool nun versucht, gleichzeitig neue Genres oder Jahreszahlen in diese Datei zu schreiben, kann die Datenbank im schlimmsten Fall irreparabel beschädigt werden. Das Skript hat zwar einen eingebauten Schutz, der blockierte Dateien erkennt, aber Vorsicht ist besser als Nachsicht.

### Der sichere Workflow:
1. Schließe mAirList oder öffne den Windows-Explorer und navigiere zu dem Ordner, in dem deine `.mldb`-Datei liegt.
2. Kopiere die Datei (z. B. `Archiv.mldb`) und füge sie an einem sicheren Ort, wie deinem **Desktop**, wieder ein.
3. Starte die `Restorer.exe`.
4. Wenn dich das Skript im Menü nach dem Pfad zur Datenbank fragt, **tippe ihn nicht mühsam ein**!
5. 💡 **Pro-Tipp:** Klicke die kopierte `.mldb`-Datei auf deinem Desktop einfach an, halte die Maustaste gedrückt und **ziehe die Datei per Drag & Drop direkt in das Fenster**. Drücke `Enter`. Der Pfad ist nun perfekt hinterlegt!
6. Wenn du mit dem Tool fertig bist und alle neuen Metadaten in der Kopie gespeichert hast, schließt du mAirList, ersetzt die alte Datei durch deine neue, bearbeitete Kopie und startest mAirList neu.

---

## 3. Der Workflow: Metadaten restaurieren

Beim ersten Start fragt dich das Tool nach deiner bevorzugten Sprache (Deutsch, Englisch, Nederlands). Diese Einstellung merkt sich das Skript für die Zukunft. Über Option **[8]** im Hauptmenü kannst du sie jederzeit wieder ändern; Option **[9]** beendet das Programm. 
Sobald du deine Datenbank-Kopie geladen hast, führt dich das interaktive Menü logisch durch den gesamten Prozess. Direkt im Hauptmenü steht als Orientierung der empfohlene Ablauf **1 → 4/5 → 7**. *Hinweis: Das Skript legt automatisch einen Ordner namens `Data` an. Arbeitsstände werden dort atomar gespeichert und anhand des vollständigen Datenbankpfads getrennt, sodass auch zwei gleichnamige `.mldb`-Dateien nicht denselben Cache benutzen.*

### Schritt 3.1: Ordner-Ausnahmen definieren (Ignore-List)
Bevor das Skript beim ersten Abruf mit der Suche beginnt, fragt es dich nach Ordnern, die **konsequent ignoriert** werden sollen (z. B. Ordner für Jingles, News, Drops oder Werbung).
*   **Kinderleichte Eingabe:** Du kannst hier einfach den physischen Ordner aus dem Windows-Explorer per Drag & Drop hineinziehen oder den exakten Namen eines virtuellen mAirList-Ordners eintippen. Drücke bei einer leeren Eingabe `Enter`, wenn du mit der Liste fertig bist.
*   **Individuell pro Datenbank:** Das Skript ist smart und merkt sich diese Ausnahmeliste individuell für exakt diese geladene `.mldb`-Datei!
*   **Jederzeit anpassbar:** Startest du das Tool später erneut mit derselben Datenbank, zeigt es dir die aktuelle Ignore-List an und fragt dich, ob du sie behalten oder neu anlegen möchtest.

### Schritt 3.2: Metadaten laden (Fetch)
In dieser Phase sucht das Skript über die APIs von MusicBrainz und Discogs nach den passenden Metadaten für deine Tracks. Deine Original-Werte bleiben dabei völlig unangetastet! 

*   **[1] Neue/unbearbeitete Tracks suchen:** Prüft nur Tracks, die noch nicht restauriert wurden, und pausiert nach jeweils 50 geladenen Tracks. Der Arbeitsstand ist jederzeit fortsetzbar.
*   **[2] Alle offenen Tracks ohne Pause suchen:** Macht dasselbe wie Option 1, läuft aber ohne 50er-Pause bis zum Ende durch – praktisch für große Datenbanken oder über Nacht.
*   **[3] Alle Tracks komplett neu prüfen:** Ignoriert das `RESTAURIERT`-Flag und holt für **ALLE** Tracks neue Vorschläge. Nach dem Review dürfen diese bewusst neu geprüften Werte auch bereits restaurierte Datensätze überschreiben; der normale Überschreib-Schutz bleibt für Option 1/2 erhalten.

Wenn MusicBrainz oder Discogs vorübergehend nicht erreichbar sind, versucht der Restorer den Request automatisch mehrfach. Bleibt der Fehler bestehen, wird der betreffende Track **nicht als fertig markiert**, sondern bleibt offen und wird bei einem späteren Abruf erneut versucht.

> **Tipp:** Du kannst den Fetch-Vorgang jederzeit mit der Tastenkombination `Strg + C` abbrechen. Das Skript speichert deinen bisherigen Fortschritt sicher ab, und du kannst beim nächsten Start exakt an dieser Stelle weitermachen!

### Schritt 3.3: Daten kontrollieren (Review)
Wähle Option **[4] Alle Vorschläge selbst kontrollieren** oder **[5] Prüfung mit Automatik**. Option 4 zeigt dir alle Vorschläge manuell. Option 5 übernimmt ausschließlich sichere **Jahr-/Genre-Treffer** automatisch; die übrigen Felder bleiben weiterhin kontrollierbar.

*   **Bestätigen:** Wenn dir ein Vorschlag (z. B. das Jahr) gefällt, drücke einfach `Enter`. Das Tool übernimmt den Wert und springt zum nächsten Feld.
*   **Original behalten (`O`-Taste):** Neben dem Vorschlag siehst du in Grau immer deinen ursprünglichen Datenbank-Wert. Ist dein eigener Wert besser? Tippe einfach ein `o` (für Original) und drücke `Enter`.
*   **Eigener Text:** Der Vorschlag ist falsch, aber dein Originalwert auch? Tippe einfach deinen gewünschten Text ein.
*   **Live Re-Fetch:** Wenn du bei Artist, Titel, Jahr oder Album einen eigenen Text eintippst (z. B. um einen Tippfehler im Artist-Namen zu korrigieren), feuert das Skript im Hintergrund sofort eine neue API-Suche ab und passt Labels, Genres und ISRC live an deine Korrektur an!
*   **Oops, vertippt?** Tippe ein `<` oder `b` (für Back) und drücke `Enter`, um einen Track zurückzuspringen.

### Schritt 3.4: Wartung (Maintenance)
Unter Option **[6]** findest du die Wartungswerkzeuge. Du kannst Genres standardisieren, Groß-/Kleinschreibung und Apostrophe in Artist/Title korrigieren oder mit dem Datei-Tagger geprüfte Metadaten aus der Datenbank in lokale FLAC-, MP3- und AIFF-Dateien schreiben. Die Sammeloption **[4]** führt die Genre- und Schreibweisenkorrektur nacheinander aus.

### Schritt 3.5: In mAirList speichern (Apply)
Wenn du alle Tracks geprüft hast, wählst du im Hauptmenü Option **[7] Geprüfte Änderungen in die Datenbank-Kopie schreiben**. Vor dem Schreiben zeigt der Restorer eine Zusammenfassung der geplanten Feldänderungen und führt eine SQLite-Integritätsprüfung durch. Erst nach deiner Bestätigung wird ein Backup erstellt und in einem schnellen Bulk-Verfahren geschrieben. Anschließend wird die Datenbankintegrität erneut geprüft.

*   Das Skript setzt dabei für jeden Track automatisch das interne Attribut `RESTAURIERT` auf `JA`. 
*   Tracks mit diesem Flag werden bei zukünftigen Durchläufen automatisch übersprungen. 
*   Fällt dir später im Live-Betrieb auf, dass ein Track doch falsche Tags hat? Lösche in mAirList einfach das "RESTAURIERT"-Attribut bei diesem Track. Beim nächsten Skript-Lauf erkennt das Tool den Track als "neu" und lädt ihn noch einmal.