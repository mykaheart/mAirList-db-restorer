# 📖 Handleiding: mAirList DB Restorer[cite: 6]

Welkom bij de officiële handleiding voor de **mAirList DB Restorer**![cite: 6] Deze tool is ontwikkeld om je honderden uren vervelend handmatig werk in de Cue-Editor te besparen door ontbrekende metadata (jaren, genres, albums, labels) volautomatisch via de API's van MusicBrainz en Discogs te zoeken en aan te vullen.[cite: 6]

Dankzij de "All-in-One"-architectuur is het programma direct klaar voor gebruik – zonder ingewikkelde installatie![cite: 6] Om ervoor te zorgen dat alles soepel verloopt, verzoeken wij je om eenmalig de volgende korte instellingsprocedure te doorlopen.[cite: 6]

---

## 1. Voorbereiding & Installatie[cite: 6]

De tool is een volledig op zichzelf staande applicatie (`.exe`).[cite: 6] Je hoeft geen Python of andere codebibliotheken te installeren.[cite: 6] Download gewoon het huidige ZIP-bestand, pak het uit op een locatie naar keuze en start het bestand **`mAirList-DB-Restorer.exe`**.[cite: 6]

### Stap 1.1: Discogs API-Keys genereren[cite: 6]
Om toegang te krijgen tot de enorme database van Discogs, heeft het script een gratis API-sleutel nodig.[cite: 6]
1. Maak een gratis account aan op [discogs.com](https://www.discogs.com) (als je er nog geen hebt) en log in.[cite: 6]
2. Klik rechtsboven op je profielfoto en selecteer **Instellingen** (Settings).[cite: 6]
3. Ga in het linkermenu helemaal naar beneden naar **Ontwikkelaars** (Developers).[cite: 6]
4. Klik op de knop **"Create an App"** (of Generate Token).[cite: 6]
5. Voer een willekeurige naam in voor de app (bijv. "mAirList Restorer").[cite: 6]
6. Je ontvangt nu twee belangrijke cryptische tekenreeksen: De **Consumer Key** en het **Consumer Secret**.[cite: 6]
7. Kopieer deze twee waarden.[cite: 6] Bij de allereerste start van de `.exe` zal het programma je ernaar vragen en ze veilig lokaal opslaan.[cite: 6]

---

## 2. De gouden regel: Back-ups! 🛡️[cite: 6]

Het belangrijkste bij het werken met databases is gegevensbeveiliging.[cite: 6] De mAirList DB Restorer grijpt diep in de structuur in en herschrijft metadata volautomatisch.[cite: 6]

⚠️ **Werk NOOIT met het actieve databasebestand (`.mldb`) dat mAirList op dit moment geopend heeft!**[cite: 6]
Wanneer mAirList draait, vergrendelt (lockt) het het databasebestand.[cite: 6] Als de tool nu probeert tegelijkertijd nieuwe genres of jaartallen in dit bestand te schrijven, kan de database in het ergste geval onherstelbaar beschadigd raken.[cite: 6] Het script heeft weliswaar een ingebouwde beveiliging die vergrendelde bestanden detecteert, maar voorkomen is beter dan genezen.[cite: 6]

### De Veilige Workflow:[cite: 6]
1. Sluit mAirList of open de Windows Verkenner en navigeer naar de map waar je `.mldb`-bestand staat.[cite: 6]
2. Kopieer het bestand (bijv. `Archief.mldb`) en plak het op een veilige plek, zoals je **Bureaublad**.[cite: 6]
3. Start de `Restorer.exe`.[cite: 6]
4. Wanneer het script in het menu naar het pad naar de database vraagt, **typ het dan niet moeizaam in**![cite: 6]
5. 💡 **Pro-Tip:** Klik gewoon op het gekopieerde `.mldb`-bestand op je bureaublad, houd de muisknop ingedrukt en **sleep het bestand direct in het venster**.[cite: 6] Druk op `Enter`.[cite: 6] Het pad is nu perfect ingevuld![cite: 6]
6. Als je klaar bent met de tool en alle nieuwe metadata in de kopie hebt opgeslagen, sluit je mAirList, vervang je het oude bestand door je nieuwe, bewerkte kopie en start je mAirList opnieuw.[cite: 6]

---

## 3. De Workflow: Metadata herstellen[cite: 6]

Bij de eerste start vraagt de tool je naar je voorkeurstaal (Duits, Engels, Nederlands).[cite: 6] Het script onthoudt deze instelling voor de toekomst.[cite: 6] Via Optie **[9]** in het hoofdmenu kun je dit op elk moment weer wijzigen.[cite: 6]
Zodra je je databasekopie hebt geladen, leidt het interactieve menu je logisch door het hele proces.[cite: 6] *Let op: Het script maakt automatisch een map genaamd `Data` aan waarin het alle logs en tussentijdse opslag netjes bewaart.*[cite: 6]

### Stap 3.1: Map-uitzonderingen definiëren (Ignore-List)[cite: 6]
Voordat het script tijdens de eerste fetch met zoeken begint, vraagt het je naar mappen die **consequent genegeerd** moeten worden (bijv. mappen voor Jingles, News, Drops of Reclame).[cite: 6]
*   **Eenvoudige invoer:** Je kunt hier de fysieke map vanuit de Windows Verkenner gewoon in slepen via Drag & Drop of de exacte naam van een virtuele mAirList-map typen.[cite: 6] Druk bij een lege invoer op `Enter` als je klaar bent met de lijst.[cite: 6]
*   **Individueel per database:** Het script is slim en onthoudt deze uitzonderingslijst individueel voor precies dit geladen `.mldb`-bestand![cite: 6]
*   **Altijd aanpasbaar:** Als je de tool later opnieuw start met dezelfde database, toont het je de huidige ignore-list en vraagt het of je deze wilt behouden of een nieuwe wilt maken.[cite: 6]

### Stap 3.2: Metadata ophalen (Fetch)[cite: 6]
In deze fase zoekt het script via de API's van MusicBrainz en Discogs naar de passende metadata voor je tracks.[cite: 6] Je originele waarden blijven daarbij volledig onaangetast![cite: 6]

*   **[1] Smart-Fetch (Standaard):** De tool controleert alleen tracks die nog *niet* hersteld zijn.[cite: 6] Om je niet te overweldigen met een enorme lijst, pauzeert het script automatisch na 50 geladen tracks.[cite: 6] Je kunt dan direct overschakelen naar de review of de volgende 50 laden.[cite: 6]
*   **[2] Smart-Fetch (Overnight):** Perfect voor enorme databases.[cite: 6] Het script laadt alle nieuwe tracks in één keer door zonder pauzes.[cite: 6] Ideaal om de pc 's nachts te laten werken.[cite: 6]
*   **[3] Full-Fetch (Reset & Overnight):** Het script negeert de "RESTAURIERT" (HERSTELD) vlag en haalt de gegevens voor **ALLE** tracks in de database volledig opnieuw op.[cite: 6]

> **Tip:** Je kunt het fetch-proces op elk moment annuleren met de toetsencombinatie `Ctrl + C`.[cite: 6] Het script slaat je voortgang tot dan toe veilig op, en je kunt de volgende keer bij het starten precies op dit punt verdergaan![cite: 6]

### Stap 3.3: Data controleren (Review)[cite: 6]
Kies Optie **[4]** of **[5]**.[cite: 6] Hier presenteert de tool je elke track afzonderlijk en stelt het de op internet gevonden metadata voor.[cite: 6]

*   **Bevestigen:** Als een suggestie je bevalt (bijv. het jaar), druk dan gewoon op `Enter`.[cite: 6] De tool neemt de waarde over en springt naar het volgende veld.[cite: 6]
*   **Origineel behouden (`O`-toets):** Naast de suggestie zie je altijd in het grijs je oorspronkelijke database-waarde.[cite: 6] Is je eigen waarde beter?[cite: 6] Typ gewoon een `o` (voor origineel) en druk op `Enter`.[cite: 6]
*   **Eigen tekst:** Is de suggestie fout, maar je originele waarde ook?[cite: 6] Typ dan gewoon je gewenste tekst in.[cite: 6]
*   **Live Re-Fetch:** Als je bij Artiest, Titel, Jaar of Album een eigen tekst typt (bijv. om een typfout in de artiestennaam te corrigeren), vuurt het script op de achtergrond direct een nieuwe API-zoekopdracht af en past het Labels, Genres en ISRC live aan je correctie aan![cite: 6]
*   **Oeps, typfout?** Typ een `<` of `b` (voor Back) en druk op `Enter` om één track terug te springen.[cite: 6]

### Stap 3.4: Onderhoud (Maintenance)[cite: 6]
Onder Optie **[6]** vind je krachtige hulpmiddelen voor massabewerking.[cite: 6] Hier kun je onder andere slordige genres standaardiseren, foutieve hoofdletters/kleine letters repareren (Title Case), oude attributen zoals "Lyrics" verwijderen (om de database te verkleinen) of de Engelse mAirList Item Types (bijv. "Music") volautomatisch laten vertalen naar je lokale taal.[cite: 6]

### Stap 3.5: Opslaan in mAirList (Apply)[cite: 6]
Wanneer je alle tracks hebt gecontroleerd, selecteer je in het hoofdmenu Optie **[7] Opslaan**.[cite: 6] Pas dan opent het script je databasekopie en schrijft het de nieuwe, schone metadata erin via een snel bulk-proces.[cite: 6]

*   Het script stelt daarbij voor elke track automatisch het interne attribuut `RESTAURIERT` in op `JA`.[cite: 6]
*   Tracks met deze vlag worden bij toekomstige runs automatisch overgeslagen.[cite: 6]
*   Valt het je later tijdens live-gebruik op dat een track toch verkeerde tags heeft?[cite: 6] Verwijder dan in mAirList gewoon het "RESTAURIERT"-attribuut bij deze track.[cite: 6] De volgende keer dat het script draait, herkent de tool de track als "nieuw" en laadt deze opnieuw.[cite: 6]