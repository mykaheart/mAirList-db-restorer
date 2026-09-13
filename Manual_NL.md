# 📖 Handleiding: mAirList DB Restorer 0.64.00 BETA

De **mAirList DB Restorer** helpt bij het onderhouden van lokale mAirList-databases (`.mldb`). Het programma leest bestaande metadata, onderzoekt ontbrekende of twijfelachtige gegevens via MusicBrainz en Discogs, kan ontbrekende BPM-waarden aanvullen vanuit rekordbox, bestandstags en AcousticBrainz en biedt verschillende onderhoudsfuncties voor bestaande databases.

De Restorer werkt bewust voorzichtig: eerst worden voorstellen gemaakt, lezen, review en schrijven blijven van elkaar gescheiden en vóór veiligheidskritische databasewijzigingen worden integriteitscontroles en back-ups uitgevoerd.

> **Belangrijk:** Het programma is bedoeld voor **lokale SQLite-databases (`.mldb`)**. Netwerkdatabases worden momenteel niet ondersteund.

---

## 1. Basisprincipe en veiligheidsgrenzen

De Restorer kan metadata aanvullen of corrigeren, maar wijzigt bepaalde technische velden nadrukkelijk **niet**:

- `Duration`, `Length` en `TotalDuration` worden nooit opnieuw berekend of overschreven.
- Audio-inhoud wordt niet geanalyseerd, geconverteerd of genormaliseerd.
- Lyrics/songteksten worden door de normale Restorer-workflow **niet uit de mAirList-database verwijderd**. Ze worden alleen uit de werk-CSV's in `Data` gehouden zodat die bestanden klein blijven.
- Bestaande geldige `BPM`-waarden worden niet automatisch overschreven.
- Het dubbele-onderhoud markeert alleen kandidaten en verwijdert nooit items.
- Gevonden SQLite-inconsistenties worden gemeld maar niet automatisch gerepareerd.

De hoofdregel is dus:

> **De machine zoekt en stelt voor; de mens beslist over inhoudelijke wijzigingen.**

---

## 2. Installatie en eerste configuratie

De release-ZIP bevat een zelfstandige `Restorer.exe`. Voor normaal gebruik is geen Python-installatie nodig.

1. Pak de ZIP volledig uit.
2. Start `Restorer.exe`.
3. Kies bij de eerste start een taal: Deutsch, English of Nederlands.
4. Voer Discogs-gegevens en een contact-e-mailadres voor MusicBrainz in.

De gegevens worden lokaal opgeslagen in `Data/config.json`. Discogs-key, Discogs-secret en MusicBrainz-contact worden daar alleen Base64-gecodeerd opgeslagen; dit is **geen cryptografische versleuteling**.

### Discogs-gegevens

Voor Discogs is een gratis ontwikkelaarstoegang nodig. Consumer Key en Consumer Secret kunnen in de ontwikkelaarsinstellingen van een Discogs-account worden aangemaakt.

### MusicBrainz-contact

MusicBrainz verlangt een duidelijke User-Agent met contactmogelijkheid. Daarom vraagt de Restorer om een geldig e-mailadres. Dit wordt alleen gebruikt in de User-Agent voor MusicBrainz-verzoeken.

---

## 3. Altijd op een databasekopie werken 🛡️

De Restorer detecteert veel locksituaties en weigert schrijfacties wanneer de database duidelijk door een ander programma wordt gebruikt. Toch geldt:

**Werk nooit rechtstreeks op de productiedatabase die op dat moment in mAirList geopend is.**

Aanbevolen werkwijze:

1. Sluit mAirList of maak een actuele kopie van de `.mldb`.
2. Bewerk die kopie met de Restorer.
3. Controleer het resultaat in mAirList.
4. Vervang of promoveer pas daarna de productiedatabase.

Apply, dubbele-onderhoud en BPM-onderhoud maken bovendien een back-up met tijdstempel naast de database. Automatisch worden de **vijf nieuwste** Restorer-back-ups bewaard.

---

## 4. De map `Data`: werkstanden, logs en configuratie

De Restorer maakt automatisch een map `Data` naast de toepassing. Daarin kunnen onder andere staan:

- `config.json` – taal, API-gegevens, ignore-lijsten en het voorkeurs-pad naar rekordbox XML per database.
- `*_vorschlaege.csv` – lopende Fetch-werkstand.
- `*_restauriert.csv` – gereviewde werkstand voor Apply.
- `*_bpm-review_YYYYMMDD-HHMMSS.csv` – volledige BPM-reviewlijst van het onderhoud.
- `*.log` – logbestanden met tijdstempel.

