# mAirList DB Restorer v0.62.03 BETA
**De intelligente metadata-reparatietool voor lokale mAirList databases**

*(Note: German and English documentation / manuals are available in the repository!)*

### 🚀 Quick Download
Voor iedereen die direct aan de slag wil zonder Python te installeren: Download gewoon de kant-en-klare, gecompileerde `.exe`-versie inclusief handleidingen!
👉 **[Download mAirList-DB-Restorer (ZIP) via Google Drive](https://drive.google.com/file/d/1lV2qG7nSj28BKC2W5FoPn4bgfqqsDjdM/view?usp=sharing)**

*(De rest van de broncode in deze repository is bedoeld voor ontwikkelaars en geïnteresseerden die het script zelf willen compileren of de code transparant willen inzien).*

---

Iedereen die een muziekdatabase beheert, kent het probleem: Ontbrekende jaartallen, lege genre-velden, onvolledige labelcodes of ontbrekende albums. De *mAirList DB Restorer* neemt dit vervelende handmatige werk uit handen en brengt je database-attributen volautomatisch op orde.

De tool analyseert je lokale mAirList SQLite-database (`.mldb`), zoekt via de **MusicBrainz** en **Discogs** API's naar de ontbrekende metadata en schrijft de door jou goedgekeurde waarden veilig terug in de database.

---

## 🛠️ Kernfuncties (Features)

Dit script zoekt niet zomaar blindelings, maar werkt met meerdere veiligheidsnetten en logica's om verkeerde tags te voorkomen en je de perfecte workflow te bieden:

*   **Smart Cleaning & VIP-lijsten:** Artiest en titel worden voor de API-zoekopdracht opgeschoond (bijv. "feat.", "ft."). Beruchte spellingen (zoals "AC/DC") krijgen voorrang via een hardcoded VIP-woordenboek.
*   **Looptijd-Matching (Maxi-herkenning):** Het script vergelijkt de gevonden API-resultaten met de *echte lokale tracklengte* (+/- tolerantie voor cue-punten). Zo herkent het feilloos extended versions of zeldzame radio-edits.
*   **Uitschieter-filter (Mediaan & Gaten-logica):** Omdat API's vaak foutieve gebruikersinvoer bevatten, berekent het script het gemiddelde van alle gevonden releasejaren en negeert het absurde uitschieters (bijv. een releasejaar van 1945 voor een track uit 2004).
*   **OAD-bescherming (Ignore-Lists):** Virtuele en fysieke mappen met namen als "OAD" (On Air Design) of "Jingles" kunnen consequent worden uitgesloten van de zoekopdracht.
*   **Ergonomisch Review-proces:** Alle API-suggesties kunnen voor het opslaan in de database in een snelle terminal-workflow worden gecontroleerd, aangepast of met één druk op de knop (terugvallen op de originele waarde) worden afgewezen.
*   **Massabewerking (Onderhoudsmodus):** Een apart menu maakt diepe database-ingrepen mogelijk, zoals het achteraf standaardiseren van honderden genres, het corrigeren van hoofdletters/kleine letters (Title Case) of het verwijderen van oude attributen ("Platinum Notes", "Lyrics").

---

## ⚠️ Belangrijke opmerkingen & Disclaimer (Lees dit a.u.b.!)

*   **LOKALE DATABASES:** Deze tool werkt momenteel **uitsluitend met lokale SQLite-databases (`.mldb`)** van mAirList. (Ondersteuning voor netwerkdatabases staat gepland voor toekomstige updates).
*   **TAALCOMPATIBILITEIT:** De veldtoewijzing bij het schrijven naar de database is momenteel geoptimaliseerd voor **Duitse, Engelse en Nederlandse** mAirList-installaties. (Meer talen volgen op verzoek).
*   **GEEN GARANTIE:** Noch de API's van MusicBrainz of Discogs, noch de algoritmes van deze tool zijn onfeilbaar. Vanwege de gigantische hoeveelheid verschillende spellingen, remixen en naamovereenkomsten kunnen er verkeerde metadata worden geleverd. **Gebruik is op eigen risico!**
*   **WERK ALTIJD MET EEN KOPIE:** Omdat de tool direct en zonder "Undo"-functie in de database schrijft, mag je **NOOIT** werken op het actieve bestand dat momenteel op de achtergrond door mAirList is geopend. Gebruik voor de tool *altijd* een kopie van je `.mldb`-bestand!

---

## 📖 Handleiding

De gedetailleerde stapsgewijze handleiding voor installatie en gebruik vind je apart in de repository (`Manual_NL.md` of in het gedownloade ZIP-archief).

---

## 🤖 Transparantie over het ontstaan

Een open woord over de code: Het functionele concept, de workflow en de architectuur van deze tool zijn bedacht door mensenhanden (Myka Vormeng). Het pure programmeren en het schrijven van de Python-code is grotendeels gedaan door de Kunstmatige Intelligentie *Google Gemini*. 

De focus van dit project ligt op wat de tool voor de mAirList-community doet en hoeveel uur vervelend handmatig werk (klikken in de cue-editor) het jullie kan besparen.

---

## 🆘 Support & Feature Requests

Technische ondersteuning, bug-reports of verzoeken voor nieuwe functies behandelen we **uitsluitend** via de volgende twee officiële kanalen:

1.  De **Issue-functie** hier op GitHub.
2.  De officiële release thread in het **mAirList-forum**.

*(Zie a.u.b. af van privéberichten of e-mails met betrekking tot supportverzoeken).*