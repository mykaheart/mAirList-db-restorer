# Changelog

Alle belangrijke wijzigingen aan dit project worden in dit bestand gedocumenteerd.

## [0.64.00 Beta] - 2026-09-13
### Toegevoegd
- **BPM maakt nu deel uit van de normale Fetch:** Ontbrekende `BPM`-waarden worden tijdens de gewone Fetch als `BPM_Vorschlag` gevonden en in Review automatisch overgenomen. Bestaande geldige BPM blijft ook bij Full Fetch beschermd.
- **rekordbox XML als primaire BPM-bron:** `AverageBpm` wordt uitsluitend via het exacte bestandspad uit `Location` gekoppeld; er wordt geen fuzzy matching op Artiest/Titel gebruikt.
- **rekordbox-pad per database onthouden:** Het in de normale Fetch gekozen XML-pad wordt per `.mldb` in `Data/config.json` opgeslagen. `Enter` gebruikt de standaard, `-` schakelt uit en verwijdert het pad; `rekordbox.xml` naast de toepassing of in `Data` wordt automatisch gevonden wanneer nog geen pad is opgeslagen.
- **Meerstaps BPM-keten:** rekordbox XML → audiobestandstag → conservatieve MusicBrainz Recording-match → AcousticBrainz Low-Level BPM.
- **BPM-onderhoudsoptie [6] blijft bestaan:** BPM-only-nazorg blijft mogelijk zonder volledige metadata-Fetch.
- **Conservatieve MusicBrainz-matching:** ISRC heeft voorrang; zonder veilige ISRC-match moeten Artiest, Titel, MusicBrainz-score en speelduur nauw overeenkomen. Dubbelzinnige recordings worden verworpen.
- **AcousticBrainz-consensus:** Meerdere analyses worden alleen geaccepteerd wanneer ze nauw overeenkomen. Half/double-time-conflicten blijven bewust leeg.
- **Volledige BPM-review-CSV in onderhoud [6]:** Elke run bewaart voorstellen plus beschermde duidelijke rekordbox-afwijkingen in `Data`, inclusief bestaande BPM, oorspronkelijke bron-BPM, status, bron, consensus, recording-MBID en matchmethode.
- **Gedetailleerde BPM-diagnose:** Niet-treffers en fouten worden per oorzaak opgesplitst, waaronder onbereikbare audiobestanden, geen eenduidige MusicBrainz-recording, AcousticBrainz zonder data/consensus, netwerkfouten, HTTP 429 en serverfouten.
- **CLI-uitbreiding:** `fetch` accepteert nu optioneel `--rekordbox-xml <pad>`.

### Veiligheid
- **Geen BPM-overschrijving:** Bestaande geldige `BPM`-attributen worden niet automatisch vervangen in de normale Fetch of onderhoud [6].
- **Identiteitswijziging tijdens Review:** Als Artiest/Titel/Jaar/Album handmatig wordt gecorrigeerd, wordt een eerder via AcousticBrainz gevonden BPM-voorstel verwijderd zodat geen verouderde Recording-match wordt geschreven. rekordbox- en bestandstag-BPM blijven aan het bestand gekoppeld.
- **Geen audioanalyse in het BPM-modul:** BPM wordt alleen uit bestaande rekordbox-data, bestandstags of externe metadata gelezen; audiobestanden worden voor BPM niet geanalyseerd of gewijzigd.
- **Bestaande databasebeveiliging:** Apply, dubbele status en BPM-onderhoud gebruiken integriteitscontroles; veiligheidskritisch onderhoud maakt back-ups en controleert daarna opnieuw. `RESTAURIERT` blijft bij BPM-onderhoud ongewijzigd.
- **Rate-limit-versterking:** AcousticBrainz gebruikt minimaal 1,05 seconde tussen requests en houdt rekening met dynamische `X-RateLimit-Remaining`-/`X-RateLimit-Reset-In`-headers.
- **Track-level retry in normale Fetch:** Als een volledige track na de interne request-retries nog mislukt door netwerk/time-out, HTTP 429 of een retrybare 5xx-fout, wordt de volledige trackopzoeking automatisch maximaal drie keer opnieuw gestart (2/5/10 s). `Retry-After` en rate-limit-resetinformatie kunnen de wachttijd verlengen; niet-tijdelijke 4xx-fouten worden niet herhaald.
- **Regressietests uitgebreid:** 33 tests controleren nu ook normale Fetch → rekordbox BPM, bescherming van bestaande BPM bij Full Fetch, BPM-schrijven via Apply, het verwijderen van identiteitsafhankelijke AcousticBrainz-voorstellen, track-level retry en `Retry-After`.

