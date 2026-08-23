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
Zusätzlich benötigst du (kostenlose) API-Zugangsdaten für Discogs:

Erstelle einen Account auf discogs.com.

Gehe zu den Entwickler-Einstellungen (Settings -> Developers).

Erstelle eine neue App/Token und kopiere dir deinen "Consumer Key" und das "Consumer Secret".

3. Der Workflow (Bedienung)
WICHTIG VORAB:
Arbeite NIEMALS mit der Datenbank-Datei (.mldb), die mAirList in diesem Moment geöffnet hat! mAirList sperrt die Datei im laufenden Betrieb. Wenn das Skript versucht, gleichzeitig zu schreiben, kann die Datenbank beschädigt werden.
➡️ Erstelle dir immer eine KOPIE deiner .mldb-Datei auf dem Desktop!

Vorbereitung: Datenbank auswählen
Starte das Tool über die Datei Restore.bat. Wähle deine Sprache aus.
Wähle [0] im Menü. Das Skript fragt dich nun nach dem Pfad zu deiner Datenbank.

PRO-TIPP: Du musst den Pfad nicht mühsam eintippen. Du kannst die .mldb-Datei einfach aus dem Windows-Explorer mit der Maus direkt in das Konsolenfenster ziehen (Drag & Drop) und Enter drücken! Das Menü merkt sich diese Datei nun für alle folgenden Schritte.

Beim allerersten Start fragt dich das Skript nach deinen Discogs-Keys und einer Kontakt-E-Mail für MusicBrainz (Vorgabe der API). Danach beginnt der Prozess:

Schritt 1: Metadaten laden (Smart-Abruf)
Wähle [1]. Das Skript liest deine Datenbank-Kopie ein und sucht für jeden Track, der noch nicht bearbeitet wurde, nach Metadaten. Die Original-Werte bleiben dabei völlig unangetastet. Der Fortschritt wird kontinuierlich zwischengespeichert. Du kannst den Vorgang jederzeit mit Strg+C abbrechen und später fortsetzen.

Schritt 2: Daten kontrollieren (Kontrolle)
Wähle [3] oder [4]. Hier bekommst du die Vorschläge des Skripts präsentiert. Du kannst jeden Vorschlag (Jahr, Genre, Album, Label) mit "Enter" ablehnen, mit "j" annehmen oder eigenen Text eintippen.

Live Re-Fetch: Wenn du beim Artist oder Titel eine eigene Korrektur eintippst (z. B. einen Schreibfehler korrigierst), holt das Skript sofort im Hintergrund die neuen, passenden Daten für deine Korrektur!

Schritt 3: In mAirList speichern (Speichern)
Wähle [5]. Das Skript schreibt alle von dir freigegebenen Metadaten in deine Datenbank-KOPIE zurück.
Wenn der Vorgang abgeschlossen ist, kannst du die Kopie wieder an ihren ursprünglichen Ort verschieben (während mAirList geschlossen ist) oder die Datenbank in der mAirList-Konfiguration neu verknüpfen.

4. Das "Restauriert" Flag (Update-Logik)
Das Skript setzt beim Speichern in mAirList das Attribut RESTAURIERT = JA für jeden bearbeiteten Track.
Tracks mit diesem Flag werden bei zukünftigen Durchläufen automatisch übersprungen.

Fällt dir später im laufenden Radiobetrieb auf, dass ein Track doch falsche Tags hat? Kein Problem: Lösche in mAirList einfach das RESTAURIERT-Attribut bei diesem Track. Beim nächsten Skript-Lauf erkennt das Tool, dass der Track "freigegeben" wurde und ruft ihn komplett neu ab!

5. Transparenz, KI-Nutzung & Support
Ein offenes Wort zur Entstehung: Dieses Skript wurde maßgeblich mit der Unterstützung von Künstlicher Intelligenz (Google Gemini) entwickelt. Mir ist Transparenz hier sehr wichtig. Ich bitte darum, von Kritik an der Entstehungsweise abzusehen. Im Fokus sollte stehen, was dieses Tool für die mAirList-Community leistet und wie viele Stunden mühsamer Handarbeit es euch ersparen kann.

WICHTIGER DISCLAIMER: Weder die KI noch die Datenbanken von MusicBrainz oder Discogs sind unfehlbar. Aufgrund der gigantischen Menge an unterschiedlichen Schreibweisen, Remixes, Re-Releases und Namensgleichheiten (bei Artist, Titel oder Label) können gelegentlich falsche Metadaten geliefert werden. Das Skript fängt durch interne Filter und Logiken sehr viel ab – aber restlos ALLES abzufangen, ist schlicht unmöglich.
Es ist daher zu 100 % ratsam und notwendig, die Ergebnisse im Review-Schritt oder später in mAirList kritisch zu hinterfragen und zu prüfen!

SUPPORT:
Technischen Support (soweit es mir möglich ist) leiste ich ausschließlich über die Issue-Funktion hier auf GitHub. Bitte keine Support-Anfragen über andere Kanäle oder Foren.

