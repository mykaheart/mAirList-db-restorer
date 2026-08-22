================================================================================
 mAirList DB Restorer v0.4
 Ein Metadaten-Reparatur-Tool für die mAirList-Community
================================================================================

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
* Ausreißer-Filter (Median): APIs enthalten oft fehlerhafte User-Einträge. 
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
Wähle [0] im Menü. Das Skript fragt dich nun nach dem Pfad zu deiner Datenbank. 
PRO-TIPP: Du musst den Pfad nicht mühsam eintippen. Du kannst die .mldb-Datei 
einfach aus dem Windows-Explorer mit der Maus direkt in das Konsolenfenster 
ziehen (Drag & Drop) und Enter drücken! Das Menü merkt sich diese Datei nun für 
alle folgenden Schritte.

Starte das Tool über die Datei "Restore.bat". 
Beim allerersten Start fragt dich das Skript nach deinen Discogs-Keys und einer 
Kontakt-E-Mail für MusicBrainz (Vorgabe der API). Danach erscheint das Hauptmenü.

SCHRITT 1: METADATEN LADEN (Datenabruf)
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