### Documentatie
- **Handleidingen DE/EN/NL volledig opnieuw gestructureerd:** Veiligheidsmodel, `Data`-werkmap, hervatten/reset, `RESTAURIERT`/`FORCE_APPLY`, alle Fetch-velden, Review, Apply, onderhoud, bestandstagger, dubbelen, BPM, rekordbox-workflow, diagnose en CLI zijn nu als één samenhangend referentiehandboek beschreven.
- **README DE/EN/NL bijgewerkt:** BPM in normale Fetch, onderhoudsfallback en de actuele licentiebestandsnaam `LICENSE` zijn gedocumenteerd.

### Gewijzigd
- **Versie:** Applicatie en Windows-versieresource blijven `0.64.00 BETA` / `0.64.0.0 Beta`; deze aanvullingen horen bij de definitieve 0.64-releasebasis.

## [0.63.00 Beta] - 2026-09-10
### Toegevoegd
- **Controle op dubbelen opnieuw ontworpen:** Onderhoudsoptie `[5]` zoekt actuele dubbele kandidaten op basis van gelijke genormaliseerde Artiest/Titel-combinaties, opgeslagen bestandspaden of geldige ISRCs en markeert de betrokken muziekitems met `DOPPELUNG=JA`.
- **Automatische statusopschoning:** Als een eerder gemarkeerde kandidaat na handmatige controle in mAirList als enig item overblijft, verwijdert de volgende scan automatisch het `DOPPELUNG`-attribuut. Een Smart Folder of filter met `DOPPELUNG = JA` blijft daardoor vanzelf actueel.
- **Regressietest voor de volledige levenscyclus:** De test controleert markeren, bewust verschillende looptijden, het handmatig verwijderen van één dubbel item en het automatisch opruimen van de resterende markering.

### Veiligheid
- **Geen automatische verwijdering:** De functie beslist nooit zelf welk item verwijderd moet worden. Ze schrijft uitsluitend controlemarkeringen; de uiteindelijke beslissing blijft volledig bij de gebruiker in de mAirList DB-app.
- **Transactie, back-up en integriteitscontrole:** Kandidaten worden eerst volledig in het geheugen berekend. Alleen echte statuswijzigingen veroorzaken een SQLite-integriteitscontrole, back-up en atomaire transactie, gevolgd door een tweede integriteitscontrole.
- **Negeerlijsten worden gerespecteerd:** Opgeslagen mapuitzonderingen voor de geselecteerde database gelden ook voor de controle op dubbelen.

### Gewijzigd
- **Officiële downloadlink:** README-bestanden en de update-melding verwijzen nu naar de officiële openbare Google Drive-map voor kant-en-klare standalone-releases.
- **Duidelijkere integriteitsbeveiliging:** Als de controle al vóór het schrijven mislukt, vermeldt de Restorer nu uitdrukkelijk dat er nog niets is gewijzigd. Meldingen die alleen indexen betreffen worden als een typisch SQLite-indexprobleem toegelicht; automatische databasereparatie gebeurt bewust niet.
- **Versie:** Applicatie en Windows-versiebron bijgewerkt naar `0.63.00 BETA` / `0.63.0.0 Beta`.

