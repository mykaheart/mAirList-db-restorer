# mAirList DB Restorer v0.4.7 Beta
**Ein Metadaten-Reparatur-Tool / Metadata Repair Tool for mAirList**

---

## 🇩🇪 DEUTSCH

Jeder, der eine Musikdatenbank pflegt, kennt das Problem: Fehlende Jahreszahlen, leere Genre-Felder, unvollständige Labelcodes oder fehlende Alben. Der mAirList DB Restorer nimmt dir diese mühsame Handarbeit ab. 

Das Tool analysiert deine lokale mAirList SQLite-Datenbank (`.mldb`), sucht über die APIs von MusicBrainz und Discogs nach den fehlenden Metadaten und schreibt die korrigierten Werte sicher in die Datenbank zurück.

---

### 1. Die Features: Was passiert unter der Haube?
Das Skript sucht nicht einfach blind drauflos, sondern arbeitet mit mehreren Sicherheitsnetzen, um falsche Tags zu vermeiden:

* **Smart Cleaning:** Vor der Suche werden Artist und Titel bereinigt. Verschiedene Schreibweisen von Features (`ft.`, `featuring`) werden standardisiert.
* **Intelligentes Matching (Levenshtein):** Das Tool prüft die prozentuale Ähnlichkeit der Suchergebnisse. So wird verhindert, dass die API für "Duran Duran" versehentlich den Breakcore-Artist "Duran Duran Duran" zuordnet.
* **Ausreißer-Filter (Median & Lücken-Logik):** APIs enthalten oft fehlerhafte User-Einträge. Das Skript berechnet den Mittelwert aller gefundenen Release-Jahre und ignoriert absurde Ausreißer (z. B. ein Release-Jahr 1945 für einen 2004er Track).
* **OAD-Schutz:** Virtuelle und physische Ordner, die "OAD" (On Air Design) heißen, werden konsequent ignoriert. Jingle-Pakete bleiben also unangetastet.
* **Maskierte Konfiguration:** Deine API-Keys werden lokal mit Base64 maskiert abgespeichert, damit sie nicht direkt im Klartext in der `config.json` stehen.
  
  > **HINWEIS:** Base64 ist *KEINE* Verschlüsselung, sondern nur eine Kodierung – sie lässt sich mit jedem Online-Tool in Sekunden zurückrechnen. Der Schutz gilt nur vor versehentlichem Draufschauen, nicht vor absichtlichem Auslesen. Gib deine `config.json` daher nicht weiter (z. B. nicht mit hochladen, wenn du Support-Anfragen stellst oder das Tool mit anderen teilst).

---

### 2. Voraussetzungen & Installation
Da es sich um ein Python-Skript handelt, musst du einmalig Python und drei Zusatzpakete installieren:

1. Lade dir [Python herunter](https://www.python.org/downloads/) und installiere es (**WICHTIG:** Setze bei der Installation unbedingt den Haken bei *"Add Python to PATH"*!).
2. Öffne die Windows-Eingabeaufforderung. *(Tipp: Drücke die Windows-Taste + R, tippe `cmd` ein und drücke Enter)*.
3. Installiere dann die benötigten Bibliotheken mit folgendem Befehl:
   ```bash
   pip install pandas requests rich
