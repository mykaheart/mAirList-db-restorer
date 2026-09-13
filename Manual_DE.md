# 📖 Handbuch: mAirList DB Restorer 0.64.00 BETA

Der **mAirList DB Restorer** unterstützt bei der Pflege lokaler mAirList-Datenbanken (`.mldb`). Er liest vorhandene Metadaten, recherchiert fehlende oder fragliche Angaben über MusicBrainz und Discogs, kann fehlende BPM aus rekordbox, Datei-Tags und AcousticBrainz ergänzen und bietet mehrere Wartungsfunktionen für bestehende Datenbanken.

Der Restorer arbeitet bewusst konservativ: Er erzeugt zunächst Vorschläge, trennt Lesen, Review und Schreiben voneinander und führt vor sicherheitskritischen Datenbankänderungen Integritätsprüfungen und Backups durch.

> **Wichtig:** Dieses Programm ist für **lokale SQLite-Datenbanken (`.mldb`)** gedacht. Netzwerkdatenbanken werden derzeit nicht unterstützt.

---

## 1. Grundprinzip und Sicherheitsgrenzen

Der Restorer darf Metadaten ergänzen oder korrigieren, verändert aber bestimmte technische Felder ausdrücklich **nicht**:

- `Duration`, `Length` und `TotalDuration` werden niemals neu berechnet oder überschrieben.
- Audioinhalte werden nicht analysiert, konvertiert oder normalisiert.
- Lyrics/Songtexte werden durch den normalen Restorer-Workflow **nicht aus der mAirList-Datenbank gelöscht**. Sie werden lediglich aus den Arbeits-CSVs im `Data`-Ordner herausgehalten, damit diese Dateien klein bleiben.
- Bestehende gültige `BPM`-Werte werden nicht automatisch überschrieben.
- Die Wartungsfunktion für Dopplungen markiert nur Kandidaten; sie löscht niemals Elemente.
- Festgestellte SQLite-Inkonsistenzen werden angezeigt, aber nicht automatisch repariert.

Die zentrale Regel lautet daher:

> **Maschine findet und schlägt vor – Mensch entscheidet über inhaltliche Änderungen.**

---

## 2. Installation und Ersteinrichtung

Die Release-ZIP enthält eine eigenständige `Restorer.exe`. Für die normale Nutzung ist keine Python-Installation erforderlich.

1. ZIP-Datei vollständig entpacken.
2. `Restorer.exe` starten.
3. Beim ersten Start Sprache auswählen: Deutsch, Englisch oder Nederlands.
4. Discogs-Zugangsdaten und eine Kontakt-E-Mail für MusicBrainz eintragen.

Die Zugangsdaten werden lokal in `Data/config.json` gespeichert. Discogs-Key, Discogs-Secret und MusicBrainz-Kontakt werden dort nur Base64-kodiert abgelegt; dies ist **keine kryptografische Verschlüsselung**.

### Discogs-Zugangsdaten

Für Discogs wird ein kostenloser Entwicklerzugang benötigt. Im Discogs-Konto können unter den Entwickler-Einstellungen Consumer Key und Consumer Secret erzeugt werden.

### MusicBrainz-Kontakt

MusicBrainz verlangt einen aussagekräftigen User-Agent mit Kontaktmöglichkeit. Deshalb fragt der Restorer nach einer gültigen E-Mail-Adresse. Sie wird ausschließlich für den User-Agent der MusicBrainz-Anfragen verwendet.

---

## 3. Unbedingt mit einer Datenbank-Kopie arbeiten 🛡️

Der Restorer erkennt viele Sperrsituationen und verweigert Schreibvorgänge, wenn die Datenbank erkennbar von einem anderen Programm benutzt wird. Trotzdem gilt:

**Arbeite niemals direkt auf der aktuell von mAirList geöffneten Produktionsdatenbank.**

Empfohlener Ablauf:

1. mAirList schließen oder eine aktuelle Kopie der `.mldb` anlegen.
2. Die Kopie mit dem Restorer bearbeiten.
3. Ergebnisse in mAirList prüfen.
4. Erst danach die produktive Datenbank ersetzen bzw. den getesteten Stand übernehmen.

