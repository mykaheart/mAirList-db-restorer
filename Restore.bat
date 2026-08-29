@echo off
cd /d "%~dp0"

:: --- Variable fuer die Session-Datenbank initialisieren ---
set "mldbpfad="
set "LANG_ARG=de"

:: --- ANSI Farb-Codes fuer Windows aktivieren ---
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "c_reset=%ESC%[0m"
set "c_cyan=%ESC%[36m"
set "c_green=%ESC%[32m"
set "c_yellow=%ESC%[33m"
set "c_magenta=%ESC%[35m"

:: --- Version dynamisch aus der utils.py auslesen ---
for /f "tokens=3" %%a in ('findstr /C:"APP_VERSION = " utils.py') do set "APP_VERSION=%%a"
set "APP_VERSION=%APP_VERSION:"=%"

:lang_select
cls
echo %c_cyan%==================================================%c_reset%
echo %c_magenta%   mAirList DB Restorer v%APP_VERSION% - Language Setup%c_reset%
echo %c_cyan%==================================================%c_reset%
echo.
echo  [%c_green%1%c_reset%] Deutsch
echo  [%c_green%2%c_reset%] English
echo.
set /p lang_choice="%c_cyan%Select / Auswahl [1-2]: %c_reset%"

if "%lang_choice%"=="1" goto lang_de
if "%lang_choice%"=="2" goto lang_en
goto lang_select

:lang_de
set "LANG_ARG=de"
set "T_TITLE=mAirList Datenbank-Assistent"
set "T_DB_NONE=Aktive Datenbank: KEINE (Bitte zuerst auswaehlen!)"
set "T_DB_ACT=Aktive Datenbank:"
set "T_OPT0=Aktive Datenbank auswaehlen / wechseln"
set "T_H1=--- SCHRITT 1: METADATEN LADEN ---"
set "T_OPT1=Smart-Abruf - Neue Tracks laden / Abbruch fortsetzen"
set "T_OPT2=Voll-Abruf  - ALLE Tracks komplett neu laden (Reset)"
set "T_H2=--- SCHRITT 2: DATEN KONTROLLIEREN ---"
set "T_OPT3=Kontrolle   - Alle Vorschlaege manuell pruefen"
set "T_OPT4=Kontrolle   - Sichere Treffer automatisch uebernehmen (unsichere werden abgefragt)"
set "T_H3=--- MASSENBEARBEITUNG ---"
set "T_OPT5=Genres      - Alle DB-Genres gem. Skript standardisieren"
set "T_H4=--- SCHRITT 3: IN MAIRLIST SPEICHERN ---"
set "T_OPT6=Speichern   - Gepruefte Werte in .mldb-Kopie schreiben"
set "T_OPT7=Beenden"
set "T_PROMPT=Auswahl [0-7]:"
set "T_ERR=Ungueltige Auswahl. Bitte erneut versuchen."
set "T_HINT=Hinweis: Bitte den Pfad zu einer KOPIE deiner Datenbank angeben."
set "T_HINT2=(Tipp: Einfach die .mldb-Datei in dieses Fenster ziehen und Enter druecken)"
set "T_PATH=Pfad:"
set "T_ERR_DB=Fehler: Keine Datenbank ausgewaehlt! Bitte waehle zuerst Option 0."
set "T_WARN1=ACHTUNG: Dies ruft ALLE Tracks erneut ab, auch bereits verarbeitete."
set "T_SURE=Wirklich fortfahren? [j/N]:"
set "T_WARN2=ACHTUNG: Dieser Vorgang schreibt alle geprueften Werte in die oben"
set "T_WARN3=ausgewaehlte .mldb-Datei. Nutze hierfuer IMMER EINE KOPIE!"
set "T_WARN4=ACHTUNG: Dies ueberschreibt alle abweichenden Genres direkt in der Datenbank."
goto menu

:lang_en
set "LANG_ARG=en"
set "T_TITLE=mAirList Database Assistant"
set "T_DB_NONE=Active Database: NONE (Please select first!)"
set "T_DB_ACT=Active Database:"
set "T_OPT0=Select / change active database"
set "T_H1=--- STEP 1: FETCH METADATA ---"
set "T_OPT1=Smart Fetch - Load new tracks / resume aborted fetch"
set "T_OPT2=Full Fetch  - Re-fetch ALL tracks (Reset)"
set "T_H2=--- STEP 2: REVIEW DATA ---"
set "T_OPT3=Review      - Manually inspect all proposals"
set "T_OPT4=Review      - Auto-accept safe matches (ask for unsure ones)"
set "T_H3=--- MASS EDITING ---"
set "T_OPT5=Genres      - Standardize all DB genres according to script"
set "T_H4=--- STEP 3: SAVE TO MAIRLIST ---"
set "T_OPT6=Apply       - Write verified values to .mldb copy"
set "T_OPT7=Exit"
set "T_PROMPT=Choice [0-7]:"
set "T_ERR=Invalid choice. Please try again."
set "T_HINT=Note: Please provide the path to a COPY of your database."
set "T_HINT2=(Tip: Just drag and drop the .mldb file into this window and press Enter)"
set "T_PATH=Path:"
set "T_ERR_DB=Error: No database selected! Please choose Option 0 first."
set "T_WARN1=WARNING: This will re-fetch ALL tracks, including already processed ones."
set "T_SURE=Really continue? [y/N]:"
set "T_WARN2=WARNING: This operation writes all verified values to the"
set "T_WARN3=selected .mldb file. ALWAYS USE A COPY for this!"
set "T_WARN4=WARNING: This will overwrite all deviating genres directly in the database."
goto menu

