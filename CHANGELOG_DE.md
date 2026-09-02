# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

## [0.51.01 Beta] - 2026-09-02
### Geändert
- **Migration auf eine eigenständige ausführbare Datei (Das "All-in-One"-Update):** Das Tool wurde vollständig von einer hybriden Batch/Python-Architektur zu einer komplett eigenständigen Python-Anwendung umgebaut, die als einzelne kompilierte `.exe`-Datei verteilt werden kann. Benutzer müssen Python oder Abhängigkeiten nicht mehr manuell installieren. `Restore.bat` wurde als veraltet eingestuft und entfernt.
- **Integriertes interaktives Menü:** Das bisherige Windows-Batch-Startmenü wurde vollständig durch eine native, dreisprachige und auf `rich` basierende Terminaloberfläche ersetzt, die direkt in `main.py` integriert ist. Dadurch wird eine deutlich sauberere und robustere Benutzererfahrung geboten.

### Hinzugefügt
- **Permanente Sprachauswahl:** Die bevorzugte Sprache des Benutzers wird nun automatisch in `config.json` gespeichert. Bei nachfolgenden Starts wird die anfängliche Sprachauswahl übersprungen. Eine neue Option `[9]` wurde dem Hauptmenü hinzugefügt, um die Sprache jederzeit zu ändern.
- **Ausführungs-"Airbag" (Absturzvermeidung):** Am Einstiegspunkt der Anwendung wurde eine globale Fehlerbehandlung implementiert. Wenn das Tool beim Start per Doppelklick auf einen kritischen Fehler stößt, wird das Terminalfenster nicht mehr kommentarlos geschlossen. Stattdessen wird der vollständige Fehler-Traceback angezeigt und auf eine Eingabe des Benutzers gewartet.
- **Dynamische Erkennung des Arbeitsverzeichnisses:** Das Tool erkennt nun intelligent seine Laufzeitumgebung (gefrorene `.exe` gegenüber normalem `.py`-Skript) und setzt explizit das korrekte Arbeitsverzeichnis. Dadurch werden `PermissionError`-Fehler (z. B. `[WinError 5]`) beim Erstellen des `Data`-Ordners verhindert, wenn das Tool aus einem Systemkontext heraus gestartet wird.

## [0.50.28 Beta] - 2026-09-02
### Hinzugefügt
- **Aufräumen des Arbeitsbereichs (Data-Verzeichnis):** Das Skript erstellt nun automatisch einen Unterordner `Data` und verschiebt beim Ausführen alle Sitzungsdateien (`.csv` und `.log`) nahtlos dorthin. So bleibt das Hauptverzeichnis sauber und übersichtlich, ohne bisherigen Fortschritt zu verlieren.
- **Übersetzung der Elementtypen:** Ein umfassendes Wörterbuch wurde hinzugefügt, um interne mAirList-Elementtypen in lesbare Bezeichnungen zu übersetzen (z. B. "Music" -> "Musik", "Voice" -> "Moderation"). Dies wird während der Fetch-Phase automatisch auf leere Felder angewendet und ist außerdem als neue dedizierte Sammelaufgabe im Wartungsmenü verfügbar.

### Geändert
- **Verbesserte Benutzerführung:** Erfolgsmeldungen am Ende der Fetch- und Review-Phasen verweisen nun ausdrücklich auf die richtige numerische Option im Menü (z. B. "Option [7] (Apply)"), anstatt rohe Python-CLI-Befehle anzuzeigen. Dadurch wird Verwirrung bei den Benutzern vermieden.

### Behoben
- **Fehler bei der Batch-Menü-Navigation:** Ein Syntaxfehler in `Restore.bat`, bei dem kaufmännische Und-Zeichen (`&`) in Menübeschreibungen dazu führten, dass die Windows-Eingabeaufforderung Befehle falsch interpretierte, wurde behoben. Dadurch funktionieren die Optionen "Overnight" und "Full Fetch" wieder vollständig.