## [0.62.05 Beta] - 2026-09-09
### Toegevoegd
- **Fouttolerante API-ophaling:** MusicBrainz- en Discogs-aanvragen worden bij tijdelijke netwerkfouten, HTTP 429 en veelvoorkomende 5xx-fouten automatisch maximaal drie keer opnieuw geprobeerd. Tracks die definitief mislukken krijgen status `FEHLER`, blijven openstaan en worden bij een latere fetch opnieuw geprobeerd.
- **Afzonderlijke werkstand per database:** CSV-cache en logs bevatten nu een korte hash van het volledige databasepad. Gelijknamige `.mldb`-bestanden in verschillende mappen kunnen daardoor nooit dezelfde werkstand gebruiken. Oude 0.62.04-caches worden bij de eerste selectie automatisch gemigreerd.
- **Atomaire CSV-opslag:** Sessiebestanden worden eerst volledig naar een tijdelijk bestand geschreven en daarna atomair vervangen.
- **SQLite-integriteitscontrole & overzicht vóór opslaan:** Geplande veldwijzigingen worden vóór het schrijven geteld en getoond. De database wordt vóór en na Opslaan gecontroleerd met `PRAGMA integrity_check`.
- **Regressietests:** Een nieuw `tests/`-pakket controleert de veiligheidskritische functies automatisch met Python `unittest`.
- **Automatische GitHub-tests:** Een GitHub Actions-workflow voert bij pushes en pull requests op Windows automatisch `compileall` en de regressietests uit. Een `requirements.txt` documenteert de Python-afhankelijkheden.

### Gewijzigd
- **GitHub-veiligheid:** Een `.gitignore` voorkomt dat de lokale map `Data/`, databases, back-ups en buildbestanden per ongeluk in de openbare repository terechtkomen.
- **Gebruiksvriendelijkere databasekeuze:** Ongeldige of incompatibele databasebestanden sluiten het interactieve programma niet meer af; de gebruiker kan direct een ander bestand kiezen.
- **Hoofdmenu duidelijker voor beginners:** De opties beschrijven nu eerst in gewone taal wat er gebeurt. Optie 5 vermeldt expliciet dat de automatische acceptatie veilige Jaar/Genre-matches betreft.
- **Lyrics/songtekst uit de werkcache verwijderd:** Deze attributen blijven in mAirList onaangetast, maar worden niet meer naar tijdelijke CSV-bestanden gekopieerd.
- **Conflictveilige datamigratie:** Bestaande bestanden in `Data` worden niet meer verwijderd; conflicterende kopieën blijven met een tijdstempel bewaard.


## [0.62.04 Beta] - 2026-09-09
### Opgelost
- **Full-Fetch / Opslaan-conflict:** Full-Fetch-items worden nu intern gemarkeerd met `FORCE_APPLY`. Daardoor mogen gecontroleerde Full-Fetch-resultaten worden opgeslagen, ook wanneer de `.mldb` nog `RESTAURIERT: JA` bevat. De normale overschrijfbeveiliging van Smart-Fetch blijft behouden.
- **Volledige cache-reset:** Wanneer `RESTAURIERT` handmatig in mAirList wordt verwijderd, vernieuwt de Restorer nu alle oorspronkelijke velden vanuit de `.mldb` (o.a. Artiest, Titel, Jaar, Genre, Album, Label, Taal en Type) in plaats van alleen Artiest/Titel.
- **Discogs Master-/Release-ID:** Zoekresultaten van het type `master` worden nu via `main_release` naar een echte release-ID vertaald voordat releasegegevens of labelcodes worden opgevraagd.
- **Thread-safe API-throttling:** De MusicBrainz- en Discogs-rate-limits zijn nu beschermd tegen gelijktijdige toegang.

### Geoptimaliseerd
- **Minder MusicBrainz-aanvragen:** Suggesties voor artiest- en titelspelling worden per track slechts één keer opgehaald en daarna hergebruikt.
- **Betrouwbaarheidslogica:** Jaarbetrouwbaarheid houdt nu rekening met overeenstemming tussen MusicBrainz en Discogs. Genrebetrouwbaarheid wordt apart bijgehouden zodat Auto Review niet langer de jaarbetrouwbaarheid gebruikt voor genrekeuzes.
- **Gelokaliseerde itemtypen:** Voorstellen voor `Typ` volgen nu de gedetecteerde Duitse, Engelse of Nederlandse databasetaal.
- **API-diagnose:** API-uitzonderingen en HTTP-fouten worden nu in het log geschreven in plaats van volledig stil genegeerd.

### Documentatie
- README-bestanden en handleidingen zijn bijgewerkt voor het huidige onderhoudsmenu, taaloptie [8], de werkelijke jaar-uitbijterlogica en de Full-Fetch-workflow.
- Projectcredits zijn bijgewerkt naar ChatGPT.

