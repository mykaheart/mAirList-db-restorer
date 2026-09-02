# Changelog

All notable changes to this project will be documented in this file.

## [0.50.28 Beta] - 2026-09-02
### Added
- **Workspace Cleanup (Data Directory):** The script now automatically creates a `Data` subfolder and seamlessly migrates all session files (`.csv` and `.log`) into it upon execution. This keeps the root directory clean and organized without losing any prior progress.
- **Item Type Translation (Elementtypen):** Added a comprehensive dictionary to translate mAirList internal item types into readable formats (e.g., "Music" -> "Musik", "Voice" -> "Moderation"). This applies automatically during the fetch phase for empty fields and is also available as a new dedicated bulk task in the Maintenance menu.

### Changed
- **Improved User Guidance:** Success messages at the end of the Fetch and Review phases now explicitly point the user to the correct numeric option in the `Restore.bat` menu (e.g., "Option [7] (Apply)"), replacing raw Python CLI commands to prevent user confusion.

### Fixed
- **Batch Menu Routing Bug:** Fixed a syntax issue in `Restore.bat` where ampersands (`&`) in menu descriptions caused the Windows command prompt to misinterpret commands, restoring full functionality to the "Overnight" and "Full Fetch" options.

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