## [0.5.2 Beta] - 2026-08-30
### Hinzugefügt
- **Niederländische Sprachunterstützung:** Das Tool ist nun vollständig dreisprachig! Eine vollständige niederländische Lokalisierung für die Konsolenoberfläche, Review-Abfragen und das `Restore.bat`-Startmenü wurde hinzugefügt, um die große D&R-/mAirList-Community in den Niederlanden zu unterstützen.

## [0.5.1 Beta] - 2026-08-30
### Geändert
- **Startup-UX / Update-Prüfung:** Die GitHub-Update-Prüfung wurde in eine eigene Ausführungsphase (`check_update`) ausgelagert. Das Skript `Restore.bat` führt diese Prüfung nun *vor* dem Laden des Haupt-Datenbankmenüs aus. Dadurch sind Update-Hinweise deutlich sichtbarer und werden nicht mehr unmittelbar von der Benutzeroberfläche überschrieben.
- **Sanfte Übergänge:** Wenn ein Update verfügbar ist, pausiert die Konsole, damit der Benutzer den Hinweis lesen kann. Wenn das Tool aktuell ist, wird zwei Sekunden lang eine kurze Bestätigung angezeigt, bevor nahtlos in das Hauptmenü gewechselt wird.

## [0.5.0 Beta] - 2026-08-29
### Hinzugefügt
- **Erweitertes Live-Neuabrufen:** Die Live-Re-Fetch-Logik während der Review-Phase reagiert nun ausdrücklich auf manuelle Änderungen in den Feldern "Year" und "Album". Änderungen an diesen Feldern lösen eine gezielte API-Anfrage aus, um die exakte Veröffentlichung abzurufen. Dadurch wird die Genauigkeit der vorgeschlagenen Labels, Label Codes und Genres deutlich verbessert.

### Geändert
- **Umfassende Architekturüberarbeitung:** Das monolithische `restore.py` wurde in eine saubere, modulare Struktur (`main.py`, `api.py`, `db.py`, `utils.py`) aufgeteilt, um Wartbarkeit und Lesbarkeit zu verbessern und zukünftige Integrationen zu ermöglichen.
- **CLI-Ausführung:** Der primäre Ausführungsbefehl wurde von `py restore.py` auf `py main.py` geändert. `Restore.bat` und die CLI-Argumente wurden entsprechend angepasst.

## [0.4.22 Beta] - 2026-08-29
### Geändert
- **Genre-Konsolidierung:** `ALLOWED_GENRES` wurde massiv auf 10 Kernkategorien (Pop, EDM, Blues, Hiphop, Rap, Rock, Classic Rock, R and B, Soul, Reggae) vereinfacht, die für die Rotationsplanung optimiert sind. Das `GENRE_SYNONYMS`-Mapping wurde erweitert, um komplexe API-Mikrogenres automatisch zu erkennen und zuzuordnen (z. B. "Nu Metal" -> "Rock", "Deep House" -> "EDM").

## [0.4.21 Beta] - 2026-08-29
### Optimiert
- **API-Konkurrenz (paralleler Abruf):** `ThreadPoolExecutor` wurde in den Fetch- und Live-Re-Fetch-Phasen implementiert. Die MusicBrainz- und Discogs-APIs werden nun gleichzeitig abgefragt, wodurch die Netzwerk-Wartezeit pro Track drastisch reduziert wird.
- **Datenbank-Sammelschreiben:** Die `apply`-Phase wurde überarbeitet, um SQLite-Transaktionen zu bündeln. Anstatt Track-Attribute Zeile für Zeile zu schreiben, verwendet das Skript nun `executemany()` für Sammelaktualisierungen. Dadurch wird der abschließende Speichervorgang der Datenbank erheblich beschleunigt und die Dauer der Sperrung der `.mldb`-Datei minimiert.

