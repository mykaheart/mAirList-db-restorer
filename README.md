==mAirList DB Restorer v0.4.5 Beta
 
 Ein Metadaten-Reparatur-Tool für die mAirList-Community

--- DEUTSCH --------------------------------------------------------------------

Jeder, der eine Musikdatenbank pflegt, kennt das Problem: Fehlende Jahreszahlen, 
leere Genre-Felder, unvollständige Labelcodes oder fehlende Alben. Der mAirList 
DB Restorer nimmt dir diese mühsame Handarbeit ab. 

Das Tool analysiert deine lokale mAirList SQLite-Datenbank (.mldb), sucht über 
die APIs von MusicBrainz und Discogs nach den fehlenden Metadaten und schreibt 
die korrigierten Werte sicher in die Datenbank zurück.

--------------------------------------------------------------------------------
 1. DIE FEATURES: WAS PASSIERT UNTER DER HAUBE?
--------------------------------------------------------------------------------
Das Skript sucht nicht einfach blind drauflos, sondern arbeitet mit mehreren 
Sicherheitsnetzen, um falsche Tags zu vermeiden:

* Smart Cleaning: Vor der Suche werden Artist und Titel bereinigt. Verschiedene 
  Schreibweisen von Features (ft., featuring) werden standardisiert.
* Intelligentes Matching (Levenshtein): Das Tool prüft die prozentuale 
  Ähnlichkeit der Suchergebnisse. So wird verhindert, dass die API für 
  "Duran Duran" versehentlich den Breakcore-Artist "Duran Duran Duran" zuordnet.
* Ausreißer-Filter (Median & Lücken-Logik): APIs enthalten oft fehlerhafte User-Einträge. 
  Das Skript berechnet den Mittelwert aller gefundenen Release-Jahre und 
  ignoriert absurde Ausreißer (z. B. ein Release-Jahr 1945 für einen 2004er Track).
* OAD-Schutz: Virtuelle und physische Ordner, die "OAD" (On Air Design) heißen, 
  werden konsequent ignoriert. Jingle-Pakete bleiben also unangetastet.
* Maskierte Konfiguration: Deine API-Keys werden lokal mit Base64 maskiert 
  abgespeichert, damit sie nicht direkt im Klartext in der config.json stehen.
  Hinweis: Base64 ist KEINE Verschlüsselung, sondern nur eine Kodierung – sie
  lässt sich mit jedem Online-Tool in Sekunden zurückrechnen. Der Schutz gilt
  nur vor versehentlichem Draufschauen, nicht vor absichtlichem Auslesen.
  Gib deine config.json daher nicht weiter (z. B. nicht mit hochladen, wenn du
  Support-Anfragen stellst oder das Tool mit anderen teilst).

--------------------------------------------------------------------------------
 2. VORAUSSETZUNGEN & INSTALLATION
--------------------------------------------------------------------------------
Da es sich um ein Python-Skript handelt, musst du einmalig Python und drei 
Zusatzpakete installieren:

1. Lade dir Python (https://www.python.org/downloads/) herunter und installiere es (WICHTIG: Setze bei der 
   Installation unbedingt den Haken bei "Add Python to PATH"!).
2. Öffne die Windows-Eingabeaufforderung. 
   (Tipp: Drücke die Windows-Taste + R, tippe "cmd" ein und drücke Enter).
   Installiere dann die benötigten Bibliotheken mit folgendem Befehl:
   
   pip install pandas requests rich

Zusätzlich benötigst du (kostenlose) API-Zugangsdaten für Discogs:
1. Erstelle einen Account auf discogs.com
2. Gehe zu den Entwickler-Einstellungen (Settings -> Developers)
3. Erstelle eine neue App/Token und kopiere dir deinen "Consumer Key" 
   und das "Consumer Secret".

--------------------------------------------------------------------------------
 3. DER WORKFLOW (BEDIENUNG)
