# mAirList DB Restorer v0.52.00 Beta[cite: 5]
**Das intelligente Metadaten-Reparatur-Tool für lokale mAirList Datenbanken**[cite: 5]

*(Note: English and Dutch documentation / manuals are available in the repository!)*[cite: 5]

### 🚀 Quick Download
Für alle, die direkt loslegen wollen, ohne Python zu installieren: Lade dir einfach die fertige, vorkompilierte `.exe`-Version inklusive Handbüchern herunter!
👉 **[Download mAirList-DB-Restorer (ZIP) via Google Drive](https://drive.google.com/file/d/1lV2qG7nSj28BKC2W5FoPn4bgfqqsDjdM/view?usp=sharing)**

*(Der restliche Quellcode in diesem Repository richtet sich an Entwickler und Interessierte, die das Skript selbst kompilieren oder den Code transparent einsehen möchten).*

---

Jeder, der eine Musikdatenbank pflegt, kennt das Problem: Fehlende Jahreszahlen, leere Genre-Felder, unvollständige Labelcodes oder fehlende Alben.[cite: 5] Der *mAirList DB Restorer* nimmt dir diese mühsame Handarbeit ab und bringt deine Datenbank-Attribute vollautomatisch auf Vordermann.[cite: 5]

Das Tool analysiert deine lokale mAirList SQLite-Datenbank (`.mldb`), sucht über die APIs von **MusicBrainz** und **Discogs** nach den fehlenden Metadaten und schreibt die von dir freigegebenen Werte sicher in die Datenbank zurück.[cite: 5]

---

## 🛠️ Kern-Funktionen (Features)[cite: 5]

Dieses Skript sucht nicht einfach blind drauflos, sondern arbeitet mit mehreren Sicherheitsnetzen und Logiken, um falsche Tags zu vermeiden und dir den perfekten Workflow zu bieten:[cite: 5]

*   **Smart Cleaning & VIP-Listen:** Vor der API-Suche werden Artist und Titel bereinigt (z. B. "feat.", "ft.").[cite: 5] Notorische Schreibweisen (wie "AC/DC") werden über ein hartcodiertes VIP-Dictionary priorisiert.[cite: 5]
*   **Laufzeit-Matching (Maxi-Erkennung):** Das Skript gleicht die gesuchten API-Treffer mit der *echten lokalen Track-Laufzeit* (+/- Toleranz für Cue-Punkte) ab.[cite: 5] So erkennt es zielsicher Extended-Versions oder seltene Radio-Edits.[cite: 5]
*   **Ausreißer-Filter (Median & Lücken-Logik):** Da APIs oft fehlerhafte User-Einträge enthalten, berechnet das Skript den Mittelwert aller gefundenen Release-Jahre und ignoriert absurde Ausreißer (z. B. ein Release-Jahr 1945 für einen 2004er Track).[cite: 5]
*   **OAD-Schutz (Ignore-Lists):** Virtuelle und physische Ordner, die z. B. "OAD" (On Air Design) oder "Jingles" heißen, können konsequent von der Suche ausgeschlossen werden.[cite: 5]
*   **Ergonomischer Review-Prozess:** Alle API-Vorschläge können vor dem Speichern in die Datenbank in einem schnellen Terminal-Workflow geprüft, angepasst oder mit einem Tastendruck (Rückgriff auf den Original-Wert) abgelehnt werden.[cite: 5]
*   **Massenbearbeitung (Wartungs-Modus):** Ein separates Menü erlaubt tiefe Datenbank-Eingriffe wie die nachträgliche Standardisierung von hunderten Genres, das Korrigieren von Groß-/Kleinschreibung (Title Case) oder das Löschen von Alt-Attributen ("Platinum Notes", "Lyrics").[cite: 5]

---

## ⚠️ Wichtige Hinweise & Disclaimer (Bitte lesen!)[cite: 5]

*   **LOKALE DATENBANKEN:** Dieses Tool funktioniert aktuell **ausschließlich mit lokalen SQLite-Datenbanken (`.mldb`)** von mAirList.[cite: 5] (Eine Unterstützung für Netzwerkdatenbanken ist für spätere Updates geplant).[cite: 5]
*   **SPRACH-KOMPATIBILITÄT:** Die Feld-Zuordnung beim Schreiben in die Datenbank ist derzeit auf **deutsche, englische und niederländische** mAirList-Installationen optimiert.[cite: 5] (Weitere Sprachen folgen auf Wunsch).[cite: 5]
*   **KEINE GARANTIE:** Weder die APIs von MusicBrainz oder Discogs noch die Algorithmen dieses Tools sind unfehlbar.[cite: 5] Aufgrund der gigantischen Menge an unterschiedlichen Schreibweisen, Remixes und Namensgleichheiten können falsche Metadaten geliefert werden.[cite: 5] **Die Nutzung erfolgt auf eigene Gefahr!**[cite: 5]
*   **IMMER MIT EINER KOPIE ARBEITEN:** Da das Tool direkt und ohne "Undo"-Funktion in die Datenbank schreibt, darf **NIEMALS** auf der aktiven, von mAirList im Hintergrund geöffneten Datei gearbeitet werden.[cite: 5] Nutze für das Tool *immer* eine Kopie deiner `.mldb`-Datei![cite: 5]

---

## 📖 Bedienungsanleitung[cite: 5]

Die detaillierte Schritt-für-Schritt-Anleitung zur Installation und Nutzung findest du separat im Repository (`Manual_DE.md` bzw. im heruntergeladenen ZIP-Archiv).[cite: 5]

---

## 🤖 Transparenz zur Entstehung[cite: 5]

Ein offenes Wort zum Code: Das funktionale Konzept, der Workflow und die Architektur dieses Tools stammen aus menschlicher Hand (Myka Vormeng).[cite: 5] Die reine Programmierung und das Verfassen des Python-Codes erfolgten maßgeblich durch die Künstliche Intelligenz *Google Gemini*.[cite: 5]

Der Fokus dieses Projektes liegt darauf, was das Tool für die mAirList-Community leistet und wie viele Stunden mühsamer Handarbeit (Klicken im Cue-Editor) es euch ersparen kann.[cite: 5]

---

## 🆘 Support & Feature-Wünsche[cite: 5]

Technischen Support, Bug-Reports oder Wünsche für neue Features bearbeiten wir **ausschließlich** über die folgenden beiden offiziellen Kanäle:[cite: 5]

1.  Die **Issue-Funktion** hier auf GitHub.[cite: 5]
2.  Den offiziellen Release-Thread im **mAirList-Forum**.[cite: 5]

*(Bitte sehe von privaten Nachrichten oder E-Mails bezüglich Supportanfragen ab).*[cite: 5]
