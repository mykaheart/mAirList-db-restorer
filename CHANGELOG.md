# Changelog

All notable changes to this project will be documented in this file.

## [0.50.27 Beta] - 2026-08-31
### Added
- **Chunking & Overnight Mode:** The fetch phase now automatically pauses every 50 tracks to encourage manageable review blocks. Added a `--no-breaks` option (Overnight Mode) to bypass these pauses for unattended mass-fetching.
- **Trilingual Attribute Mapping:** The tool now dynamically scans the mAirList `item_attributes` table upon startup to detect the database language (English, German, or Dutch). It automatically maps internal fields (like "Year" or "Language") to the correct local database terminology during the save phase.

## [0.50.26 Beta] - 2026-08-31
### Added
- **Duration-Based Version Detection:** The MusicBrainz API fetch now cross-references the local track duration (with a +/- 18 seconds tolerance for cue points) to accurately identify and tag specific release variants, such as Extended Versions, Radio Edits, or Maxi Mixes.

## [0.50.25 Beta] - 2026-08-31
### Added
- **Original Value Preservation ('O' Key):** The interactive review now displays the original database value in gray text next to the API suggestion. Users can quickly press `o` to reject the suggestion and safely retain their original local data.

## [0.50.24 Beta] - 2026-08-31
### Added
- **Interactive Maintenance Menu:** Replaced the basic standardize phase with a robust, dedicated maintenance menu featuring severe warnings for direct, non-undoable database operations.
- **Smart Casing & Apostrophe Fix:** Added a mass-edit function to automatically correct title casing (while respecting the `ARTIST_FIXES` dictionary) and standardize various apostrophe characters (`´`, `` ` ``, `‘`) to a clean standard `'`.
- **Database Cleanup:** Added a dedicated purge function to strip bloated, unneeded attributes like 'Platinum Notes' and 'Lyrics', effectively shrinking the database size.

## [0.50.23 Beta] - 2026-08-31
### Changed
- **Version Scheme Update:** Transitioned to a new, standardized two-digit versioning format (`0.xx.xx`).
### Added
- **Schema Compatibility Check:** The script now queries the `schemaversion` directly from the mAirList `config` table on startup. Execution is blocked if the schema is unsupported, protecting future mAirList updates from accidental structural corruption.

## [0.5.2 Beta] - 2026-08-30
### Added
- **Dutch Language Support:** The tool is now fully trilingual! Added complete Dutch (Nederlands) localization for the console interface, review prompts, and the `Restore.bat` startup menu to support the large community of D&R / mAirList users in the Netherlands.

## [0.5.1 Beta] - 2026-08-30
### Changed
- **Startup UX / Update Check:** Extracted the GitHub update check into a dedicated execution phase (`check_update`). The `Restore.bat` script now triggers this check *before* loading the main database menu, ensuring that update notifications are highly visible and no longer instantly overwritten by the UI.
- **Graceful Transitions:** If an update is available, the console now pauses for the user to read the alert. If the tool is up to date, it displays a brief confirmation (2 seconds) before smoothly transitioning into the main menu.

## [0.5.0 Beta] - 2026-08-29
### Added
- **Advanced Live Re-Fetch:** The live re-fetch logic during the review phase now explicitly reacts to manual changes in the 'Year' and 'Album' fields. Modifying these fields triggers a highly targeted API request to fetch the exact release, drastically improving the accuracy of suggested Labels, Label Codes, and Genres.

### Changed
- **Massive Architecture Refactoring:** Split the monolithic `restore.py` into a clean, modular structure (`main.py`, `api.py`, `db.py`, `utils.py`) to improve maintainability, readability, and pave the way for future integrations.
- **CLI Execution:** The primary execution command has changed from `py restore.py` to `py main.py`. `Restore.bat` and CLI arguments have been updated accordingly.

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
