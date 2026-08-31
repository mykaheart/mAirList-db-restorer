# mAirList DB Restorer v0.50.27 Beta
**De intelligente metadata-reparatietool voor lokale mAirList-databases**

Iedereen die een muziekdatabase beheert, kent het probleem: ontbrekende jaartallen, lege genre-velden, onvolledige labelcodes of ontbrekende albums. De *mAirList DB Restorer* neemt dit tijdrovende handwerk van je over en brengt je database-attributen volautomatisch op orde.

De tool analyseert je lokale mAirList SQLite-database (`.mldb`), zoekt via de API's van **MusicBrainz** en **Discogs** naar de ontbrekende metadata en schrijft de door jou goedgekeurde waarden veilig terug in de database.

---

## 🛠️ Kernfuncties (Features)

Dit script zoekt niet zomaar blindelings, maar werkt met meerdere vangnetten en logica's om foute tags te voorkomen en je de perfecte workflow te bieden:

*   **Smart Cleaning & VIP-lijsten:** Voor het zoeken worden artiest en titel opgeschoond (bijv. "feat.", "ft."). Notorische schrijfwijzen (zoals "AC/DC") krijgen prioriteit via een hardcoded VIP-woordenboek.
*   **Speelduur-Matching (Maxi-herkenning):** Het script vergelijkt de API-zoekresultaten met de *echte lokale track-speelduur* (+/- tolerantie voor cue-punten). Zo herkent het feilloos Extended Versions of zeldzame Radio Edits.
*   **Outlier-Filter (Mediaan & Hiaat-logica):** Omdat API's vaak foutieve gebruikersinvoer bevatten, berekent het script het gemiddelde van alle gevonden releasejaren en negeert absurde uitschieters (bijv. releasejaar 1945 voor een track uit 2004).
*   **OAD-Bescherming (Ignore-lijsten):** Virtuele en fysieke mappen met de naam, bijvoorbeeld, "OAD" (On Air Design) of "Jingles" kunnen consequent van de zoekopdracht worden uitgesloten.
*   **Ergonomisch Review-proces:** Alle API-suggesties kunnen voor het opslaan in een snelle terminal-workflow worden gecontroleerd, aangepast of met één druk op de knop (terugval op de originele waarde) worden afgewezen.
*   **Massabewerking (Onderhoudsmodus):** Een apart menu maakt diepe database-ingrepen mogelijk, zoals het achteraf standaardiseren van honderden genres, het corrigeren van hoofdletters/kleine letters (Title Case), of het verwijderen van oude attributen ("Platinum Notes", "Lyrics").

---

## ⚠️ Belangrijke opmerkingen & Disclaimer (Lezen a.u.b.!)

*   **LOKALE DATABASES:** Deze tool werkt momenteel **uitsluitend met lokale SQLite-databases (`.mldb`)** van mAirList. (Ondersteuning voor netwerkdatabases is gepland voor toekomstige updates).
*   **TAALCOMPATIBILITEIT:** De veldtoewijzing bij het schrijven naar de database is momenteel geoptimaliseerd voor **Duitse, Engelse en Nederlandse** mAirList-installaties. (Meer talen volgen op verzoek).
*   **GEEN GARANTIE:** Noch de API's van MusicBrainz of Discogs, noch de algoritmen van deze tool zijn onfeilbaar. Vanwege de gigantische hoeveelheid verschillende schrijfwijzen, remixen en gelijknamigheden kan verkeerde metadata worden geleverd. **Gebruik is op eigen risico!**
*   **WERK ALTIJD OP EEN KOPIE:** Omdat de tool direct en zonder "Undo"-functie in de database schrijft, mag je **NOOIT** werken op het actieve bestand dat momenteel in mAirList is geopend. Gebruik voor deze tool *altijd* een kopie van je `.mldb`-bestand!

---

## 📖 Gebruikershandleiding (How-To)

De gedetailleerde instructies voor installatie (Python, benodigde modules) en de uitleg van de exacte workflow (stap-voor-stap) vind je in de bijgevoegde handleidingen:

*   👉 **[Manual_DE.pdf / Manual_DE.txt]** (Voeg hier bestandspad/link in)
*   👉 **[Manual_EN.pdf / Manual_EN.txt]** (Voeg hier bestandspad/link in)
*   👉 **[Manual_NL.pdf / Manual_NL.txt]** (Voeg hier bestandspad/link in)

---

## 🤖 Transparantie over de ontwikkeling

Een open woord over de code: Het functionele concept, de workflow en de architectuur van deze tool zijn afkomstig van een mens (Myka Vormeng). De daadwerkelijke programmering en het schrijven van de Python-code zijn grotendeels uitgevoerd door de Kunstmatige Intelligentie *Google Gemini*.

De focus van dit project ligt op wat de tool voor de mAirList-community doet en hoeveel uren vervelend handwerk (klikken in de Cue Editor) het jullie kan besparen.

---

## 🆘 Support & Feature Requests

Technische ondersteuning, bugrapporten of verzoeken voor nieuwe functies behandelen we **uitsluitend** via de volgende twee officiële kanalen:

1.  De **Issues-functie** hier op GitHub.
2.  De officiële release-thread in het **mAirList-forum**.

*(Stuur a.u.b. geen privéberichten of e-mails met betrekking tot supportvragen).*