## [0.62.03 Beta] - 2026-09-04
### Opgelost
- **Slimme update-checker:** De ingebouwde update-checker vertaalt versienummers nu naar wiskundige waarden en vergelijkt deze correct. Dit voorkomt valse update-meldingen wanneer de lokaal gebruikte versie hoger is dan de versie in de GitHub-repository (bijv. tijdens lokale ontwikkeling).

## [0.62.02 Beta] - 2026-09-03
### Opgelost
- **Cache Sync & Geforceerde Reset:** Een kritieke fout verholpen waarbij het handmatig verwijderen van het 'RESTAURIERT: JA'-attribuut in mAirList werd genegeerd door de cache van de tool. De Fetch-fase detecteert nu discrepanties en forceert een complete nieuwe fetch voor deze bewerkte tracks.
- **Overschrijfbeveiliging (Apply):** De Apply-fase controleert nu live de `.mldb`-database voordat er geschreven wordt. Tracks die in mAirList al zijn gemarkeerd als 'RESTAURIERT: JA', worden strikt uitgesloten van het schrijfproces. Dit voorkomt dat handmatige bewerkingen in de app worden overschreven door oude CSV-cachegegevens.

### Gewijzigd
- **UI-verfijning:** De prompt voor taalselectie tijdens de Review-fase is opgeschoond. Overtollige 'j'- en 'Enter'-hints zijn verwijderd voor een overzichtelijkere terminalweergave.

## [0.62.00 Beta] - 2026-09-03
### Toegevoegd
- **Slimme back-up opschoning:** De `Apply`-fase beheert nu automatisch de databaseback-ups. Het script bewaart altijd de 5 meest recente `.backup`-bestanden en verwijdert oudere versies stilletjes om de harde schijf op de lange termijn schoon te houden.

## [0.61.00 Beta] - 2026-09-03
### Gewijzigd
- **Onderhoudsmenu opgeschoond:** Het onderhoudsmenu is gestroomlijnd. Verouderde of zeer specifieke functies (zoals het verwijderen van "Platinum Notes" en het zoeken naar duplicaten) zijn verwijderd en de overige kernfuncties zijn logisch hernummerd.
- **mAirList 8.1+ Compatibiliteit:** De genre-standaardisatie [1] is volledig herschreven. Het controleert nu dynamisch of mAirList de nieuwe native `genre`-kolom (sinds v8.1 Beta) of de oude `item_attributes`-tabellen gebruikt, zodat slimme mappen (Smart Folders) 100% correct synchroniseren.

## [0.60.00 Beta] - 2026-09-03
### Toegevoegd
- **FLAC-Tagger (Audio Metadata Injectie):** Een krachtige nieuwe onderhoudsoptie [7] toegevoegd die metadata (Artiest, Titel, Jaar, Genre, Album, Label) direct vanuit de database naar de fysieke audiobestanden (FLAC, MP3, AIFF) schrijft via de `mutagen`-bibliotheek. Dit dient als de ultieme back-up voor het geval de database ooit corrupt raakt.
- **Slimme lokale padtoewijzing:** De FLAC-Tagger bevat een intelligente 'on-the-fly' padvertaler. Als mAirList relatieve paden via opslaglocaties (Storage Locations) gebruikt, kunnen gebruikers hun lokale basismappen eenvoudig via drag & drop naar de terminal slepen. De tool zoekt en tagt de bestanden automatisch, zonder de databasepaden te wijzigen.

### Gewijzigd
- **Genre-uitbreiding:** `Pop-Rock` is toegevoegd aan de `ALLOWED_GENRES`-lijst om crossover-planning beter te ondersteunen. Synoniemen zoals "pop rock" of "pop/rock" worden nu correct toegewezen aan deze nieuwe categorie in plaats van standaard als "Rock" te worden gemarkeerd.

## [0.52.00 Beta] - 2026-09-02
### Toegevoegd
- **Duplicaatdetectie (Onderhoud):** Een nieuwe, veelgevraagde onderhoudsoptie [6] toegevoegd om tracks met identieke Artiest/Titel-combinaties te vinden. Om de database-integriteit absoluut te waarborgen, verplaatst de tool geen elementen, maar markeert ze veilig met een nieuw `DOPPELUNG`-attribuut dat op `JA` wordt gezet. Hierdoor kunnen gebruikers ze gemakkelijk filteren en beheren binnen de mAirList-GUI.
- **Discogs Master Release-logica:** API-query's naar Discogs geven nu prioriteit aan `type=master`. Hierdoor wordt expliciet het echte oorspronkelijke releasejaar ("eerste bekende release") opgehaald, in plaats van de datums van latere compilatie-heruitgaven.
- **Tracktaal ophalen:** De MusicBrainz-API-integratie is voorbereid om het veld met de tracktaal op te halen (indien verstrekt door de database) om het taalattribuut tijdens de review-fase automatisch in te vullen.