--------------------------------------------------------------------------------
WICHTIG VORAB: 
Arbeite NIEMALS mit der Datenbank-Datei (.mldb), die mAirList in diesem Moment 
geöffnet hat! mAirList sperrt die Datei im laufenden Betrieb. Wenn das Skript 
versucht, gleichzeitig zu schreiben, kann die Datenbank beschädigt werden. 
-> Erstelle dir immer eine KOPIE deiner .mldb-Datei auf dem Desktop!

VORBEREITUNG: DATENBANK AUSWÄHLEN
Starte das Tool über die Datei "Restore.bat". Wähle deine Sprache aus.
Wähle [0] im Menü. Das Skript fragt dich nun nach dem Pfad zu deiner Datenbank. 
PRO-TIPP: Du musst den Pfad nicht mühsam eintippen. Du kannst die .mldb-Datei 
einfach aus dem Windows-Explorer mit der Maus direkt in das Konsolenfenster 
ziehen (Drag & Drop) und Enter drücken! Das Menü merkt sich diese Datei nun für 
alle folgenden Schritte.

Beim allerersten Start fragt dich das Skript nach deinen Discogs-Keys und einer 
Kontakt-E-Mail für MusicBrainz (Vorgabe der API). Danach beginnt der Prozess:

SCHRITT 1: METADATEN LADEN (Smart-Abruf)
Wähle [1]. Das Skript liest deine Datenbank-Kopie ein und sucht für jeden Track, 
der noch nicht bearbeitet wurde, nach Metadaten. Die Original-Werte bleiben 
dabei völlig unangetastet. Der Fortschritt wird kontinuierlich zwischengespeichert. 
Du kannst den Vorgang jederzeit mit Strg+C abbrechen und später fortsetzen.

SCHRITT 2: DATEN KONTROLLIEREN (Kontrolle)
Wähle [3] oder [4]. Hier bekommst du die Vorschläge des Skripts präsentiert. 
Du kannst jeden Vorschlag (Jahr, Genre, Album, Label) mit "Enter" ablehnen, mit 
"j" annehmen oder eigenen Text eintippen.
- Live Re-Fetch: Wenn du beim Artist oder Titel eine eigene Korrektur eintippst 
  (z.B. einen Schreibfehler korrigierst), holt das Skript sofort im Hintergrund 
  die neuen, passenden Daten für deine Korrektur!

SCHRITT 3: IN MAIRLIST SPEICHERN (Speichern)
Wähle [5]. Das Skript schreibt alle von dir freigegebenen Metadaten in deine 
Datenbank-KOPIE zurück. 
Wenn der Vorgang abgeschlossen ist, kannst du die Kopie wieder an ihren 
ursprünglichen Ort verschieben (während mAirList geschlossen ist) oder die 
Datenbank in der mAirList-Konfiguration neu verknüpfen.

--------------------------------------------------------------------------------
 4. DAS "RESTAURIERT" FLAG (Update-Logik)
--------------------------------------------------------------------------------
Das Skript setzt beim Speichern in mAirList das Attribut "RESTAURIERT" = "JA" 
für jeden bearbeiteten Track. 
Tracks mit diesem Flag werden bei zukünftigen Durchläufen automatisch übersprungen. 
Fällt dir später im laufenden Radiobetrieb auf, dass ein Track doch falsche 
Tags hat? Kein Problem: Lösche in mAirList einfach das "RESTAURIERT"-Attribut 
bei diesem Track. Beim nächsten Skript-Lauf erkennt das Tool, dass der Track 
"freigegeben" wurde und ruft ihn komplett neu ab!


================================================================================
--- ENGLISH --------------------------------------------------------------------
================================================================================

Anyone who maintains a music database knows the problem: missing release years, 
empty genre fields, incomplete label codes, or missing album titles. The mAirList 
DB Restorer automates this tedious manual work for you.

The tool analyzes your local mAirList SQLite database (.mldb), searches for the 
missing metadata via the MusicBrainz and Discogs APIs, and safely writes the 
corrected values back into the database.

--------------------------------------------------------------------------------
 1. THE FEATURES: WHAT HAPPENS UNDER THE HOOD?
--------------------------------------------------------------------------------
The script doesn't just search blindly; it uses several safety nets to avoid 
incorrect tags:

* Smart Cleaning: Artist and title are cleaned before searching. Different 
  spellings of features (ft., featuring) are standardized.
* Intelligent Matching (Levenshtein): The tool checks the percentage 
  similarity of the search results. This prevents the API from accidentally 
  assigning the breakcore artist "Duran Duran Duran" to "Duran Duran".
* Outlier Filter (Median & Gap Logic): APIs often contain incorrect user entries. 
  The script calculates the average of all found release years and 
  ignores absurd outliers (e.g., a release year of 1945 for a 2004 track).
* OAD Protection: Virtual and physical folders named "OAD" (On Air Design) 
  are strictly ignored. Jingle packages thus remain untouched.
* Masked Configuration: Your API keys are stored locally masked with Base64 
  so they are not directly readable in plain text in the config.json.
  Note: Base64 is NOT encryption, just encoding – it can be decoded in 
  seconds with any online tool. The protection only applies to accidental 
  glances, not intentional reading. Therefore, do not share your config.json 
  (e.g., do not upload it when asking for support or sharing the tool).

--------------------------------------------------------------------------------
 2. REQUIREMENTS & INSTALLATION
--------------------------------------------------------------------------------
Since this is a Python script, you need to install Python and three 
additional packages once:

1. Download and install Python (https://www.python.org/downloads/) (IMPORTANT: Make sure to 
   check the box "Add Python to PATH" during installation!).
2. Open the Windows Command Prompt. 
   (Tip: Press Windows Key + R, type "cmd", and press Enter).
   Then install the required libraries with the following command:
   
   pip install pandas requests rich

Additionally, you need (free) API credentials for Discogs:
1. Create an account on discogs.com
2. Go to the developer settings (Settings -> Developers)
3. Create a new App/Token and copy your "Consumer Key" 
   and "Consumer Secret".

--------------------------------------------------------------------------------
 3. THE WORKFLOW (USAGE)
--------------------------------------------------------------------------------
IMPORTANT BEFORE YOU START: 
NEVER work with the database file (.mldb) that is currently open in mAirList! 
mAirList locks the file while running. If the script tries to write at the same 
time, the database can be corrupted. 
-> Always create a COPY of your .mldb file on your desktop!

PREPARATION: SELECT DATABASE
Start the tool using the "Restore.bat" file. Select your language.
Select [0] in the menu. The script will now ask for the path to your database. 
PRO TIP: You don't have to type the path manually. You can simply drag and drop 
the .mldb file from the Windows Explorer directly into the console window and 
press Enter! The menu will now remember this file for all subsequent steps.

On the very first start, the script will ask you for your Discogs keys and a 
contact email for MusicBrainz (API requirement). After that, the process begins:

STEP 1: FETCH METADATA (Smart Fetch)
Select [1]. The script reads your database copy and searches for metadata for 
each track that has not yet been processed. The original values remain 
completely untouched. The progress is continuously saved. 
You can abort the process at any time with Ctrl+C and resume it later.

STEP 2: REVIEW DATA (Review)
Select [3] or [4]. Here you are presented with the script's suggestions. 
You can reject any suggestion (year, genre, album, label) with "Enter", accept 
it with "y", or type your own text.
- Live Re-Fetch: If you type your own correction for Artist or Title 
  (e.g., correcting a typo), the script immediately fetches the new, 
  matching data for your correction in the background!

STEP 3: SAVE TO MAIRLIST (Apply)
Select [5]. The script writes all the metadata you approved back into your 
database COPY. 
When the process is complete, you can move the copy back to its original 
location (while mAirList is closed) or reconnect the database in the 
mAirList configuration.

--------------------------------------------------------------------------------
 4. THE "RESTAURIERT" FLAG (Update Logic)
--------------------------------------------------------------------------------
When saving to mAirList, the script sets the attribute "RESTAURIERT" = "JA" 
for each processed track. 
Tracks with this flag are automatically skipped during future runs. 
If you notice later during live radio operation that a track still has wrong 
tags? No problem: Simply delete the "RESTAURIERT" attribute for this track in 
mAirList. On the next script run, the tool will recognize that the track has 
been "released" and will re-fetch it completely!
