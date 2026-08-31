# mAirList DB Restorer v0.50.27 Beta
**Das intelligente Metadaten-Reparatur-Tool für lokale mAirList Datenbanken**

*(Note: English and Dutch documentation / manuals are available in the repository!)*

Jeder, der eine Musikdatenbank pflegt, kennt das Problem: Fehlende Jahreszahlen, leere Genre-Felder, unvollständige Labelcodes oder fehlende Alben. Der *mAirList DB Restorer* nimmt dir diese mühsame Handarbeit ab und bringt deine Datenbank-Attribute vollautomatisch auf Vordermann.

Das Tool analysiert deine lokale mAirList SQLite-Datenbank (`.mldb`), sucht über die APIs von **MusicBrainz** und **Discogs** nach den fehlenden Metadaten und schreibt die von dir freigegebenen Werte sicher in die Datenbank zurück.

---

## 🛠️ Kern-Funktionen (Features)

Dieses Skript sucht nicht einfach blind drauflos, sondern arbeitet mit mehreren Sicherheitsnetzen und Logiken, um falsche Tags zu vermeiden und dir den perfekten Workflow zu bieten:

*   **Smart Cleaning & VIP-Listen:** Vor der API-Suche werden Artist und Titel bereinigt (z. B. "feat.", "ft."). Notorische Schreibweisen (wie "AC/DC") werden über ein hartcodiertes VIP-Dictionary priorisiert.
*   **Laufzeit-Matching (Maxi-Erkennung):** Das Skript gleicht die gesuchten API-Treffer mit der *echten lokalen Track-Laufzeit* (+/- Toleranz für Cue-Punkte) ab. So erkennt es zielsicher Extended-Versions oder seltene Radio-Edits.
*   **Ausreißer-Filter (Median & Lücken-Logik):** Da APIs oft fehlerhafte User-Einträge enthalten, berechnet das Skript den Mittelwert aller gefundenen Release-Jahre und ignoriert absurde Ausreißer (z. B. ein Release-Jahr 1945 für einen 2004er Track).
*   **OAD-Schutz (Ignore-Lists):** Virtuelle und physische Ordner, die z. B. "OAD" (On Air Design) oder "Jingles" heißen, können konsequent von der Suche ausgeschlossen werden.
*   **Ergonomischer Review-Prozess:** Alle API-Vorschläge können vor dem Speichern in die Datenbank in einem schnellen Terminal-Workflow geprüft, angepasst oder mit einem Tastendruck (Rückgriff auf den Original-Wert) abgelehnt werden.
*   **Massenbearbeitung (Wartungs-Modus):** Ein separates Menü erlaubt tiefe Datenbank-Eingriffe wie die nachträgliche Standardisierung von hunderten Genres, das Korrigieren von Groß-/Kleinschreibung (Title Case) oder das Löschen von Alt-Attributen ("Platinum Notes", "Lyrics").

---

## ⚠️ Wichtige Hinweise & Disclaimer (Bitte lesen!)

*   **LOKALE DATENBANKEN:** Dieses Tool funktioniert aktuell **ausschließlich mit lokalen SQLite-Datenbanken (`.mldb`)** von mAirList. (Eine Unterstützung für Netzwerkdatenbanken ist für spätere Updates geplant).
*   **SPRACH-KOMPATIBILITÄT:** Die Feld-Zuordnung beim Schreiben in die Datenbank ist derzeit auf **deutsche, englische und niederländische** mAirList-Installationen optimiert. (Weitere Sprachen folgen auf Wunsch).
*   **KEINE GARANTIE:** Weder die APIs von MusicBrainz oder Discogs noch die Algorithmen dieses Tools sind unfehlbar. Aufgrund der gigantischen Menge an unterschiedlichen Schreibweisen, Remixes und Namensgleichheiten können falsche Metadaten geliefert werden. **Die Nutzung erfolgt auf eigene Gefahr!**
*   **IMMER MIT EINER KOPIE ARBEITEN:** Da das Tool direkt und ohne "Undo"-Funktion in die Datenbank schreibt, darf **NIEMALS** auf der aktiven, von mAirList im Hintergrund geöffneten Datei gearbeitet werden. Nutze für das Tool *immer* eine Kopie deiner `.mldb`-Datei!

---

## 📖 Bedienungsanleitung (How-To)

Die detaillierte Anleitung zur Installation (Python, benötigte Module) und die Erklärung des genauen Workflows (Schritt-für-Schritt) findest du in den beiliegenden Handbüchern:

*   👉 **[Manual_DE.pdf / Manual_DE.txt]** (Hier Dateipfad/Link einfügen)
*   👉 **[Manual_EN.pdf / Manual_EN.txt]** (Hier Dateipfad/Link einfügen)
*   👉 **[Manual_NL.pdf / Manual_NL.txt]** (Hier Dateipfad/Link einfügen)

---

## 🤖 Transparenz zur Entstehung

Ein offenes Wort zum Code: Das funktionale Konzept, der Workflow und die Architektur dieses Tools stammen aus menschlicher Hand (Myka Vormeng). Die reine Programmierung und das Verfassen des Python-Codes erfolgten maßgeblich durch die Künstliche Intelligenz *Google Gemini*. 

Der Fokus dieses Projektes liegt darauf, was das Tool für die mAirList-Community leistet und wie viele Stunden mühsamer Handarbeit (Klicken im Cue-Editor) es euch ersparen kann.

---

## 🆘 Support & Feature-Wünsche

Technischen Support, Bug-Reports oder Wünsche für neue Features bearbeiten wir **ausschließlich** über die folgenden beiden offiziellen Kanäle:

1.  Die **Issue-Funktion** hier auf GitHub.
2.  Den offiziellen Release-Thread im **mAirList-Forum**.

*(Bitte sehe von privaten Nachrichten oder E-Mails bezüglich Supportanfragen ab).*