Bei Apply, Dopplungswartung und BPM-Wartung erstellt der Restorer zusätzlich ein Zeitstempel-Backup neben der Datenbank. Es werden automatisch die **neuesten fünf** solcher Backups behalten.

---

## 4. Der `Data`-Ordner: Arbeitsstände, Logs und Konfiguration

Der Restorer legt automatisch einen Ordner `Data` neben der Anwendung an. Dort befinden sich unter anderem:

- `config.json` – Sprache, API-Zugangsdaten, Ignore-Listen und der bevorzugte rekordbox-XML-Pfad pro Datenbank.
- `*_vorschlaege.csv` – laufender Fetch-Arbeitsstand.
- `*_restauriert.csv` – nach dem Review freigegebener Arbeitsstand für Apply.
- `*_bpm-review_YYYYMMDD-HHMMSS.csv` – vollständige Review-Liste der BPM-Wartung.
- `*.log` – Laufprotokolle mit Zeitstempel.

### Kollisionssichere Arbeitsstände

Der Dateiname der Arbeits-CSVs enthält neben dem Datenbanknamen einen kurzen Hash des vollständigen Datenbankpfads. Dadurch können zwei gleichnamige `.mldb`-Dateien aus verschiedenen Ordnern nicht versehentlich denselben Arbeitsstand benutzen.

Ältere Arbeitsdateien werden beim Start nach Möglichkeit in das neue Schema migriert. Wenn bereits eine Datei gleichen Namens existiert, wird nichts überschrieben; beide Stände bleiben erhalten.

### Lyrics/Songtexte

Lyrics-Felder werden beim Schreiben der Arbeits-CSVs gezielt entfernt. Das betrifft **nur die Restorer-Arbeitsdateien**. Die entsprechenden Werte in der `.mldb` bleiben unverändert.

---

## 5. Hauptmenü und empfohlener Workflow

Der normale Metadaten-Workflow lautet:

**[1] oder [2] oder [3] Fetch → [4] oder [5] Review → [7] Apply**

Weitere Optionen:

- **[0]** Datenbank auswählen
- **[6]** Wartungsmenü
- **[8]** Sprache wechseln
- **[9]** Programm beenden

---

## 6. Datenbank auswählen und Ignore-Listen

Nach Auswahl von **[0]** kann der Pfad zur `.mldb` eingegeben oder per Drag & Drop in das Konsolenfenster gezogen werden.

Beim ersten Fetch fragt der Restorer nach Ordnern, die ignoriert werden sollen. Typische Beispiele sind `OAD`, Jingles, News, Werbung oder andere Bereiche, die nicht durch die Metadatenrecherche laufen sollen.

Die Ignore-Liste kann enthalten:

- physische Pfade,
- virtuelle mAirList-Ordnernamen,
- Teilordnernamen.

Sie wird **pro Datenbankpfad** in `config.json` gespeichert. Beim nächsten Lauf kann sie beibehalten oder neu erstellt werden.

Die gespeicherte Ignore-Liste wird außerdem bei Dopplungs- und BPM-Wartung berücksichtigt. Die einfachen Wartungsfunktionen für Genre und Schreibweise arbeiten dagegen direkt auf den betreffenden Datenbankfeldern und verwenden diese Ignore-Liste nicht.

---

## 7. Fetch: Metadaten recherchieren

### [1] Neue/offene Tracks in 50er-Blöcken

Lädt nur noch offene Titel. Nach jeweils 50 bearbeiteten Tracks kann der Fetch pausiert und zum Review gewechselt werden. Der Arbeitsstand wird regelmäßig atomar gespeichert.

### [2] Alle offenen Tracks ohne Pause

Gleiche Logik wie [1], aber ohne 50er-Pausen. Geeignet für längere unbeaufsichtigte Läufe.

### [3] Full Fetch

Prüft alle relevanten Tracks erneut – auch Titel, die bereits `RESTAURIERT=JA` besitzen.

Beim Full Fetch wird der aktuelle Stand aus der `.mldb` erneut in den Arbeitscache übernommen. Die betreffenden Zeilen erhalten intern `FORCE_APPLY=JA`, damit bewusst neu geprüfte Werte später trotz normalem Restauriert-Schutz geschrieben werden dürfen.

**Wichtig:** Auch beim Full Fetch werden bereits vorhandene gültige BPM **nicht überschrieben**.