🇬🇧 ENGLISH
Anyone who maintains a music database knows the problem: missing release years, empty genre fields, incomplete label codes, or missing album titles. The mAirList DB Restorer automates this tedious manual work for you.

The tool analyzes your local mAirList SQLite database (.mldb), searches for the missing metadata via the MusicBrainz and Discogs APIs, and safely writes the corrected values back into the database.

1. The Features: What Happens Under the Hood?
The script doesn't just search blindly; it uses several safety nets to avoid incorrect tags:

Smart Cleaning: Artist and title are cleaned before searching. Different spellings of features (ft., featuring) are standardized.

Intelligent Matching (Levenshtein): The tool checks the percentage similarity of the search results. This prevents the API from accidentally assigning the breakcore artist "Duran Duran Duran" to "Duran Duran".

Outlier Filter (Median & Gap Logic): APIs often contain incorrect user entries. The script calculates the average of all found release years and ignores absurd outliers (e.g., a release year of 1945 for a 2004 track).

OAD Protection: Virtual and physical folders named "OAD" (On Air Design) are strictly ignored. Jingle packages thus remain untouched.

Masked Configuration: Your API keys are stored locally masked with Base64 so they are not directly readable in plain text in the config.json.

NOTE: Base64 is NOT encryption, just encoding - it can be decoded in seconds with any online tool. The protection only applies to accidental glances, not intentional reading. Therefore, do not share your config.json (e.g., do not upload it when asking for support or sharing the tool).

2. Requirements & Installation
Since this is a Python script, you need to install Python and three additional packages once:

Download and install Python (IMPORTANT: Make sure to check the box "Add Python to PATH" during installation!).

Open the Windows Command Prompt. (Tip: Press Windows Key + R, type cmd, and press Enter).

Then install the required libraries with the following command:

Bash
pip install pandas requests rich
Additionally, you need (free) API credentials for Discogs:

Create an account on discogs.com.

Go to the developer settings (Settings -> Developers).

Create a new App/Token and copy your "Consumer Key" and "Consumer Secret".

3. The Workflow (Usage)
IMPORTANT BEFORE YOU START:
NEVER work with the database file (.mldb) that is currently open in mAirList! mAirList locks the file while running. If the script tries to write at the same time, the database can be corrupted.
➡️ Always create a COPY of your .mldb file on your desktop!

Preparation: Select Database
Start the tool using the Restore.bat file. Select your language.
Select [0] in the menu. The script will now ask for the path to your database.

PRO TIP: You don't have to type the path manually. You can simply drag and drop the .mldb file from the Windows Explorer directly into the console window and press Enter! The menu will now remember this file for all subsequent steps.

On the very first start, the script will ask you for your Discogs keys and a contact email for MusicBrainz (API requirement). After that, the process begins:

Step 1: Fetch Metadata (Smart Fetch)
Select [1]. The script reads your database copy and searches for metadata for each track that has not yet been processed. The original values remain completely untouched. The progress is continuously saved. You can abort the process at any time with Ctrl+C and resume it later.

Step 2: Review Data (Review)
Select [3] or [4]. Here you are presented with the script's suggestions. You can reject any suggestion (year, genre, album, label) with "Enter", accept it with "y", or type your own text.

Live Re-Fetch: If you type your own correction for Artist or Title (e.g., correcting a typo), the script immediately fetches the new, matching data for your correction in the background!

Step 3: Save to mAirList (Apply)
Select [5]. The script writes all the metadata you approved back into your database COPY.
When the process is complete, you can move the copy back to its original location (while mAirList is closed) or reconnect the database in the mAirList configuration.

4. The "RESTAURIERT" Flag (Update Logic)
When saving to mAirList, the script sets the attribute RESTAURIERT = JA for each processed track.
Tracks with this flag are automatically skipped during future runs.

If you notice later during live radio operation that a track still has wrong tags? No problem: Simply delete the RESTAURIERT attribute for this track in mAirList. On the next script run, the tool will recognize that the track has been "released" and will re-fetch it completely!

5. Transparency, AI Usage & Support
A candid word about the development: This script was largely developed with the assistance of Artificial Intelligence (Google Gemini). Transparency is very important to me here. I kindly ask you to refrain from criticizing how the code was created. The focus should remain on the utility this tool provides to the mAirList community and the countless hours of manual labor it saves you.

IMPORTANT DISCLAIMER: Neither the AI nor the databases of MusicBrainz or Discogs are flawless. Due to the massive amount of different spellings, remixes, re-releases, and identical names (for artists, titles, or labels), incorrect metadata can occasionally be returned. The script catches a lot through internal filters and logic – but catching absolutely EVERYTHING is simply impossible.
Therefore, it is 100% recommended and necessary to critically review and verify the results during the review step or later in mAirList!

SUPPORT:
Technical support (as far as I am able to provide it) is handled exclusively via the issue tracker here on GitHub. Please do not send support requests through other channels or forums.