### Werkstanden zonder naamconflicten

De werkbestandsnaam bevat naast de databasenaam ook een korte hash van het volledige databasepad. Twee gelijknamige `.mldb`-bestanden in verschillende mappen kunnen daardoor niet per ongeluk dezelfde werkstand gebruiken.

Oudere werkbestanden worden waar mogelijk gemigreerd. Bestaat de doelnaam al, dan wordt niets overschreven en blijven beide bestanden behouden.

### Lyrics

Lyrics-kolommen worden bewust verwijderd wanneer werk-CSV's worden opgeslagen. Dit geldt **alleen voor de Restorer-werkbestanden**. De waarden in de `.mldb` blijven onaangeroerd.

---

## 5. Hoofdmenu en aanbevolen workflow

De normale metadata-workflow is:

**[1] of [2] of [3] Fetch → [4] of [5] Review → [7] Apply**

Andere opties:

- **[0]** database selecteren
- **[6]** onderhoudsmenu
- **[8]** taal wijzigen
- **[9]** afsluiten

---

## 6. Database selecteren en ignore-lijsten

Na keuze **[0]** kan het pad naar de `.mldb` worden ingevoerd of het bestand naar het consolevenster worden gesleept.

Vóór de eerste Fetch vraagt de Restorer om mappen die genegeerd moeten worden. Typische voorbeelden zijn `OAD`, jingles, nieuws, reclame of andere gebieden die niet door metadataonderzoek moeten lopen.

De ignore-lijst kan bestaan uit:

- fysieke paden,
- virtuele mAirList-mapnamen,
- gedeeltelijke mapnamen.

Deze wordt **per databasepad** in `config.json` opgeslagen. Bij een volgende run kan de lijst worden behouden of opnieuw opgebouwd.

De opgeslagen ignore-lijst wordt ook gebruikt door dubbele- en BPM-onderhoud. De eenvoudige onderhoudsfuncties voor genre en hoofd-/kleine letters schrijven rechtstreeks naar de relevante databasevelden en gebruiken deze ignore-lijst niet.

---

## 7. Fetch: metadata onderzoeken

### [1] Nieuwe/open tracks in blokken van 50

Haalt alleen openstaande titels op. Na elke 50 verwerkte tracks kan worden gepauzeerd en naar Review worden gegaan. De werkstand wordt regelmatig atomair opgeslagen.

### [2] Alle open tracks zonder pauze

Dezelfde logica als [1], maar zonder blokpauzes. Geschikt voor langere onbeheerde runs.

### [3] Full Fetch

Controleert alle relevante tracks opnieuw, ook tracks die al `RESTAURIERT=JA` hebben.

Bij Full Fetch wordt eerst de actuele database-inhoud opnieuw naar de werkstand gesynchroniseerd. De betreffende regels krijgen intern `FORCE_APPLY=JA`, zodat bewust opnieuw beoordeelde metadata later ondanks de normale bescherming van gerestaureerde tracks kan worden geschreven.

**Belangrijk:** Ook bij Full Fetch blijven bestaande geldige BPM-waarden beschermd.

### Welke items worden niet normaal gefetcht?

Systeem-/niet-muziektypen zoals `Dummy`, `Stream`, `Command`, `Silence` en `Other` worden uit de normale API-Fetch gefilterd. Ook je ignore-lijst wordt toegepast.

### Welke velden kunnen worden onderzocht of voorgesteld?

| Veld | Gedrag |
| --- | --- |
| Artist | voorstel voor schrijfwijze/opschoning |
| Title | voorstel voor schrijfwijze/opschoning |
| Jaar | MusicBrainz + Discogs met plausibiliteits-/uitbijterlogica |
| Genre | Discogs, daarna mapping naar de Restorer-genreset |
| Album | Discogs of MusicBrainz |
| STYLE | Discogs styles |
| DISCOGS_RELEASE_ID | gekozen Discogs-referentie |
| Label | Discogs |
| Labelcode | Discogs/MusicBrainz-hulpopzoeking waar beschikbaar |
| ISRC | MusicBrainz |
| Taal | wordt niet blind uit een MusicBrainz-release-taal afgeleid; zonder betrouwbare bron blijft dit onder handmatige controle |
| Soort | alleen voorgesteld wanneer het attribuut leeg is, gebaseerd op het interne mAirList-itemtype |
| BPM | rekordbox XML → bestandstag → MusicBrainz/AcousticBrainz |