### Welche Elemente werden nicht normal gefetcht?

System-/Nicht-Musiktypen wie `Dummy`, `Stream`, `Command`, `Silence` und `Other` werden aus dem normalen API-Fetch herausgefiltert. Zusätzlich gelten deine Ignore-Listen.

### Welche Felder können recherchiert oder vorgeschlagen werden?

Der Fetch arbeitet unter anderem mit:

| Feld | Verhalten |
| --- | --- |
| Artist | Schreibweisen-Vorschlag / Bereinigung |
| Title | Schreibweisen-Vorschlag / Bereinigung |
| Jahr | MusicBrainz + Discogs, mit Plausibilitäts-/Ausreißerlogik |
| Genre | Discogs, anschließend Mapping auf die Restorer-Genrekategorien |
| Album | Discogs bzw. MusicBrainz |
| STYLE | Discogs Styles |
| DISCOGS_RELEASE_ID | passende Discogs-Referenz |
| Label | Discogs |
| Labelcode | Discogs/MusicBrainz-Hilfsrecherche, soweit verfügbar |
| ISRC | MusicBrainz |
| Sprache | wird nicht blind aus MusicBrainz-Release-Sprache abgeleitet; bleibt bei fehlender sicherer Quelle unter manueller Kontrolle |
| Typ | wird nur vorgeschlagen, wenn das Attribut leer ist; Grundlage ist der interne mAirList-Elementtyp |
| BPM | rekordbox XML → Datei-Tag → MusicBrainz/AcousticBrainz |

### Laufzeit-Matching

Wo möglich wird die lokale Tracklaufzeit zur Identifikation verwendet. Sie dient ausschließlich als Matching-Hilfe und wird **niemals verändert**.

### Release-Jahr und Ausreißer

Der Restorer sammelt plausible Veröffentlichungsjahre und filtert extreme Einzel-Ausreißer. Ziel ist das ursprüngliche bzw. früheste plausible Veröffentlichungsjahr und nicht das Jahr einer späteren Compilation.

### API-Fehler und Wiederaufnahme

MusicBrainz-, Discogs- und AcousticBrainz-Zugriffe besitzen Retry-/Rate-Limit-Logik. Zusätzlich startet der normale Fetch bei **vorübergehenden** Fehlern den kompletten Track automatisch neu: bis zu drei Wiederholungen mit wachsender Pause von 2, 5 und 10 Sekunden. Diese Track-Retries gelten nur für Netzwerk/Timeout, HTTP 429 und retrybare 5xx-Fehler. `Retry-After` bzw. verfügbare Rate-Limit-Reset-Hinweise des Servers werden berücksichtigt und können die Pause verlängern. Nicht-transiente 4xx-/Logikfehler werden nicht sinnlos wiederholt. Erst wenn auch die automatischen Wiederholungen scheitern, bleibt der Track offen (`FEHLER`) und wird bei einem späteren Fetch erneut versucht.

`Strg+C` beendet einen Fetch kontrolliert; der bisherige Arbeitsstand wird gespeichert.

---

## 8. BPM im normalen Fetch

Seit 0.64 ist die BPM-Suche Bestandteil des normalen Fetch-Workflows.

### rekordbox XML auswählen

Vor einem normalen Fetch kann ein rekordbox-XML-Export angegeben werden. Der gewählte Pfad wird **pro Datenbank** gespeichert. Beim nächsten Fetch erscheint er als Standardwert.

- `Enter` übernimmt den angezeigten Standardpfad.
- `-` deaktiviert die XML-Nutzung und löscht den gespeicherten Pfad für diese Datenbank.
- Existiert noch kein gespeicherter Pfad, sucht der Restorer zusätzlich nach `rekordbox.xml` neben der Anwendung bzw. im `Data`-Ordner.
- Ist die XML nicht vorhanden oder ungültig, bricht der Metadaten-Fetch nicht ab; die BPM-Suche läuft mit den Fallbacks weiter.

### Quellen-Priorität

Für einen Track ohne gültigen BPM gilt:

1. **rekordbox XML** – `AverageBpm`, ausschließlich bei exakt passendem Dateipfad aus `Location`.
2. **Audio-Datei-Tag** – z. B. ID3 `TBPM` oder Vorbis/FLAC `BPM`/`tempo`.
3. **MusicBrainz Recording-ID** – bevorzugt über gültige ISRC, sonst konservatives Artist/Title/Laufzeit-Matching.
4. **AcousticBrainz** – Low-Level-BPM nur bei sicher zugeordnetem MusicBrainz Recording.

Der rekordbox-Abgleich verwendet **kein Artist-/Titel-Fuzzy-Matching**. Der Dateipfad ist die Identität.

### Schutz vorhandener BPM

Besitzt die Live-Datenbank bereits einen gültigen BPM, wird für diesen Titel kein neuer BPM-Vorschlag erzeugt – auch nicht im Full Fetch.

### Review-Verhalten

Ein neuer `BPM_Vorschlag` erscheint im normalen Review und wird dort automatisch in das Feld `BPM` übernommen. Die Quelle steht im Arbeitsstand als `BPM_Quelle`. Die Quelle selbst wird nicht als mAirList-Attribut geschrieben.

BPM-Fehler sind für den allgemeinen Metadaten-Fetch nicht destruktiv: Wenn kein sicherer BPM gefunden wird, können die übrigen Metadaten trotzdem normal weiterbearbeitet werden. Wird im Review die Track-Identität manuell geändert, wird ein zuvor über AcousticBrainz ermittelter BPM-Vorschlag aus Sicherheitsgründen verworfen; rekordbox- und Datei-Tag-BPM bleiben an die konkrete Datei gebunden. Später kann Wartungsoption [6] ausschließlich die fehlenden BPM nachpflegen.

---

## 9. `RESTAURIERT`, Resume und Reset-Verhalten

Nach erfolgreichem Apply setzt der Restorer für geschriebene Tracks `RESTAURIERT=JA`.

Bei späteren normalen Fetches werden solche Tracks geschützt und übersprungen.

Wenn du in mAirList das Attribut `RESTAURIERT` bei einem Titel entfernst, erkennt der Restorer die `.mldb` beim nächsten Lauf als maßgebliche Quelle. Der alte Cache-Status wird zurückgesetzt und die Originalfelder dieses Tracks werden erneut aus der Datenbank geladen. Der Titel kann anschließend neu gefetcht und reviewed werden.

Ein Full Fetch ist die ausdrückliche Ausnahme: Er setzt für den Arbeitslauf `FORCE_APPLY=JA`, damit bewusst neu geprüfte Metadaten auch bei bereits restaurierten Titeln angewendet werden dürfen. Nach erfolgreichem Apply wird `FORCE_APPLY` wieder geleert.

---

## 10. Review: Vorschläge kontrollieren

### [4] Manuelles Review

Jeder offene, erfolgreich gefetchte Track wird einzeln angezeigt.

Bei interaktiven Feldern gilt grundsätzlich:

- **Enter** – Vorschlag übernehmen.
- **o** – Originalwert behalten.
- **eigener Text** – eigenen Wert eintragen.
- **`<` oder `b`** – einen Track zurückgehen.

### [5] Review mit Automatik

Sichere Jahr- und Genre-Treffer mit hoher Konfidenz können automatisch übernommen werden. Andere Felder bleiben wie im normalen Review kontrollierbar.

### Live Re-Fetch

Wenn Artist, Titel, Jahr oder Album manuell geändert werden, führt der Restorer eine gezielte erneute MusicBrainz-/Discogs-Recherche aus, damit abhängige Vorschläge wie Genre, Label, Labelcode, ISRC, STYLE und Discogs-ID zur korrigierten Identität passen.

### Automatisch übernommene technische Felder

Wenn ein sicherer Vorschlag vorliegt, werden `STYLE`, `DISCOGS_RELEASE_ID`, `Labelcode`, `ISRC`, `Typ` und `BPM` im Review ohne zusätzliche Einzelabfrage in den Arbeitsstand übernommen. Ein vorhandener BPM ist dabei bereits zuvor geschützt worden und erhält keinen neuen Vorschlag.

### Sprache

Da MusicBrainz in diesem Workflow keine zuverlässige Recording-Sprache liefert, wird Sprache nicht aus einem beliebigen Release-Sprachfeld abgeleitet. Bereits vorhandene Angaben bleiben erhalten; bei Bedarf kann Sprache im Review manuell gesetzt werden. Häufig verwendete eigene Sprachen merkt sich der Restorer in `config.json`.

