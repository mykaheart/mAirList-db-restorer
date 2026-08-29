# Changelog

All notable changes to this project will be documented in this file.

## [0.4.22 Beta] - 2026-08-29
### Changed
- **Genre Consolidation:** Massively simplified the `ALLOWED_GENRES` to 10 core categories (Pop, EDM, Blues, Hiphop, Rap, Rock, Classic Rock, R and B, Soul, Reggae) optimized for rotation scheduling. Expanded the `GENRE_SYNONYMS` mapping to automatically catch and funnel complex API micro-genres (e.g., "Nu Metal" -> "Rock", "Deep House" -> "EDM").

## [0.4.21 Beta] - 2026-08-29
### Optimized
- **API Concurrency (Parallel Fetch):** Implemented `ThreadPoolExecutor` in the fetch and live re-fetch phases. MusicBrainz and Discogs APIs are now queried simultaneously, dramatically reducing network wait times per track.
- **Database Bulk-Write:** Refactored the `apply` phase to bundle SQLite transactions. Instead of writing track attributes row by row, the script now uses `executemany()` for bulk updates, speeding up the final database saving process immensely and minimizing the duration the `.mldb` file is locked.

## [0.4.20 Beta] - 2026-08-28
### Added
- **Ergonomic Review:** The review prompts now accept an empty input (pressing Enter or Return) as an affirmative response to accept suggestions, significantly speeding up the tagging process for large track lists.

## [0.4.19 Beta] - 2026-08-28
### Added
- **Language Memory (Sprach-Gedächtnis):** Custom languages entered manually during the review phase (e.g., "Französisch") are now permanently saved to the `config.json` array `CUSTOM_LANGS`. The script dynamically expands the language selection menu for all subsequent tracks.
- **Undo Function (Step Back):** Replaced the static `for`-loop with an index-based `while`-loop in the review phase. Users can now type `<` or `b` (Back) at any prompt to safely jump back to the previous track and correct typing errors.

## [0.4.18 Beta] - 2026-08-28
### Added
- **Language Shortcuts:** Introduced quick-selection numeric shortcuts for the most common languages during the manual review phase (e.g., `1` for English, `2` for German) to significantly speed up the tagging workflow.

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
- **Language Support:** Added 'Sprache' (Language) as a supported attribute in the review and apply phases.
- **Forced Prompts:** The review process now explicitly asks for Album, Label, and Language, ensuring these fields can be filled manually even if the APIs return no suggestions.

### Fixed
- **Display Bug:** Resolved an issue where empty API results (Pandas NaN values) were displayed as the string 'nan' during the manual review.

## [0.4.5 Beta] - 2026-08-22
### Added
- **Bilingual Support:** The tool is now fully bilingual! Added complete English and German localization.
- **Batch Menu Update:** `Restore.bat` now includes a language selection screen on startup.
- **CLI Argument:** Added `--lang` argument to `restore.py` to seamlessly pass the selected language to the Python environment.

## [0.4.4 Beta] - 2026-08-22
### Added
- **Smart Year Gap-Filter:** Implemented an advanced logic to intelligently ignore extreme year outliers (e.g., 1945 vs. 2004) while preserving legitimate historical re-releases.
- **VIP Dictionary:** Added `ARTIST_FIXES` to automatically correct notorious artist naming conventions (e.g., forcing "AC/DC" or "a-ha").

### Fixed
- **Artist Split Bug:** Removed aggressive comma-splitting rules that accidentally turned bands like "AC, DC" into feature artists.

## [0.4.0 Beta] - Initial Public Release
### Added
- Core functionality: Fetch from MusicBrainz and Discogs, manual review flow, and safe application to local mAirList SQLite databases (`.mldb`).
- Rich CLI interface with progress bars and dynamic console styling.
- Local Base64-masked credential storage for Discogs API and MusicBrainz contact info.