### Matching op speelduur

Waar mogelijk wordt de lokale speelduur gebruikt als identificatiehulp. Deze wordt **nooit gewijzigd**.

### Releasejaar en uitbijters

De Restorer verzamelt plausibele releasejaren en filtert extreme eenmalige uitbijters. Het doel is het oorspronkelijke of vroegst plausibele releasejaar, niet het jaar van een latere compilatie.

### API-fouten en hervatten

MusicBrainz-, Discogs- en AcousticBrainz-verzoeken gebruiken retry-/rate-limit-logica. Daarnaast start de normale Fetch bij **tijdelijke** fouten de volledige trackopzoeking automatisch opnieuw: maximaal drie herpogingen met oplopende wachttijden van 2, 5 en 10 seconden. Deze track-retries gelden alleen voor netwerk/time-out, HTTP 429 en retrybare 5xx-fouten. `Retry-After` of beschikbare rate-limit-resetinformatie van de server wordt gerespecteerd en kan de wachttijd verlengen. Niet-tijdelijke 4xx-/logische fouten worden niet zinloos herhaald. Pas wanneer ook de automatische herpogingen mislukken, blijft de track open (`FEHLER`) voor een latere Fetch.

`Ctrl+C` beëindigt een Fetch gecontroleerd en slaat de huidige werkstand op.

---

## 8. BPM in de normale Fetch

Sinds 0.64 maakt BPM-opzoeking deel uit van de normale Fetch-workflow.

### rekordbox XML selecteren

Vóór een normale Fetch kan een rekordbox-XML-export worden opgegeven. Het gekozen pad wordt **per database** opgeslagen en de volgende keer als standaard getoond.

- `Enter` gebruikt het getoonde standaardpad.
- `-` schakelt XML-gebruik uit en verwijdert het opgeslagen pad voor die database.
- Als er nog geen opgeslagen pad is, zoekt de Restorer ook naar `rekordbox.xml` naast de toepassing en in de map `Data`.
- Ontbreekt de XML of is deze ongeldig, dan gaat de metadata-Fetch door en gebruikt BPM de andere bronnen.

### Bronprioriteit

Voor een track zonder geldige BPM:

1. **rekordbox XML** – `AverageBpm`, alleen wanneer `Location` exact naar hetzelfde bestandspad verwijst.
2. **Audiobestandstag** – bijvoorbeeld ID3 `TBPM` of Vorbis/FLAC `BPM`/`tempo`.
3. **MusicBrainz Recording-ID** – bij voorkeur via geldige ISRC, anders conservatieve matching op Artist/Title/speelduur.
4. **AcousticBrainz** – Low-Level BPM alleen voor een veilig geïdentificeerde MusicBrainz-opname.

Voor rekordbox wordt **geen fuzzy Artist-/Title-matching** gebruikt. Het bestandspad is de identiteit.

### Bescherming van bestaande BPM

Als de live database al een geldige BPM bevat, wordt voor dat item geen nieuw BPM-voorstel gemaakt, ook niet bij Full Fetch.

### Gedrag in Review

Een nieuwe `BPM_Vorschlag` wordt in de normale Review getoond en automatisch naar `BPM` gekopieerd. De bron blijft in de werkstand staan als `BPM_Quelle`. De bron zelf wordt niet als mAirList-attribuut geschreven.

Een fout die alleen de BPM-fallback betreft maakt de overige metadata niet onbruikbaar. Als de trackidentiteit tijdens Review handmatig wordt gewijzigd, wordt een eerder via AcousticBrainz gevonden BPM-voorstel voor de veiligheid verwijderd; rekordbox- en bestandstag-BPM blijven aan het concrete bestand gekoppeld. De andere metadata kan normaal verder worden verwerkt en ontbrekende BPM kan later apart via onderhoud [6] worden aangevuld.

---

## 9. `RESTAURIERT`, hervatten en resetgedrag

Na succesvolle Apply zet de Restorer `RESTAURIERT=JA` op geschreven tracks.

Normale latere Fetch-runs beschermen en slaan deze tracks over.

Als je in mAirList het attribuut `RESTAURIERT` bij een track verwijdert, wordt de `.mldb` bij de volgende run opnieuw de bron van waarheid. De verouderde werkstatus wordt gereset en de oorspronkelijke velden van die track worden opnieuw uit de database geladen voordat hij weer wordt gefetcht.