---

## 11. Apply: geprüfte Änderungen sicher in die `.mldb` schreiben

Option **[7]** schreibt nur Tracks, deren Review abgeschlossen ist.

Vor dem Schreiben passiert Folgendes:

1. Schutzprüfung gegen bereits `RESTAURIERT=JA` markierte Tracks.
2. Ausnahmen mit `FORCE_APPLY=JA` werden bewusst zugelassen.
3. SQLite-`integrity_check`.
4. Übersicht der tatsächlich geplanten Feldänderungen – einschließlich BPM.
5. Sicherheitsbestätigung.
6. Zeitstempel-Backup der `.mldb`.
7. Rotation alter Restorer-Backups; die neuesten fünf bleiben erhalten.
8. Sammelschreiben in die Datenbank.
9. Zweiter SQLite-Integritätscheck.
10. Synchronisierung der Arbeits-CSVs und Setzen von `RESTAURIERT=JA`.

Wenn die Integritätsprüfung **vor** dem Schreiben fehlschlägt, wird nichts verändert. Typische Meldungen wie `wrong # of entries in index ...` deuten auf bereits vorhandene SQLite-/Index-Probleme hin. Der Restorer repariert solche Strukturen bewusst nicht automatisch.

---

## 12. Wartungsmenü [6]

Das Wartungsmenü enthält direkte Pflegefunktionen. Es ist vom normalen Fetch/Review/Apply-Workflow getrennt.

> **Achtung:** Die einfachen Wartungsfunktionen [1]–[4] schreiben direkt. Für diese Funktionen solltest du selbst vorher eine Datenbank- bzw. Dateikopie anlegen. Die aufwendigeren Funktionen [5] und [6] besitzen zusätzliche integrierte Integritäts-/Backup-Sicherungen.

### Wartung [1] – Genres standardisieren

Bestehende Genrewerte werden auf die im Restorer verwendeten Kernkategorien normalisiert. Aktuell gehören dazu unter anderem:

`Pop`, `EDM`, `Blues`, `Hiphop`, `Rap`, `Rock`, `Classic Rock`, `Pop-Rock`, `R and B`, `Soul`, `Reggae`.

Sowohl ein natives Genre-Feld als auch ein Genre-Attribut werden berücksichtigt, sofern sie im jeweiligen Datenbankschema existieren.

### Wartung [2] – Schreibweise und Apostrophe korrigieren

Artist und Titel werden auf konsistente Apostrophe und eine intelligente Groß-/Kleinschreibung normalisiert. Diese Funktion arbeitet direkt auf den entsprechenden `items`-Feldern.

### Wartung [3] – Datei-Tagger

Schreibt **geprüfte Datenbankwerte in lokale Audiodateien**. Unterstützt werden über Mutagen:

- FLAC
- Ogg Vorbis
- MP3
- AIFF

Geschrieben werden:

- Artist
- Title
- Jahr/Date
- Genre
- Album
- Label/Publisher

Nicht Teil dieses Datei-Taggers sind unter anderem BPM, ISRC, Labelcode, Sprache oder Lyrics.

Da mAirList Dateinamen häufig relativ zu Storage Locations speichert, fragt der Tagger nach lokalen Basisordnern. Er verändert die Audiodateien direkt und besitzt dafür keinen Undo-Mechanismus. Vor Nutzung ist daher ein Dateibackup empfehlenswert.

### Wartung [4] – Sammellauf

Führt **nur Wartung [1] und [2]** nacheinander aus. Der Datei-Tagger ist nicht Bestandteil dieses Sammellaufs.

---

## 13. Wartung [5] – Dopplungs-Kandidaten

Die Dopplungsprüfung dient als **Review-Hilfe**, nicht als Löschautomatik.

Ein Musik-Element wird als Kandidat verknüpft, wenn mindestens eines dieser starken Kriterien erfüllt ist:

- identische normalisierte Kombination aus Artist + Title,
- identischer gespeicherter Dateipfad,
- identische gültige ISRC.

Unterschiedliche Laufzeiten verhindern eine Markierung bewusst nicht, weil Radio Edit, Albumversion, Remaster oder andere Varianten anschließend von einem Menschen bewertet werden sollen.