:menu
cls
echo %c_cyan%==================================================%c_reset%
echo %c_magenta%   %T_TITLE% v%APP_VERSION%%c_reset%
echo.
echo %c_magenta%        (c) 2026 by Myka Vormeng %c_reset%
echo %c_magenta%             und Google Gemini %c_reset%
echo %c_cyan%==================================================%c_reset%

if "%mldbpfad%"=="" goto show_no_db
echo %c_green% %T_DB_ACT% %mldbpfad%%c_reset%
goto show_db_done

:show_no_db
echo %c_yellow% %T_DB_NONE%%c_reset%

:show_db_done
echo.
echo  [%c_cyan%0%c_reset%] %T_OPT0%
echo.
echo %c_yellow% %T_H1%%c_reset%
echo  [%c_green%1%c_reset%] %T_OPT1%
echo  [%c_green%2%c_reset%] %T_OPT2%
echo.
echo %c_yellow% %T_H2%%c_reset%
echo  [%c_green%3%c_reset%] %T_OPT3%
echo  [%c_green%4%c_reset%] %T_OPT4%
echo.
echo %c_yellow% %T_H3%%c_reset%
echo  [%c_green%5%c_reset%] %T_OPT5%
echo.
echo %c_yellow% %T_H4%%c_reset%
echo  [%c_green%6%c_reset%] %T_OPT6%
echo.
echo  [%c_green%7%c_reset%] %T_OPT7%
echo.
set /p wahl="%c_cyan%%T_PROMPT% %c_reset%"

if "%wahl%"=="0" goto set_db
if "%wahl%"=="1" goto fetch
if "%wahl%"=="2" goto fetch_full
if "%wahl%"=="3" goto review
if "%wahl%"=="4" goto review_auto
if "%wahl%"=="5" goto standardize
if "%wahl%"=="6" goto apply
if "%wahl%"=="7" goto ende
echo %c_yellow%%T_ERR%%c_reset%
pause
goto menu

:set_db
echo.
echo %c_cyan%%T_HINT%%c_reset%
echo %c_yellow%%T_HINT2%%c_reset%
set /p mldbpfad="%T_PATH% "
set "mldbpfad=%mldbpfad:"=%"
goto menu

:check_db
if "%mldbpfad%"=="" (
    echo.
    echo %c_yellow%%T_ERR_DB%%c_reset%
    pause
    set DB_OK=0
) else (
    set DB_OK=1
)
goto :eof

:fetch
call :check_db
if "%DB_OK%"=="0" goto menu
py main.py fetch --db "%mldbpfad%" --lang %LANG_ARG%
pause
goto menu

:fetch_full
call :check_db
if "%DB_OK%"=="0" goto menu
echo.
echo %c_yellow%%T_WARN1%%c_reset%
set /p bestaetigung="%T_SURE% "
if /i not "%bestaetigung%"=="j" if /i not "%bestaetigung%"=="y" goto menu
py main.py fetch --db "%mldbpfad%" --full --lang %LANG_ARG%
pause
goto menu

:review
call :check_db
if "%DB_OK%"=="0" goto menu
py main.py review --db "%mldbpfad%" --lang %LANG_ARG%
pause
goto menu

:review_auto
call :check_db
if "%DB_OK%"=="0" goto menu
py main.py review --auto-hoch --db "%mldbpfad%" --lang %LANG_ARG%
pause
goto menu

:standardize
call :check_db
if "%DB_OK%"=="0" goto menu
echo.
echo %c_yellow%%T_WARN4%%c_reset%
set /p bestaetigung="%T_SURE% "
if /i not "%bestaetigung%"=="j" if /i not "%bestaetigung%"=="y" goto menu
py main.py standardize --db "%mldbpfad%" --lang %LANG_ARG%
pause
goto menu

:apply
call :check_db
if "%DB_OK%"=="0" goto menu
echo.
echo %c_yellow%%T_WARN2%%c_reset%
echo %c_yellow%%T_WARN3%%c_reset%
echo.
py main.py apply --db "%mldbpfad%" --lang %LANG_ARG%
pause
goto menu

:ende
pause