Full Fetch is de bewuste uitzondering. De werkregels krijgen `FORCE_APPLY=JA`, zodat bewust opnieuw beoordeelde metadata ook bij al gerestaureerde tracks mag worden geschreven. Na succesvolle Apply wordt `FORCE_APPLY` weer geleegd.

---

## 10. Review: voorstellen controleren

### [4] Handmatige Review

Elke open, succesvol gefetchte track wordt afzonderlijk getoond.

Voor interactieve velden geldt:

- **Enter** – voorstel accepteren.
- **o** – originele waarde behouden.
- **eigen tekst** – eigen waarde invoeren.
- **`<` of `b`** – één track terug.

### [5] Review met automatisering

Jaar- en Genre-voorstellen met hoge betrouwbaarheid kunnen automatisch worden overgenomen. Andere velden blijven controleerbaar zoals in de handmatige modus.

### Live re-fetch

Als Artist, Title, Jaar of Album handmatig wordt gewijzigd, voert de Restorer een gerichte nieuwe MusicBrainz-/Discogs-opzoeking uit zodat afhankelijke voorstellen zoals Genre, Label, Labelcode, ISRC, STYLE en Discogs-ID bij de gecorrigeerde identiteit passen.

### Automatisch overgenomen technische velden

Wanneer een veilig voorstel bestaat, worden `STYLE`, `DISCOGS_RELEASE_ID`, `Labelcode`, `ISRC`, `Soort` en `BPM` zonder extra individuele vraag naar de gereviewde werkstand gekopieerd. Bestaande BPM is al eerder beschermd en krijgt daarom geen nieuw voorstel.

### Taal

MusicBrainz levert in deze workflow geen betrouwbare recording-taal. De Restorer leidt taal daarom niet af uit een willekeurig release-taalveld. Bestaande waarden blijven staan en taal kan indien nodig handmatig in Review worden ingesteld. Vaak gebruikte eigen talen worden in `config.json` onthouden.

---

## 11. Apply: gereviewde wijzigingen veilig naar `.mldb` schrijven

Optie **[7]** schrijft alleen tracks waarvan de Review voltooid is.

Vóór het schrijven gebeurt:

1. bescherming van reeds `RESTAURIERT=JA` gemarkeerde tracks.
2. bewuste uitzondering voor `FORCE_APPLY=JA` uit Full Fetch.
3. SQLite `integrity_check`.
4. overzicht van de werkelijk geplande veldwijzigingen, inclusief BPM.
5. veiligheidsbevestiging.
6. `.mldb`-back-up met tijdstempel.
7. opruimen van oude Restorer-back-ups; de nieuwste vijf blijven staan.
8. gebundeld schrijven naar de database.
9. tweede SQLite-integriteitscontrole.
10. synchronisatie van werk-CSV's en zetten van `RESTAURIERT=JA`.

Als de integriteitscontrole **vóór** het schrijven mislukt, wordt niets gewijzigd. Meldingen zoals `wrong # of entries in index ...` duiden doorgaans op een reeds bestaand SQLite-/indexprobleem. De Restorer repareert databasestructuren bewust niet automatisch.

---

## 12. Onderhoudsmenu [6]

Het onderhoudsmenu bevat directe database-/bestandsbewerkingen en staat los van de normale Fetch/Review/Apply-workflow.

> **Waarschuwing:** Eenvoudige onderhoudsopties [1]–[4] schrijven direct. Maak vooraf zelf een database- of bestandskopie. De uitgebreidere opties [5] en [6] hebben extra ingebouwde integriteits-/back-upbeveiliging.

### Onderhoud [1] – Genres standaardiseren

Bestaande genres worden gemapt naar de kerncategorieën van de Restorer, waaronder momenteel:

`Pop`, `EDM`, `Blues`, `Hiphop`, `Rap`, `Rock`, `Classic Rock`, `Pop-Rock`, `R and B`, `Soul`, `Reggae`.

Zowel een native genreveld als een genre-attribuut wordt verwerkt wanneer het databaseschema dit bevat.

### Onderhoud [2] – Hoofd-/kleine letters en apostrofs corrigeren

Artist en Title worden genormaliseerd naar consistente apostrofs en intelligente hoofd-/kleine letters. Deze functie schrijft rechtstreeks naar de betreffende `items`-velden.

### Onderhoud [3] – Bestandstagger

Schrijft **gereviewde databasewaarden naar lokale audiobestanden** via Mutagen. Ondersteunde formaten:

- FLAC
- Ogg Vorbis
- MP3
- AIFF

Geschreven velden:

- Artist
- Title
- Jaar/Date
- Genre
- Album
- Label/Publisher

BPM, ISRC, Labelcode, Taal en Lyrics worden niet door deze bestandstagger geschreven.

Omdat mAirList paden vaak relatief aan Storage Locations opslaat, vraagt de tagger om lokale basismappen. De audiobestanden worden direct gewijzigd en er is geen Undo-functie; een bestandsback-up wordt daarom aanbevolen.

### Onderhoud [4] – Gecombineerde run

Voert **alleen onderhoud [1] en [2]** na elkaar uit. De bestandstagger hoort niet bij deze gecombineerde actie.

---

## 13. Onderhoud [5] – Dubbele kandidaten

De dubbele controle is een **reviewhulp**, geen automatische verwijderfunctie.

Muziekitems worden als kandidaten gekoppeld wanneer minstens één sterk criterium overeenkomt:

- dezelfde genormaliseerde Artist + Title,
- hetzelfde opgeslagen bestandspad,
- dezelfde geldige ISRC.

Verschillende speelduur voorkomt bewust geen match, omdat Radio Edits, albumversies, remasters of andere varianten later door een mens moeten worden beoordeeld.

### Wat wordt geschreven?

Kandidaten krijgen:

`DOPPELUNG=JA`

Geen track wordt automatisch verwijderd en geen kandidaat wordt als “fout” verklaard.

Bij een volgende scan wordt de status opnieuw uit de actuele database opgebouwd. Bestaat een eerdere partner niet meer, dan wordt de verouderde `DOPPELUNG`-markering verwijderd.

### Aanbevolen Smart Folder in mAirList

Maak `DOPPELUNG` beschikbaar als standaardattribuut en gebruik bijvoorbeeld:

- Attribuut: `DOPPELUNG`
- Voorwaarde: `is one of`
- Waarde: `JA`

### Veiligheid

Wanneer een wijziging nodig is:

1. integriteitscontrole
2. back-up
3. één databasetransactie voor de nieuwe status
4. tweede integriteitscontrole

---

## 14. Onderhoud [6] – Ontbrekende BPM direct aanvullen

Deze optie blijft bestaan voor puur BPM-onderhoud, ook nu BPM-opzoeking in de normale Fetch is geïntegreerd.

Ze werkt alleen op bestandsgebonden muziekitems zonder geldige BPM.

### rekordbox XML

Dezelfde per database opgeslagen rekordbox-XML-keuze als bij de normale Fetch kan opnieuw worden gebruikt. rekordbox levert `AverageBpm`; de Restorer accepteert dit alleen bij exact gelijk bestandspad.

### Fallbacks

Als rekordbox geen passende waarde levert:

1. BPM uit de lokale audiobestandstag lezen.
2. MusicBrainz-opname via ISRC of conservatieve matching identificeren.
3. AcousticBrainz Low-Level BPM opvragen.

Bij meerdere AcousticBrainz-analyses wordt alleen een nauwe consensus geaccepteerd. Onduidelijke Half-/Double-Time-situaties worden afgewezen.

### Voorbeeld, diagnose en review-CSV

Vóór het schrijven toont het onderhoud een voorbeeld en samenvatting. Daarnaast wordt in `Data` een volledige BPM-review-CSV aangemaakt met onder andere:

- ID
- Artist
- Title
- voorgestelde BPM
- bestaande BPM
- oorspronkelijke bron-BPM
- Bron
- Status
- AcousticBrainz-consensus
- Recording MBID
- matchingmethode

Niet-treffers en fouten worden per oorzaak opgesplitst, bijvoorbeeld:

- audiobestand niet bereikbaar
- bestandstag niet leesbaar
- geen eenduidige MusicBrainz-opname
- MusicBrainz netwerk/time-out, 429, 5xx of andere HTTP-fout
- AcousticBrainz zonder datasetrecord
- AcousticBrainz-record zonder bruikbare BPM
- geen veilige AcousticBrainz-consensus
- AcousticBrainz netwerk/rate-limit/serverfout

### Half-/Double-Time-conflicten

Als al een geldige BPM bestaat en rekordbox een duidelijk afwijkende waarde meldt, wordt niets overschreven. Typische 2:1-gevallen zoals `180 ↔ 90` worden in de review-CSV vermeld als `HALF_DOUBLE_KONFLIKT`.