### Was wird geschrieben?

Kandidaten erhalten das Attribut:

`DOPPELUNG=JA`

Kein Track wird automatisch gelöscht oder als „falsch“ erklärt.

Beim nächsten Scan wird der Status neu aus der aktuellen Datenbank berechnet. Existiert der frühere Partner nicht mehr, entfernt der Restorer die veraltete `DOPPELUNG`-Markierung wieder.

### Empfohlener Smart Folder in mAirList

Lege `DOPPELUNG` als Standard-Attribut an bzw. mache es in mAirList verfügbar und verwende einen Filter wie:

- Attribut: `DOPPELUNG`
- Bedingung: `is one of`
- Wert: `JA`

### Sicherheit

Wenn eine Änderung notwendig ist:

1. Integritätsprüfung
2. Backup
3. eine Datenbanktransaktion für den neuen Status
4. erneute Integritätsprüfung

---

## 14. Wartung [6] – Fehlende BPM direkt ergänzen

Diese Funktion ist für die reine BPM-Nachpflege gedacht und bleibt auch nach Integration der BPM-Suche in den normalen Fetch bestehen.

Sie arbeitet nur auf dateibasierten Musik-Elementen ohne gültigen BPM.

### rekordbox-XML

Die gleiche per Datenbank gespeicherte rekordbox-XML-Auswahl wie im normalen Fetch kann verwendet werden. rekordbox liefert `AverageBpm`; der Restorer übernimmt ihn nur bei exakt passendem Dateipfad.

### Fallbacks

Falls rekordbox keinen passenden Wert liefert:

1. BPM aus lokalem Audio-Tag lesen.
2. MusicBrainz Recording möglichst über ISRC bzw. konservatives Matching identifizieren.
3. AcousticBrainz Low-Level-BPM abfragen.

Bei mehreren AcousticBrainz-Analysen wird nur ein enger Konsens akzeptiert. Unklare Half-/Double-Time-Situationen werden verworfen.

### Vorschau, Diagnose und Review-CSV

Vor dem Schreiben zeigt die Wartung eine Vorschau und eine Zusammenfassung. Zusätzlich entsteht im `Data`-Ordner eine vollständige BPM-Review-CSV mit unter anderem:

- ID
- Artist
- Title
- vorgeschlagenem BPM
- vorhandenem BPM
- ursprünglichem Quellen-BPM
- Quelle
- Status
- AcousticBrainz-Konsens
- Recording-MBID
- Matching-Methode

Nichttreffer und Fehler werden nach Ursache getrennt ausgewiesen, z. B.:

- Audiodatei nicht erreichbar
- Audio-Tag nicht lesbar
- kein eindeutiges MusicBrainz Recording
- MusicBrainz Netzwerk/Timeout, 429, 5xx oder anderer HTTP-Fehler
- AcousticBrainz ohne Datensatz
- AcousticBrainz ohne nutzbaren BPM
- kein sicherer AcousticBrainz-Konsens
- AcousticBrainz Netzwerk/Rate-Limit/Serverfehler

### Half-/Double-Time-Konflikte

Ist bereits ein BPM vorhanden und rekordbox liefert einen deutlich abweichenden Wert, wird nichts überschrieben. Besonders typische 2:1-Konflikte wie `180 ↔ 90` werden in der Review-CSV als `HALF_DOUBLE_KONFLIKT` sichtbar gemacht.

Das ist absichtlich nur eine Warnung: Unterschiedliche DJ-/Analyseprogramme können dasselbe musikalische Tempo in Half- oder Double-Time zählen.

### Sicherheit

Nach ausdrücklicher Bestätigung folgen:

1. Integritätsprüfung
2. Backup
3. atomare BPM-Transaktion
4. Live-Schutz gegen inzwischen vorhandene BPM
5. erneute Integritätsprüfung

`RESTAURIERT` wird durch diese Wartungsfunktion **nicht verändert**.

AcousticBrainz wird mit mindestens 1,05 Sekunden Basisabstand angesprochen; zusätzlich werden die dynamischen Rate-Limit-Header berücksichtigt.

---

## 15. rekordbox-Workflow für große Bibliotheken

Für eine hohe BPM-Abdeckung ist folgender Ablauf empfehlenswert:

