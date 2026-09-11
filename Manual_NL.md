# 📖 Handleiding: mAirList DB Restorer

Welkom bij de officiële handleiding voor de **mAirList DB Restorer**! Deze tool is ontwikkeld om je honderden uren vervelend handmatig werk in de Cue-Editor te besparen door ontbrekende metadata (jaren, genres, albums, labels) volautomatisch via de API's van MusicBrainz en Discogs te zoeken en aan te vullen.

Dankzij de "All-in-One"-architectuur is het programma direct klaar voor gebruik – zonder ingewikkelde installatie! Om ervoor te zorgen dat alles soepel verloopt, verzoeken wij je om eenmalig de volgende korte instellingsprocedure te doorlopen.

---

## 1. Voorbereiding & Installatie

De tool is een volledig op zichzelf staande applicatie (`.exe`). Je hoeft geen Python of andere codebibliotheken te installeren. Download gewoon het huidige ZIP-bestand, pak het uit op een locatie naar keuze en start het bestand **`Restorer.exe`**.

### Stap 1.1: Discogs API-Keys genereren
Om toegang te krijgen tot de enorme database van Discogs, heeft het script een gratis API-sleutel nodig.
1. Maak een gratis account aan op [discogs.com](https://www.discogs.com) (als je er nog geen hebt) en log in.
2. Klik rechtsboven op je profielfoto en selecteer **Instellingen** (Settings).
3. Ga in het linkermenu helemaal naar beneden naar **Ontwikkelaars** (Developers).
4. Klik op de knop **"Create an App"** (of Generate Token).
5. Voer een willekeurige naam in voor de app (bijv. "mAirList Restorer").
6. Je ontvangt nu twee belangrijke cryptische tekenreeksen: De **Consumer Key** en het **Consumer Secret**.
7. Kopieer deze twee waarden. Bij de allereerste start van de `.exe` zal het programma ernaar vragen en de waarden lokaal in de map `Data` opslaan. Ze zijn daar alleen met Base64 verhuld en niet cryptografisch versleuteld.

---

## 2. De gouden regel: Back-ups! 🛡️

Het belangrijkste bij het werken met databases is gegevensbeveiliging. De mAirList DB Restorer grijpt diep in de structuur in en herschrijft metadata volautomatisch.

⚠️ **Werk NOOIT met het actieve databasebestand (`.mldb`) dat mAirList op dit moment geopend heeft!**
Wanneer mAirList draait, vergrendelt (lockt) het het databasebestand. Als de tool nu probeert tegelijkertijd nieuwe genres of jaartallen in dit bestand te schrijven, kan de database in het ergste geval onherstelbaar beschadigd raken. Het script heeft weliswaar een ingebouwde beveiliging die vergrendelde bestanden detecteert, maar voorkomen is beter dan genezen.

### De Veilige Workflow:
1. Sluit mAirList of open de Windows Verkenner en navigeer naar de map waar je `.mldb`-bestand staat.
2. Kopieer het bestand (bijv. `Archief.mldb`) en plak het op een veilige plek, zoals je **Bureaublad**.
3. Start de `Restorer.exe`.
4. Wanneer het script in het menu naar het pad naar de database vraagt, **typ het dan niet moeizaam in**!
5. 💡 **Pro-Tip:** Klik gewoon op het gekopieerde `.mldb`-bestand op je bureaublad, houd de muisknop ingedrukt en **sleep het bestand direct in het venster**. Druk op `Enter`. Het pad is nu perfect ingevuld!
6. Als je klaar bent met de tool en alle nieuwe metadata in de kopie hebt opgeslagen, sluit je mAirList, vervang je het oude bestand door je nieuwe, bewerkte kopie en start je mAirList opnieuw.

---

## 3. De Workflow: Metadata herstellen

Bij de eerste start vraagt de tool je naar je voorkeurstaal (Duits, Engels, Nederlands). Het script onthoudt deze instelling voor de toekomst. Via Optie **[8]** in het hoofdmenu kun je dit op elk moment wijzigen; Optie **[9]** sluit het programma af.
Zodra je je databasekopie hebt geladen, leidt het interactieve menu je door het proces en toont het de aanbevolen volgorde **1 → 4/5 → 7**. *Let op: Het script maakt automatisch een map `Data` aan. Werkbestanden worden atomair opgeslagen en per volledig databasepad gescheiden, zodat twee gelijknamige `.mldb`-bestanden nooit dezelfde cache gebruiken.*

### Stap 3.1: Map-uitzonderingen definiëren (Ignore-List)
Voordat het script tijdens de eerste fetch met zoeken begint, vraagt het je naar mappen die **consequent genegeerd** moeten worden (bijv. mappen voor Jingles, News, Drops of Reclame).
*   **Eenvoudige invoer:** Je kunt hier de fysieke map vanuit de Windows Verkenner gewoon in slepen via Drag & Drop of de exacte naam van een virtuele mAirList-map typen. Druk bij een lege invoer op `Enter` als je klaar bent met de lijst.
*   **Individueel per database:** Het script is slim en onthoudt deze uitzonderingslijst individueel voor precies dit geladen `.mldb`-bestand!
*   **Altijd aanpasbaar:** Als je de tool later opnieuw start met dezelfde database, toont het je de huidige ignore-list en vraagt het of je deze wilt behouden of een nieuwe wilt maken.

### Stap 3.2: Metadata ophalen (Fetch)
In deze fase zoekt het script via de API's van MusicBrainz en Discogs naar de passende metadata voor je tracks. Je originele waarden blijven daarbij volledig onaangetast!

*   **[1] Nieuwe/onbewerkte tracks zoeken:** Controleert alleen tracks die nog niet hersteld zijn en pauzeert na elke 50 tracks. De werkstand kan altijd worden hervat.
*   **[2] Alle openstaande tracks zonder pauze zoeken:** Doet hetzelfde als optie 1, maar loopt zonder 50-trackpauzes tot het einde door – handig voor grote databases of 's nachts.
*   **[3] Alle tracks volledig opnieuw controleren:** Negeert de `RESTAURIERT`-vlag en haalt voor **ALLE** tracks nieuwe suggesties op. Na controle mogen deze bewust vernieuwde waarden ook reeds herstelde database-items overschrijven; de normale overschrijfbeveiliging blijft actief voor opties 1/2.

Als MusicBrainz of Discogs tijdelijk niet bereikbaar is, probeert de Restorer de aanvraag automatisch meerdere keren. Blijft de fout bestaan, dan wordt de track **niet als klaar gemarkeerd**; hij blijft openstaan en wordt bij een latere fetch opnieuw geprobeerd.

> **Tip:** Je kunt het fetch-proces op elk moment annuleren met de toetsencombinatie `Ctrl + C`. Het script slaat je voortgang tot dan toe veilig op, en je kunt de volgende keer bij het starten precies op dit punt verdergaan!

### Stap 3.3: Data controleren (Review)
Kies **[4] Alle suggesties zelf controleren** of **[5] Controle met automatische hulp**. Optie 4 is volledig handmatig. Optie 5 accepteert alleen veilige **Jaar/Genre**-matches automatisch; alle andere velden blijven controleerbaar.

*   **Bevestigen:** Als een suggestie je bevalt (bijv. het jaar), druk dan gewoon op `Enter`. De tool neemt de waarde over en springt naar het volgende veld.
*   **Origineel behouden (`O`-toets):** Naast de suggestie zie je altijd in het grijs je oorspronkelijke database-waarde. Is je eigen waarde beter? Typ gewoon een `o` (voor origineel) en druk op `Enter`.
*   **Eigen tekst:** Is de suggestie fout, maar je originele waarde ook? Typ dan gewoon je gewenste tekst in.
*   **Live Re-Fetch:** Als je bij Artiest, Titel, Jaar of Album een eigen tekst typt (bijv. om een typfout in de artiestennaam te corrigeren), vuurt het script op de achtergrond direct een nieuwe API-zoekopdracht af en past het Labels, Genres en ISRC live aan je correctie aan!
*   **Oeps, typfout?** Typ een `<` of `b` (voor Back) en druk op `Enter` om één track terug te springen.

### Stap 3.4: Onderhoud (Maintenance)
Onder Optie **[6]** vind je de onderhoudshulpmiddelen. Je kunt genres standaardiseren, hoofdletters/kleine letters en apostrofs in Artiest/Titel corrigeren of met de bestandstagger gecontroleerde metadata uit de database naar lokale FLAC-, MP3- en AIFF-bestanden schrijven. Combinatieoptie **[4]** voert de genre- en tekstcorrectie achter elkaar uit.

Onderhoudsoptie **[5] Dubbele kandidaten markeren / status bijwerken** zoekt naar actuele controlekandidaten. Muziekitems gelden als kandidaat wanneer ze dezelfde genormaliseerde Artiest/Titel-combinatie, hetzelfde opgeslagen bestandspad of dezelfde geldige ISRC hebben. Verschillende looptijden verhinderen bewust geen markering, omdat verschillende edits of versies daarna door de gebruiker in de mAirList DB-app moeten worden beoordeeld.

Gevonden items krijgen alleen het attribuut `DOPPELUNG=JA`; **er wordt nooit automatisch een item verwijderd**. Na je controle in mAirList voer je dezelfde functie opnieuw uit. Heeft een eerder gemarkeerd item dan geen passende partner meer, dan verwijdert de Restorer automatisch het `DOPPELUNG`-attribuut. Daardoor is het attribuut bijzonder geschikt voor een Smart Folder of databasefilter met `DOPPELUNG = JA`. **Voor gebruik in een Smart Folder moet `DOPPELUNG` eerst als standaardattribuut in mAirList worden toegevoegd of beschikbaar gemaakt.** Voor elke echte wijziging controleert de Restorer de SQLite-integriteit, maakt hij een back-up en synchroniseert hij de markeringen in één transactie.

### Stap 3.5: Opslaan in mAirList (Apply)
Wanneer je alle tracks hebt gecontroleerd, selecteer je **[7] Gecontroleerde wijzigingen naar de databasekopie schrijven**. Voor het schrijven toont de Restorer een overzicht van de geplande veldwijzigingen en voert hij een SQLite-integriteitscontrole uit. Pas na jouw bevestiging wordt een back-up gemaakt en de bulk-write uitgevoerd. Daarna wordt de database-integriteit opnieuw gecontroleerd.

*   Het script stelt daarbij voor elke track automatisch het interne attribuut `RESTAURIERT` in op `JA`.
*   Tracks met deze vlag worden bij toekomstige runs automatisch overgeslagen.
*   Valt het je later tijdens live-gebruik op dat een track toch verkeerde tags heeft? Verwijder dan in mAirList gewoon het "RESTAURIERT"-attribuut bij deze track. De volgende keer dat het script draait, herkent de tool de track als "nieuw" en laadt deze opnieuw.