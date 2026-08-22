@echo off
cd /d "%~dp0"

:: --- Variable fuer die Session-Datenbank initialisieren ---
set "mldbpfad="

:: --- ANSI Farb-Codes fuer Windows aktivieren ---
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "c_reset=%ESC%[0m"
set "c_cyan=%ESC%[36m"
set "c_green=%ESC%[32m"
set "c_yellow=%ESC%[33m"
set "c_magenta=%ESC%[35m"

:: --- Version dynamisch aus der restore.py auslesen ---
for /f "tokens=3" %%a in ('findstr /C:"APP_VERSION = " restore.py') do set "APP_VERSION=%%a"
:: Anfuehrungszeichen sauber entfernen
set "APP_VERSION=%APP_VERSION:"=%"

:menu
cls
echo %c_cyan%==================================================%c_reset%
echo %c_magenta%   mAirList Datenbank-Assistent v%APP_VERSION%%c_reset%
echo.
echo %c_magenta%        (c) 2026 by Myka Vormeng %c_reset%
echo %c_magenta%             und Google Gemini %c_reset%
echo %c_cyan%==================================================%c_reset%
if "%mldbpfad%"=="" (
    echo %c_yellow% Aktive Datenbank: KEINE ^(Bitte zuerst auswaehlen!^)%c_reset%
) else (
    echo %c_green% Aktive Datenbank: %mldbpfad%%c_reset%
)
echo.
echo  [%c_cyan%0%c_reset%] Aktive Datenbank auswaehlen / wechseln
echo.
echo %c_yellow% --- SCHRITT 1: METADATEN LADEN ---%c_reset%
echo  [%c_green%1%c_reset%] Smart-Abruf - Neue Tracks laden / Abbruch fortsetzen
echo  [%c_green%2%c_reset%] Voll-Abruf  - ALLE Tracks komplett neu laden (Reset)
echo.
echo %c_yellow% --- SCHRITT 2: DATEN KONTROLLIEREN ---%c_reset%
echo  [%c_green%3%c_reset%] Kontrolle   - Alle Vorschlaege manuell pruefen
echo  [%c_green%4%c_reset%] Kontrolle   - Sichere Treffer automatisch uebernehmen (unsichere werden abgefragt)
echo.
echo %c_yellow% --- SCHRITT 3: IN MAIRLIST SPEICHERN ---%c_reset%
echo  [%c_green%5%c_reset%] Speichern   - Gepruefte Werte in .mldb-Kopie schreiben
echo.
echo  [%c_green%6%c_reset%] Beenden
echo.
set /p wahl="%c_cyan%Auswahl [0-6]: %c_reset%"

if "%wahl%"=="0" goto set_db
if "%wahl%"=="1" goto fetch
if "%wahl%"=="2" goto fetch_full
if "%wahl%"=="3" goto review
if "%wahl%"=="4" goto review_auto
if "%wahl%"=="5" goto apply
if "%wahl%"=="6" goto ende
echo %c_yellow%Ungueltige Auswahl. Bitte erneut versuchen.%c_reset%
pause
goto menu

:set_db
echo.
echo %c_cyan%Hinweis:%c_reset% Bitte den Pfad zu einer KOPIE deiner Datenbank angeben.
echo %c_yellow%(Tipp: Einfach die .mldb-Datei mit der Maus in dieses Fenster ziehen und Enter druecken)%c_reset%
set /p mldbpfad="Pfad: "
set "mldbpfad=%mldbpfad:"=%"
goto menu

:check_db
if "%mldbpfad%"=="" (
    echo.
    echo %c_yellow%Fehler: Keine Datenbank ausgewaehlt! Bitte waehle zuerst Option 0.%c_reset%
    pause
    set DB_OK=0
) else (
    set DB_OK=1
)
goto :eof

:fetch
call :check_db
if "%DB_OK%"=="0" goto menu
py restore.py fetch --db "%mldbpfad%"
pause
goto menu

:fetch_full
call :check_db
if "%DB_OK%"=="0" goto menu
echo.
echo %c_yellow%ACHTUNG: Dies ruft ALLE Tracks erneut ab, auch bereits verarbeitete.%c_reset%
set /p bestaetigung="Wirklich fortfahren? [j/N]: "
if /i not "%bestaetigung%"=="j" goto menu
py restore.py fetch --db "%mldbpfad%" --full
pause
goto menu

:review
call :check_db
if "%DB_OK%"=="0" goto menu
py restore.py review --db "%mldbpfad%"
pause
goto menu

:review_auto
call :check_db
if "%DB_OK%"=="0" goto menu
py restore.py review --auto-hoch --db "%mldbpfad%"
pause
goto menu

:apply
call :check_db
if "%DB_OK%"=="0" goto menu
echo.
echo %c_yellow%ACHTUNG: Dieser Vorgang schreibt alle geprueften Werte in die oben%c_reset%
echo %c_yellow%ausgewaehlte .mldb-Datei. Nutze hierfuer IMMER EINE KOPIE!%c_reset%
echo.
py restore.py apply --db "%mldbpfad%"
pause
goto menu

:ende
exit