1. Musikbibliothek in rekordbox importieren.
2. Tracks vollständig analysieren lassen.
3. Collection als rekordbox XML exportieren.
4. Im Restorer diese XML für den normalen Fetch oder Wartung [6] auswählen.
5. rekordbox kann später erneut analysiert/exportiert werden; solange der Export am gleichen Pfad liegt, verwendet der Restorer beim nächsten Lauf automatisch den gespeicherten Pfad.

Der Restorer schreibt nichts in die rekordbox-Library zurück.

---

## 16. Fehlerfälle und Diagnose

### Datenbank ist gesperrt

mAirList oder ein anderes Programm hält die `.mldb` geöffnet. Anwendung schließen bzw. mit einer echten Kopie arbeiten.

### SQLite-Integritätsprüfung schlägt fehl

Der Restorer bricht den Schreibvorgang ab. Die Inkonsistenz bestand bereits vor dem geplanten Schreiben. Der Restorer führt **keine automatische REINDEX-/Repair-Aktion** aus.

### API-Fehler

Bei vorübergehenden Metadaten-API-Fehlern führt der normale Fetch automatisch bis zu drei komplette Track-Wiederholungen aus (2/5/10 s; Server-`Retry-After` wird respektiert). Erst danach bleibt ein Track bei anhaltendem Fehler offen. Nicht-transiente 4xx-Fehler werden nicht automatisch wiederholt. Bei reinen BPM-Fallback-Fehlern können die übrigen Metadaten trotzdem weiterbearbeitet werden; fehlende BPM können später über Wartung [6] ergänzt werden.

### Audiodatei nicht gefunden

Für Datei-Tags/BPM oder den Datei-Tagger müssen lokale Pfade aufgelöst werden können. Beim BPM-Matching kann der Restorer mAirList-Storage-Locations aus der Datenbank auflösen; der Datei-Tagger bietet zusätzlich die manuelle Eingabe lokaler Basisordner an.

### rekordbox XML passt nicht

Nur exakte Dateipfade werden verwendet. Wurde die Musik seit dem rekordbox-Export verschoben oder unterscheiden sich Storage-Pfade, fällt der Restorer auf die nächsten BPM-Quellen zurück.

---

## 17. Kommandozeile für Entwickler/Power-User

Die normale Release-Nutzung erfolgt über das interaktive Menü. Im Python-Quellbetrieb stehen zusätzlich Phasen wie `fetch`, `review`, `apply`, `maintenance` und `check_update` zur Verfügung.

Für Fetch gibt es unter anderem:

- `--full`
- `--no-breaks`
- `--rekordbox-xml <pfad>`
- `--lang de|en|nl`

Die EXE-Nutzung über das Hauptmenü bleibt der empfohlene Weg.

---

## 18. Was der Restorer bewusst nicht macht

- keine Änderung von Tracklaufzeiten
- keine Audioanalyse oder Loudness-Berechnung
- keine Konvertierung von Audioformaten
- keine automatische Löschung von Dopplungen
- keine automatische Reparatur von SQLite-Strukturen
- keine Ableitung der Gesangssprache aus einem unsicheren MusicBrainz-Release-Feld
- kein automatisches Überschreiben bestehender gültiger BPM
- keine Unterstützung von mAirList-Netzwerkdatenbanken

---

## 19. Tests und Release-Sicherheit

Der Quellstand enthält Regressionstests, die unter anderem Workspace-Trennung, Lyrics-Ausschluss, Apply-Schutz, Full-Fetch-Ausnahme, Dopplungsstatus, BPM-Konsens, rekordbox-Pfadmatching, Half-/Double-Time-Schutz, API-Retry-/Rate-Limits einschließlich Track-Level-Retry sowie Backup-/Bestätigungslogik prüfen.

Für Entwickler:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions führt zusätzlich einen Compile-Check und die Regressionstests unter Windows aus.

---

## 20. Lizenz und Support

Der mAirList DB Restorer ist **source-available Freeware**. Die genauen Nutzungs- und Weitergabebedingungen stehen in der Datei `LICENSE`.

Bug-Reports und Feature-Wünsche bitte über die offiziellen Projektkanäle einreichen: GitHub Issues bzw. den offiziellen Release-Thread im mAirList-Forum.
