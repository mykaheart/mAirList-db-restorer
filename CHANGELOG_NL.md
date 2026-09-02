# Changelog

Alle belangrijke wijzigingen aan dit project worden in dit bestand gedocumenteerd.

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
