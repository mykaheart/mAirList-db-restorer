# mAirList DB Restorer v0.64.00 BETA
**Das intelligente Metadaten-Reparatur-Tool für lokale mAirList Datenbanken**

*(Note: English and Dutch documentation / manuals are available in the repository!)*

### 🚀 Quick Download
Für alle, die direkt loslegen wollen, ohne Python zu installieren: Lade dir einfach die fertige, vorkompilierte `.exe`-Version inklusive Handbüchern herunter!
👉 **[Download mAirList-DB-Restorer (ZIP) via Google Drive](https://drive.google.com/drive/folders/18SmIOBFbSM5apwS6FA3F72-syLvBAftj?usp=drive_link)**

*(Der restliche Quellcode in diesem Repository richtet sich an Entwickler und Interessierte, die das Skript selbst kompilieren oder den Code transparent einsehen möchten).*

---

Jeder, der eine Musikdatenbank pflegt, kennt das Problem: Fehlende Jahreszahlen, leere Genre-Felder, unvollständige Labelcodes oder fehlende Alben. Der *mAirList DB Restorer* nimmt dir diese mühsame Handarbeit ab und bringt deine Datenbank-Attribute vollautomatisch auf Vordermann.

Das Tool analysiert deine lokale mAirList SQLite-Datenbank (`.mldb`), sucht über die APIs von **MusicBrainz** und **Discogs** nach den fehlenden Metadaten und schreibt die von dir freigegebenen Werte sicher in die Datenbank zurück.

---

## 🛠️ Kern-Funktionen (Features)

Dieses Skript sucht nicht einfach blind drauflos, sondern arbeitet mit mehreren Sicherheitsnetzen und Logiken, um falsche Tags zu vermeiden und dir den perfekten Workflow zu bieten:

*   **Smart Cleaning & VIP-Listen:** Vor der API-Suche werden Artist und Titel bereinigt (z. B. "feat.", "ft."). Notorische Schreibweisen (wie "AC/DC") werden über ein hartcodiertes VIP-Dictionary priorisiert.
*   **Laufzeit-Matching (Maxi-Erkennung):** Das Skript gleicht die gesuchten API-Treffer mit der *echten lokalen Track-Laufzeit* (+/- Toleranz für Cue-Punkte) ab. So erkennt es zielsicher Extended-Versions oder seltene Radio-Edits.
*   **Ausreißer-Filter (Lücken-Logik):** Gefundene Release-Jahre werden sortiert und auf unplausible Einzel-Ausreißer geprüft. Liegt das älteste Jahr mehr als acht Jahre vor dem nächsten Treffer und kommt nur einmal vor, wird es verworfen. So werden typische Fehleinträge aus Community-Datenbanken abgefangen.
*   **OAD-Schutz (Ignore-Lists):** Virtuelle und physische Ordner, die z. B. "OAD" (On Air Design) oder "Jingles" heißen, können konsequent von der Suche ausgeschlossen werden.
*   **Ergonomischer Review-Prozess:** Alle API-Vorschläge können vor dem Speichern in die Datenbank in einem schnellen Terminal-Workflow geprüft, angepasst oder mit einem Tastendruck (Rückgriff auf den Original-Wert) abgelehnt werden.
*   **Massenbearbeitung (Wartungs-Modus):** Ein separates Menü erlaubt die nachträgliche Standardisierung von Genres, das Korrigieren von Groß-/Kleinschreibung und Apostrophen sowie das Schreiben geprüfter Metadaten in lokale FLAC-, MP3- und AIFF-Dateien.
*   **Hardening & Wiederaufnahme:** Einzelne API-Requests werden automatisch wiederholt; bei transienten Netzwerk-/429-/5xx-Fehlern startet zusätzlich der komplette Track bis zu dreimal mit 2/5/10-s-Backoff neu. Erst danach bleibt er als offen markiert. Sitzungs-CSVs werden atomar gespeichert und pro Datenbankpfad getrennt, damit Arbeitsstände weder beschädigt noch zwischen gleichnamigen Datenbanken vermischt werden.
*   **Sicheres Speichern:** Vor dem finalen Schreiben zeigt der Restorer eine Änderungsübersicht, prüft die SQLite-Integrität, erstellt ein Backup und prüft die Datenbank nach dem Schreiben erneut.
*   **Dopplungsprüfung:** Die Wartung kann aktuelle Dopplungs-Kandidaten anhand identischer Artist/Titel-Kombinationen, Dateipfade oder gültiger ISRCs mit `DOPPELUNG=JA` markieren. Beim nächsten Lauf werden erledigte Markierungen automatisch wieder entfernt; Elemente werden niemals automatisch gelöscht.
*   **BPM-Restauration im normalen Fetch + als Wartung:** Seit 0.64 läuft die BPM-Kette auch im normalen Fetch. Primäre Quelle ist ein optionaler, pro Datenbank gemerkter rekordbox-XML-Export: `AverageBpm` wird ausschließlich über den exakt passenden Dateipfad zugeordnet. Danach folgen Audio-Datei-Tags und als letzter Fallback MusicBrainz + AcousticBrainz. Bestehende gültige BPM werden auch beim Full Fetch niemals überschrieben. Wartungsoption [6] bleibt als schneller BPM-only-Nachpflegeweg mit Review-CSV, Ursachen-Diagnose und Half-/Double-Time-Konfliktanzeige erhalten.

---

## ⚠️ Wichtige Hinweise & Disclaimer (Bitte lesen!)

*   **LOKALE DATENBANKEN:** Dieses Tool funktioniert aktuell **ausschließlich mit lokalen SQLite-Datenbanken (`.mldb`)** von mAirList. (Eine Unterstützung für Netzwerkdatenbanken ist für spätere Updates geplant).
*   **SPRACH-KOMPATIBILITÄT:** Die Feld-Zuordnung beim Schreiben in die Datenbank ist derzeit auf **deutsche, englische und niederländische** mAirList-Installationen optimiert. (Weitere Sprachen folgen auf Wunsch).
*   **KEINE GARANTIE:** Weder die APIs von MusicBrainz oder Discogs noch die Algorithmen dieses Tools sind unfehlbar. Aufgrund der gigantischen Menge an unterschiedlichen Schreibweisen, Remixes und Namensgleichheiten können falsche Metadaten geliefert werden. **Die Nutzung erfolgt auf eigene Gefahr!**
*   **IMMER MIT EINER KOPIE ARBEITEN:** Da das Tool direkt und ohne "Undo"-Funktion in die Datenbank schreibt, darf **NIEMALS** auf der aktiven, von mAirList im Hintergrund geöffneten Datei gearbeitet werden. Nutze für das Tool *immer* eine Kopie deiner `.mldb`-Datei!

---

## 📖 Bedienungsanleitung

Die detaillierte Schritt-für-Schritt-Anleitung zur Installation und Nutzung findest du separat im Repository (`Manual_DE.md` bzw. im heruntergeladenen ZIP-Archiv).

---

## 🧪 Entwicklung & Tests

Für Entwickler liegt eine `requirements.txt` bei. Die sicherheitskritischen Regressionstests benötigen kein zusätzliches Test-Framework und laufen mit:

```bash
python -m unittest discover -s tests -v
```

Bei Pushes und Pull Requests führt GitHub Actions zusätzlich automatisch einen Compile-Check und die Regressionstests unter Windows aus.

---

## 📜 Lizenz

Der mAirList DB Restorer wird als **source-available Freeware** veröffentlicht. Der Quellcode darf eingesehen und für den eigenen privaten bzw. internen Gebrauch angepasst werden. Eine Weiterverteilung, ein Re-Upload, Spiegeln, Verkaufen oder Veröffentlichen veränderter oder unveränderter Fassungen ist ohne vorherige schriftliche Genehmigung nicht gestattet. Offizielle Downloads dürfen über alle vom Rechteinhaber ausdrücklich benannten Vertriebskanäle angeboten werden. Details stehen in `LICENSE`.

## 🤖 Transparenz zur Entstehung

Ein offenes Wort zum Code: Das funktionale Konzept, der Workflow und die Architektur dieses Tools stammen aus menschlicher Hand (Myka Vormeng). Die reine Programmierung und das Verfassen des Python-Codes erfolgten maßgeblich durch die Künstliche Intelligenz *ChatGPT*.

Der Fokus dieses Projektes liegt darauf, was das Tool für die mAirList-Community leistet und wie viele Stunden mühsamer Handarbeit (Klicken im Cue-Editor) es euch ersparen kann.

---

## 🆘 Support & Feature-Wünsche

Technischen Support, Bug-Reports oder Wünsche für neue Features bearbeiten wir **ausschließlich** über die folgenden beiden offiziellen Kanäle:

1.  Die **Issue-Funktion** hier auf GitHub.
2.  Den offiziellen Release-Thread im **mAirList-Forum**.

*(Bitte sehe von privaten Nachrichten oder E-Mails bezüglich Supportanfragen ab).*