## [0.4.20 Beta] - 2026-08-28
### Hinzugefügt
- **Komfortabler Review:** Die Review-Abfragen akzeptieren nun eine leere Eingabe (Enter oder Return drücken) als Bestätigung zum Übernehmen von Vorschlägen. Dadurch wird das Tagging großer Tracklisten erheblich beschleunigt.

## [0.4.19 Beta] - 2026-08-28
### Hinzugefügt
- **Sprachgedächtnis:** Benutzerdefinierte Sprachen, die während der Review-Phase manuell eingegeben werden (z. B. "Französisch"), werden nun dauerhaft im `CUSTOM_LANGS`-Array von `config.json` gespeichert. Das Skript erweitert das Sprachauswahlmenü für alle nachfolgenden Tracks dynamisch.
- **Rückgängig-Funktion (Schritt zurück):** Die statische `for`-Schleife in der Review-Phase wurde durch eine indexbasierte `while`-Schleife ersetzt. Benutzer können nun bei jeder Abfrage `<` oder `b` (Back) eingeben, um sicher zum vorherigen Track zurückzuspringen und Tippfehler zu korrigieren.

## [0.4.18 Beta] - 2026-08-28
### Hinzugefügt
- **Sprachkürzel:** Für die häufigsten Sprachen wurden während der manuellen Review-Phase schnelle numerische Auswahlkürzel eingeführt (z. B. `1` für Englisch, `2` für Deutsch), um den Tagging-Workflow deutlich zu beschleunigen.

## [0.4.17 Beta] - 2026-08-23
### Hinzugefügt
- **Dynamisches Logging:** Logdateien enthalten nun dynamisch den Datenbanknamen und einen Zeitstempel (z. B. `DBName_20260823_141500.log`), um Überschreiben zu verhindern und die Fehlersuche zu verbessern.
- **Proaktive Datenbanksperrprüfung:** Das Skript überprüft nun direkt zu Beginn der `fetch`- und `review`-Phasen ausdrücklich, ob die `.mldb`-Datei von mAirList gesperrt ist. Dadurch werden Lese-/Schreibkonflikte verhindert.
- **Feedback zur Ignorierliste:** Vor Beginn des Fetch-Prozesses wird nun eine deutlich sichtbare Erfolgsmeldung mit der genauen Anzahl der erfolgreich ignorierten Tracks (z. B. OAD, Jingles, News) angezeigt.

### Behoben
- **SQLite-Schemafehler:** Ein kritischer Fehler wurde behoben, bei dem das Skript fälschlicherweise die Tabelle `folder_items` statt `item_folders` abfragte. Dadurch hatte die Ignorierliste für Ordner zuvor stillschweigend nicht funktioniert.
- **Vermeidung stiller Abstürze (Der Airbag):** Die Haupt-Fetch-Schleife wurde mit einer robusten Fehlerbehandlung versehen. Unterbrochene API-Verbindungen, Timeouts oder ungültige Zeichen in Track-Tags führen nicht mehr zum Absturz des gesamten Skripts; Fehler werden protokolliert und das Skript fährt nahtlos mit dem nächsten Track fort.
- **Fehler bei der Terminal-Hervorhebung:** Der standardmäßige Syntax-Highlighter der `rich`-Konsole (`highlight=False`) wurde deaktiviert, um zu verhindern, dass zufällige Wörter wie 'true' oder reine Zahlen in der Terminalausgabe fälschlicherweise eingefärbt werden.
- **Duran-Duran-VIP-Fix:** "Duran Duran" wurde zum `ARTIST_FIXES`-Wörterbuch hinzugefügt, damit die MusicBrainz-API die legendäre Band aus den 80ern nicht mit dem amerikanischen Breakcore-Künstler "Duran Duran Duran" verwechselt.
- **Batch-Datei bleibt geöffnet:** Der `exit`-Befehl in `Restore.bat` wurde durch `pause` ersetzt, damit das Terminalfenster nach der Ausführung oder bei unerwarteten Abstürzen geöffnet bleibt.