Dit is bewust alleen een waarschuwing: verschillende DJ-/analyseprogramma's kunnen dezelfde muzikale puls als Half- of Double-Time tellen.

### Veiligheid

Na uitdrukkelijke bevestiging volgen:

1. integriteitscontrole
2. back-up
3. atomaire BPM-transactie
4. live-bescherming tegen BPM die tijdens de scan intussen is toegevoegd
5. tweede integriteitscontrole

`RESTAURIERT` wordt door BPM-onderhoud **niet gewijzigd**.

AcousticBrainz gebruikt minimaal 1,05 seconde basisafstand en houdt ook rekening met dynamische rate-limit-headers.

---

## 15. rekordbox-workflow voor grote bibliotheken

Voor hoge BPM-dekking:

1. Importeer de muziekbibliotheek in rekordbox.
2. Laat rekordbox alle tracks analyseren.
3. Exporteer de Collection als rekordbox XML.
4. Selecteer die XML in de normale Fetch of onderhoud [6].
5. Later kan opnieuw worden geanalyseerd/geëxporteerd; blijft de export op hetzelfde pad, dan gebruikt de Restorer het opgeslagen pad automatisch opnieuw.

De Restorer schrijft nooit terug naar de rekordbox-library.

---

## 16. Fouten en diagnose

### Database is vergrendeld

mAirList of een ander programma houdt de `.mldb` open. Sluit de toepassing of werk met een echte kopie.

### SQLite-integriteitscontrole mislukt

De Restorer breekt de schrijfactie af. De inconsistentie bestond al vóór de geplande wijziging. Er wordt geen automatische REINDEX-/repairactie uitgevoerd.

### API-fouten

Tijdelijke metadata-API-fouten veroorzaken in de normale Fetch maximaal drie volledige track-herpogingen (2/5/10 s; server-`Retry-After` wordt gerespecteerd). Alleen als de fout daarna blijft bestaan, blijft de track open. Niet-tijdelijke 4xx-fouten worden niet automatisch herhaald. Een fout die alleen de BPM-fallback betreft verhindert niet dat de overige metadata wordt gereviewd; BPM kan later via onderhoud [6] worden toegevoegd.

### Audiobestand niet gevonden

Bestandstags/BPM en de bestandstagger vereisen dat lokale paden kunnen worden opgelost. Voor BPM kan de Restorer mAirList Storage Locations uit de database oplossen; de bestandstagger laat daarnaast handmatige basismappen toe.

### rekordbox XML matcht niet

Alleen exacte bestandspaden worden geaccepteerd. Zijn bestanden na export verplaatst of verschillen storagepaden, dan valt de Restorer terug op de volgende BPM-bron.

---

## 17. Opdrachtregel voor ontwikkelaars/power-users

Normaal releasegebruik gebeurt via het interactieve menu. In Python-/broncodegebruik zijn ook fasen zoals `fetch`, `review`, `apply`, `maintenance` en `check_update` beschikbaar.

Voor Fetch zijn onder andere beschikbaar:

- `--full`
- `--no-breaks`
- `--rekordbox-xml <pad>`
- `--lang de|en|nl`

De interactieve EXE-workflow blijft de aanbevolen methode.

---

## 18. Wat de Restorer bewust niet doet

- geen wijzigingen aan trackduur
- geen audioanalyse of loudness-berekening
- geen audioformaatconversie
- geen automatische verwijdering van dubbelen
- geen automatische SQLite-reparatie
- geen afleiding van zangtaal uit een onbetrouwbaar MusicBrainz-releaseveld
- geen automatisch overschrijven van bestaande geldige BPM
- geen ondersteuning voor mAirList-netwerkdatabases

---

## 19. Tests en releaseveiligheid

De broncode bevat regressietests voor onder andere scheiding van werkstanden, uitsluiten van Lyrics, Apply-bescherming, Full-Fetch-uitzondering, dubbele status, BPM-consensus, exacte rekordbox-padmatching, Half-/Double-Time-bescherming, API-retry/rate-limits inclusief track-level retry en back-up-/bevestigingslogica.

Voor ontwikkelaars:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions voert bovendien een compile-check en de regressietests onder Windows uit.

---

## 20. Licentie en support

mAirList DB Restorer is **source-available freeware**. De exacte gebruiks- en verspreidingsvoorwaarden staan in `LICENSE`.

Gebruik voor bugreports en featurewensen de officiële projectkanalen: GitHub Issues of de officiële release-thread in het mAirList-forum.