### Gewijzigd
- **Google Drive Update Routing:** De ingebouwde update-checker levert nu direct de Google Drive-link om het gecompileerde, kant-en-klare `.exe` ZIP-pakket te downloaden, waarbij de ruwe GitHub-coderepository wordt omzeild.
- **Geavanceerde Workspace Cleanup:** Het bestand `config.json` wordt nu automatisch gemigreerd naar en geladen vanuit de map `Data`, zodat de hoofdmap volledig schoon blijft (en alleen de `.exe` bevat).
- **Menu Ergonomie:** De prompttekst wanneer het fetch-proces na 50 tracks pauzeert, is verduidelijkt om de gebruiker beter te begeleiden. Menu-opties [8] en [9] zijn omgewisseld voor een meer intuïtieve lay-out.

### Opgelost
- **Fetch Restoration Sync Bug:** Een logicafout verholpen waarbij de tool oude `_vorschlaege.csv`-voortgang prioriteerde boven de daadwerkelijke status van de `.mldb`-database. Tracks die in de database al zijn gemarkeerd als `RESTAURIERT: JA`, worden nu strikt genegeerd, zelfs als ze als in behandeling verschijnen in een oud sessiebestand.
- **Dummy Element Filtering:** De tool negeert nu expliciet mAirList-systeemitems zoals `Dummy`, `Stream`, `Command`, `Silence` en `Other` tijdens de initiële fetch-fase om nutteloze API-query's te voorkomen.
- **Case-Insensitive SQL Mapping:** Een crash in het onderhoudsmenu (`no such column: ID`) verholpen door een robuuste, case-insensitieve `PRAGMA`-tabelscanner te implementeren. De tool identificeert nu dynamisch de juiste primaire sleutels (`idx`/`ID` en `Item`/`ItemIdx`) in alle verschillende mAirList-databaseversies.

## [0.51.01 Beta] - 2026-09-02
### Gewijzigd
- **Migratie naar zelfstandig uitvoerbaar bestand (de "All-in-One"-update):** De tool is volledig herbouwd van een hybride Batch/Python-architectuur naar een volledig zelfstandige Python-applicatie, ontworpen om als één gecompileerd `.exe`-bestand te worden verspreid. Gebruikers hoeven Python of afhankelijkheden niet langer handmatig te installeren. `Restore.bat` is verouderd verklaard en verwijderd.
- **Geïntegreerd interactief menu:** Het oude Windows-batchstartmenu is volledig vervangen door een native, meertalige, door `rich` aangedreven terminalinterface die rechtstreeks in `main.py` is geïntegreerd. Dit zorgt voor een veel schonere en robuustere gebruikerservaring.

### Toegevoegd
- **Permanente taalkeuze:** De voorkeurstaal van de gebruiker wordt nu automatisch opgeslagen in `config.json`. Bij volgende starts wordt de eerste taalkeuze overgeslagen. Een nieuwe optie `[9]` is aan het hoofdmenu toegevoegd om de taal op elk moment te wijzigen.
- **Uitvoerings-"airbag" (crashpreventie):** Er is een globale foutafhandeling toegevoegd bij het starten van de applicatie. Als de tool bij het starten via dubbelklikken een kritieke fout tegenkomt, wordt het terminalvenster niet langer stilletjes gesloten. In plaats daarvan wordt de volledige fout-traceback weergegeven en wordt op invoer van de gebruiker gewacht.
- **Dynamische detectie van de werkmap:** De tool detecteert nu intelligent zijn uitvoeringsomgeving (bevroren `.exe` versus standaard `.py`-script) en stelt expliciet de juiste werkmap in. Dit voorkomt `PermissionError` (bijv. `[WinError 5]`) bij het aanmaken van de map `Data` wanneer de tool vanuit een systeemcontext wordt gestart.

