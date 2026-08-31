# 📖 Handleiding: mAirList DB Restorer

Welkom bij de officiële handleiding voor de **mAirList DB Restorer**! Deze tool is ontworpen om je honderden uren vervelend handwerk in de cue-editor te besparen door ontbrekende metadata (jaren, genres, albums, labels) volledig automatisch te zoeken en aan te vullen via de API's van MusicBrainz en Discogs.

Voer eenmalig de volgende korte installatie uit om ervoor te zorgen dat alles soepel verloopt.

---

## 1. Voorbereiding & Installatie

Omdat deze tool een Python-script is, heeft je computer de juiste omgeving nodig om het uit te voeren. De installatie duurt slechts ongeveer 5 minuten.

### Stap 1.1: Python installeren
1. Download de nieuwste versie van **Python** voor Windows: [python.org/downloads](https://www.python.org/downloads/)
2. Start het gedownloade `.exe`-bestand.
3. ⚠️ **EXTREEM BELANGRIJK:** Vink onderaan in het installatievenster absoluut het vakje aan bij **"Add Python to PATH"**! Als dit vakje niet is aangevinkt, zal het script later niet starten.
4. Klik op "Install Now" en wacht tot de installatie is voltooid.

### Stap 1.2: Benodigde bibliotheken installeren
Het script maakt gebruik van externe bibliotheken (bijv. voor het kleurrijke terminalmenu of CSV-export). Deze moeten eenmalig worden geïnstalleerd.
1. Druk op je toetsenbord op de `Windows-toets + R`.
2. Typ `cmd` in het venster en druk op `Enter`. (De zwarte Windows Opdrachtprompt wordt geopend).
3. Kopieer het volgende commando, plak het in het zwarte venster en druk op `Enter`:
   `pip install pandas requests rich`
4. Windows downloadt nu de vereiste pakketten. Zodra dit klaar is, kun je het venster sluiten.

### Stap 1.3: Discogs API-keys genereren
Om toegang te krijgen tot de enorme database van Discogs, heeft het script een (gratis) API-sleutel nodig.
1. Maak een gratis account aan op [discogs.com](https://www.discogs.com) (als je dat nog niet hebt) en log in.
2. Klik rechtsboven op je profielfoto en kies **Instellingen** (Settings).
3. Ga in het linker menu helemaal naar beneden naar **Ontwikkelaars** (Developers).
4. Klik op de knop **"Create an App"** (of Generate Token).
5. Geef een willekeurige naam op voor de app (bijv. "mAirList Restorer").
6. Je ontvangt nu twee belangrijke cryptische reeksen: De **Consumer Key** en de **Consumer Secret**.
7. Kopieer beide waardes. Bij de allereerste start van `Restore.bat` zal het script hiernaar vragen en ze veilig en gemaskeerd opslaan.

---

## 2. De Gouden Regel: Back-ups! 🛡️

Het allerbelangrijkste bij het werken met databases is gegevensbeveiliging. De mAirList DB Restorer grijpt diep in de structuur in en herschrijft metadata volledig automatisch.

⚠️ **Werk NOOIT met het actieve databasebestand (`.mldb`) dat mAirList op dat moment geopend heeft!**

Wanneer mAirList actief is, vergrendelt (lockt) het het databasebestand. Als het Python-script tegelijkertijd probeert nieuwe genres of jaartallen naar dit bestand te schrijven, kan de database in het worst-case scenario onherstelbaar beschadigd raken.

### De veilige workflow:
1. Sluit mAirList of open Windows Verkenner en navigeer naar de map waarin je `.mldb`-bestand zich bevindt.
2. Kopieer het bestand (bijv. `Archief.mldb`) en plak het op een veilige plek, zoals je **Bureaublad**.
3. Start `Restore.bat`.
4. Wanneer het script vraagt naar het pad van de database, **typ dit dan niet moeizaam in**!
5. 💡 **Pro-tip:** Klik op het gekopieerde `.mldb`-bestand op je bureaublad, houd de muisknop ingedrukt en **sleep het bestand via drag & drop direct naar het zwarte consolevenster**. Druk op `Enter`. Het pad is nu perfect ingesteld.
6. Zodra je klaar bent met de tool en alle nieuwe metadata in de kopie is opgeslagen, sluit je mAirList, vervang je het oude bestand door je nieuwe, bewerkte kopie en start je mAirList opnieuw op.

---

## 3. De Workflow: Metadata herstellen

Zodra je `Restore.bat` hebt gestart en je databasekopie hebt geselecteerd, leidt het hoofdmenu je logisch door het hele proces.

### Stap 3.1: Map-uitzonderingen definiëren (Ignore-lijst)
Voordat het script bij de eerste fetch begint met zoeken, vraagt het naar mappen die **consequent genegeerd** moeten worden (bijv. mappen voor jingles, nieuws, drops of reclame).
*   **Eenvoudige invoer:** Je kunt de fysieke map vanuit Windows Verkenner eenvoudig via drag & drop naar binnen slepen of de exacte naam van een virtuele mAirList-map intypen. Druk op een lege regel op `Enter` wanneer je klaar bent met de lijst.
*   **Individueel per database:** Het script is slim en onthoudt deze uitzonderingslijst individueel voor precies die geladen `.mldb`-file!
*   **Altijd aanpasbaar:** Start je de tool later opnieuw op met dezelfde database, dan toont het de huidige ignore-lijst en vraagt het of je deze wilt behouden of opnieuw wilt aanmaken.

### Stap 3.2: Metadata ophalen (Fetch)
In deze fase zoekt het script via de API's van MusicBrainz en Discogs naar passende metadata voor je tracks. Je originele waardes blijven hierbij volledig onaangetast! Je hebt drie opties:

*   **[1] Smart-Fetch (Standaard):** De tool controleert alleen tracks die *nog niet* zijn hersteld. Om je te beschermen tegen een gigantische lijst, pauzeert het script automatisch na het laden van 50 tracks. Je kunt dan direct doorgaan naar de review of de volgende 50 laden.
*   **[2] Smart-Fetch (Overnight):** Perfect voor enorme databases. Het script laadt alle nieuwe tracks in één keer door zonder pauzes. Ideaal om de pc 's nachts te laten werken.
*   **[3] Full-Fetch (Reset & Overnight):** Het script negeert de "RESTAURIERT"-flag en haalt de data voor **ALLE** tracks in de database volledig opnieuw op.

> **Tip:** Je kunt het fetch-proces op elk moment afbreken met de toetscombinatie `Ctrl + C`. Het script slaat je huidige voortgang veilig op, zodat je bij de volgende start precies op dat punt kunt doorgaan!

### Stap 3.3: Data controleren (Review)
Hier presenteert de tool je elke track afzonderlijk en stelt de op internet gevonden metadata voor.

*   **Bevestigen:** Als een suggestie (bijv. het jaar) goed is, druk je simpelweg op `Enter`. De tool neemt de waarde over en gaat door naar het volgende veld.
*   **Origineel behouden (`O`-toets):** Naast de suggestie zie je in het grijs altijd je oorspronkelijke databasewaarde staan. Is jouw eigen waarde beter? Typ dan simpelweg `o` (van Origineel) in en druk op `Enter`.
*   **Eigen tekst:** De suggestie is fout, maar je originele waarde ook? Typ dan gewoon je gewenste tekst in.
*   **Live Re-Fetch:** Als je bij artiest, titel, jaar of album een eigen tekst intypt (bijv. om een typefout in de artiestennaam te herstellen), stuurt het script onmiddellijk een nieuwe API-zoekopdracht op de achtergrond en past het labels, genres en ISRC live aan op jouw correctie!
*   **Oeps, vertypt?** Typ `<` of `b` (van Back) in en druk op `Enter` om één track terug te gaan.

### Stap 3.4: Opslaan in mAirList (Apply)
Zodra je alle tracks hebt gecontroleerd, kies je in het hoofdmenu optie **[7] Opslaan**. Pas dan opent het script je databasekopie en schrijft het de nieuwe, schone metadata erin.

*   Het script stelt hierbij automatisch het interne attribuut `RESTAURIERT` in op `JA` voor elke verwerkte track.
*   Tracks met deze flag worden bij toekomstige runs automatisch overgeslagen.
*   Merk je tijdens de live-uitzending later dat een track toch verkeerde tags heeft? Verwijder in mAirList dan eenvoudig het "RESTAURIERT"-attribuut bij die track. Bij de volgende script-run herkent de tool de track als "nieuw" en haalt deze opnieuw op.

---

## 4. Het Onderhoudsmenu (Massabewerking)

Via optie **[6] Onderhoud** in het hoofdmenu krijg je toegang tot een krachtige speciaaltool voor diepgaande database-ingrepen.

⚠️ **WAARSCHUWING:** Alle functies in dit menu schrijven **rechtstreeks** naar de database. Er is hier geen voorafgaande review-stap en geen "Undo"!

*   **[1] Genres standaardiseren:** Scant de gehele database en brengt wildgroei in genres (bijv. "Deep House" of "Trance") terug naar een schone hoofdcategorie (bijv. "EDM").
*   **[2] Hoofdletters/kleine letters & apostrofs corrigeren:** Repareert verkeerde aanhalingstekens (´, `, ‘ worden ') in artiest- en titelsamenstellingen. Daarnaast wordt "Title Case" toegepast (elk woord begint met een hoofdletter). Uitzonderingen zoals "AC/DC" of "a-ha" worden beschermd door een VIP-lijst.
*   **[3] 'Platinum Notes' & 'Lyrics' verwijderen:** DJ-software vervuilt mAirList vaak met onzichtbare attributen zoals langere songteksten. Deze optie wist deze data volledig en verkleint je databasebestand merkbaar.

---

## 5. FAQ & Troubleshooting

**Waarom springt het script tijdens de review niet naar de volgende track?**
De tool wacht op invoer. Druk bij lege velden simpelweg op `Enter` om naar de volgende stap te gaan.

**Waarom vindt het script mijn jingle-pakketten niet?**
Dat is opzettelijk! Het script heeft een ingebouwde OAD-bescherming (On Air Design). Het negeert automatisch alle tracks in mappen die op jouw ignore-lijst staan.

**Het script vertoont kleurrijke foutmeldingen (timeouts) tijdens het fetchen!**
Geen paniek, de "airbag" is geactiveerd. Als de servers van Discogs of MusicBrainz tijdelijk niet reageren (timeout), crasht het script niet. Het logt de fout, slaat die ene track over en gaat naadloos door met de volgende.