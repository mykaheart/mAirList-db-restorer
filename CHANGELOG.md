# Changelog

All notable changes to this project will be documented in this file.

## [0.4.17 Beta] - 2026-08-23
### Added
- **Dynamic Logging:** Log files now dynamically include the database name and a timestamp (e.g., `DBName_20260823_141500.log`) to prevent overwriting and improve debugging.
- **Proactive Database Lock Check:** The script now explicitly verifies if the `.mldb` file is locked by mAirList at the very beginning of the `fetch` and `review` phases, preventing read/write conflicts.
- **Ignore-List Feedback:** Added a prominent success message displaying the exact number of successfully ignored tracks (e.g., OAD, Jingles, News) before the fetch process begins.

### Fixed
- **SQLite Schema Bug:** Fixed a critical issue where the script incorrectly queried the `folder_items` table instead of `item_folders`, which caused the folder ignore-list to fail silently.
- **Silent Crash Prevention (The Airbag):** Wrapped the main fetch loop in a robust error-handling block. Interrupted API connections, timeouts, or illegal characters in track tags will no longer crash the entire script; errors are logged, and the script seamlessly proceeds to the next track.
- **Terminal Highlighting Glitch:** Disabled the default `rich` console syntax highlighter (`highlight=False`) to prevent random words like 'true' or raw numbers from being incorrectly colored in the terminal output.
- **Duran Duran VIP Fix:** Added "Duran Duran" to the `ARTIST_FIXES` dictionary to prevent the MusicBrainz API from confusing the legendary 80s band with the American breakcore artist "Duran Duran Duran".
- **Batch File Persistence:** Replaced the `exit` command with `pause` in `Restore.bat` to ensure the terminal window remains open after execution or unexpected crashes.

## [0.4.7 Beta] - 2026-08-23
### Added
- **Language Support:** Added 'Sprache' (Language) as a supported attribute in the review and apply phases[cite: 7].
- **Forced Prompts:** The review process now explicitly asks for Album, Label, and Language, ensuring these fields can be filled manually even if the APIs return no suggestions[cite: 7].

### Fixed
- **Display Bug:** Resolved an issue where empty API results (Pandas NaN values) were displayed as the string 'nan' during the manual review[cite: 7].

## [0.4.5 Beta] - 2026-08-22
### Added
- **Bilingual Support:** The tool is now fully bilingual! Added complete English and German localization[cite: 7].
- **Batch Menu Update:** `Restore.bat` now includes a language selection screen on startup[cite: 7].
- **CLI Argument:** Added `--lang` argument to `restore.py` to seamlessly pass the selected language to the Python environment[cite: 7].

## [0.4.4 Beta] - 2026-08-22
### Added
- **Smart Year Gap-Filter:** Implemented an advanced logic to intelligently ignore extreme year outliers (e.g., 1945 vs. 2004) while preserving legitimate historical re-releases[cite: 7].
- **VIP Dictionary:** Added `ARTIST_FIXES` to automatically correct notorious artist naming conventions (e.g., forcing "AC/DC" or "a-ha")[cite: 7].

### Fixed
- **Artist Split Bug:** Removed aggressive comma-splitting rules that accidentally turned bands like "AC, DC" into feature artists[cite: 7].

## [0.4.0 Beta] - Initial Public Release
### Added
- Core functionality: Fetch from MusicBrainz and Discogs, manual review flow, and safe application to local mAirList SQLite databases (`.mldb`)[cite: 7].
- Rich CLI interface with progress bars and dynamic console styling[cite: 7].
- Local Base64-masked credential storage for Discogs API and MusicBrainz contact info[cite: 7].