## [0.50.28 Beta] - 2026-09-02
### Toegevoegd
- **Opschoning van de werkruimte (Data-map):** Het script maakt nu automatisch een submap `Data` aan en verplaatst alle sessiebestanden (`.csv` en `.log`) tijdens het uitvoeren naadloos hiernaartoe. Zo blijft de hoofdmap netjes en overzichtelijk, zonder eerder geboekte voortgang te verliezen.
- **Vertaling van itemtypen:** Er is een uitgebreide woordenlijst toegevoegd om interne mAirList-itemtypen te vertalen naar leesbare benamingen (bijv. "Music" -> "Muziek", "Voice" -> "Presentatie). Dit wordt automatisch toegepast tijdens de fetch-fase op lege velden en is ook beschikbaar als een nieuwe speciale bulktaak in het onderhoudsmenu.

### Gewijzigd
- **Verbeterde gebruikersbegeleiding:** Succesmeldingen aan het einde van de Fetch- en Review-fases verwijzen nu expliciet naar de juiste numerieke optie in het menu (bijv. "Optie [7] (Apply)"), in plaats van ruwe Python CLI-commando's, om verwarring bij gebruikers te voorkomen.

### Opgelost
- **Fout in batchmenu-routering:** Een syntaxisprobleem in `Restore.bat` waarbij ampersands (`&`) in menubeschrijvingen ervoor zorgden dat de Windows-opdrachtprompt opdrachten verkeerd interpreteerde, is opgelost. Hierdoor werken de opties "Overnight" en "Full Fetch" weer volledig correct.

## [0.5.2 Beta] - 2026-08-30
### Toegevoegd
- **Nederlandse taalondersteuning:** De tool is nu volledig drietalig! Er is een complete Nederlandse lokalisatie toegevoegd voor de console-interface, reviewprompts en het `Restore.bat`-startmenu, ter ondersteuning van de grote D&R / mAirList-community in Nederland.

## [0.5.1 Beta] - 2026-08-30
### Gewijzigd
- **Startup-UX / updatecontrole:** De GitHub-updatecontrole is verplaatst naar een aparte uitvoeringsfase (`check_update`). Het script `Restore.bat` voert deze controle nu uit *voordat* het hoofdmenu van de database wordt geladen, zodat update-meldingen goed zichtbaar zijn en niet langer direct door de interface worden overschreven.
- **Soepele overgangen:** Als er een update beschikbaar is, pauzeert de console zodat de gebruiker de melding kan lezen. Als de tool up-to-date is, wordt gedurende 2 seconden een korte bevestiging weergegeven voordat soepel naar het hoofdmenu wordt overgegaan.

## [0.5.0 Beta] - 2026-08-29
### Toegevoegd
- **Geavanceerd live opnieuw ophalen:** De live re-fetch-logica tijdens de reviewfase reageert nu expliciet op handmatige wijzigingen in de velden 'Year' en 'Album'. Het wijzigen van deze velden activeert een zeer gerichte API-aanvraag om de exacte release op te halen, waardoor de nauwkeurigheid van voorgestelde labels, labelcodes en genres sterk verbetert.

### Gewijzigd
- **Grote architectuurrefactoring:** Het monolithische `restore.py` is opgesplitst in een schone, modulaire structuur (`main.py`, `api.py`, `db.py`, `utils.py`) om onderhoudbaarheid en leesbaarheid te verbeteren en toekomstige integraties mogelijk te maken.
- **CLI-uitvoering:** Het primaire uitvoeringscommando is gewijzigd van `py restore.py` naar `py main.py`. `Restore.bat` en de CLI-argumenten zijn dienovereenkomstig bijgewerkt.

## [0.4.22 Beta] - 2026-08-29
### Gewijzigd
- **Genreconsolidatie:** `ALLOWED_GENRES` is sterk vereenvoudigd tot 10 hoofdcategorieën (Pop, EDM, Blues, Hiphop, Rap, Rock, Classic Rock, R and B, Soul, Reggae), geoptimaliseerd voor rotatieplanning. De `GENRE_SYNONYMS`-mapping is uitgebreid om automatisch complexe API-microgenres te herkennen en onder te brengen (bijv. "Nu Metal" -> "Rock", "Deep House" -> "EDM").

## [0.4.21 Beta] - 2026-08-29
### Geoptimaliseerd
- **API-concurrentie (parallel ophalen):** `ThreadPoolExecutor` is geïmplementeerd in de fetch- en live re-fetch-fases. De MusicBrainz- en Discogs-API's worden nu gelijktijdig bevraagd, waardoor de netwerkwachttijd per track aanzienlijk wordt verminderd.
- **Bulk schrijven naar database:** De `apply`-fase is herbouwd om SQLite-transacties te bundelen. In plaats van trackattributen rij voor rij te schrijven, gebruikt het script nu `executemany()` voor bulkupdates. Dit versnelt het uiteindelijke opslaan van de database aanzienlijk en verkort de tijd dat het `.mldb`-bestand vergrendeld is.

## [0.4.20 Beta] - 2026-08-28
### Toegevoegd
- **Ergonomische review:** De reviewprompts accepteren nu een lege invoer (Enter of Return indrukken) als bevestiging om suggesties te accepteren. Dit versnelt het taggen van grote tracklijsten aanzienlijk.

## [0.4.19 Beta] - 2026-08-28
### Toegevoegd
- **Taalgeheugen:** Aangepaste talen die tijdens de reviewfase handmatig worden ingevoerd (bijv. "Frans") worden nu permanent opgeslagen in de `CUSTOM_LANGS`-array van `config.json`. Het script breidt het taalkeuzemenu dynamisch uit voor alle volgende tracks.
- **Ongedaan maken (stap terug):** De statische `for`-lus in de reviewfase is vervangen door een indexgebaseerde `while`-lus. Gebruikers kunnen nu bij elke prompt `<` of `b` (Back) invoeren om veilig terug te springen naar het vorige nummer en typefouten te corrigeren.

## [0.4.18 Beta] - 2026-08-28
### Toegevoegd
- **Taal-sneltoetsen:** Er zijn snelle numerieke sneltoetsen geïntroduceerd voor de meest voorkomende talen tijdens de handmatige reviewfase (bijv. `1` voor Engels, `2` voor Duits) om het taggen aanzienlijk te versnellen.

## [0.4.17 Beta] - 2026-08-23
### Toegevoegd
- **Dynamische logging:** Logbestanden bevatten nu dynamisch de databasenaam en een tijdstempel (bijv. `DBName_20260823_141500.log`) om overschrijven te voorkomen en foutopsporing te verbeteren.
- **Proactieve controle op databaselocks:** Het script controleert nu expliciet of het `.mldb`-bestand door mAirList is vergrendeld, direct aan het begin van de `fetch`- en `review`-fases, om lees-/schrijfconflicten te voorkomen.
- **Feedback over de negeerlijst:** Er is een prominente succesmelding toegevoegd met het exacte aantal succesvol genegeerde tracks (bijv. OAD, Jingles, News) voordat het fetch-proces begint.

### Opgelost
- **SQLite-schemafout:** Een kritieke fout waarbij het script ten onrechte de tabel `folder_items` in plaats van `item_folders` bevroeg, waardoor de negeerlijst voor mappen stilletjes niet werkte, is opgelost.
- **Preventie van stille crashes (de airbag):** De hoofd-fetchlus is voorzien van robuuste foutafhandeling. Onderbroken API-verbindingen, time-outs of ongeldige tekens in tracktags laten het volledige script niet langer crashen; fouten worden gelogd en het script gaat naadloos verder met het volgende nummer.
- **Probleem met terminalmarkering:** De standaard syntax-highlighter van de `rich`-console (`highlight=False`) is uitgeschakeld om te voorkomen dat willekeurige woorden zoals 'true' of onbewerkte getallen onjuist worden gekleurd in de terminaluitvoer.
- **Duran Duran VIP-fix:** "Duran Duran" is toegevoegd aan de `ARTIST_FIXES`-woordenlijst om te voorkomen dat de MusicBrainz-API de legendarische band uit de jaren 80 verwart met de Amerikaanse breakcore-artiest "Duran Duran Duran".
- **Batchbestand blijft geopend:** Het `exit`-commando in `Restore.bat` is vervangen door `pause`, zodat het terminalvenster na uitvoering of onverwachte crashes open blijft.
