# Changelog

All notable changes to this project will be documented in this file.

## [0.63.00 Beta] - 2026-09-09
### Added
- **Redesigned duplicate scan:** Maintenance option `[5]` finds current duplicate candidates by matching normalized Artist/Title pairs, stored file paths, or valid ISRCs and marks affected music items with `DOPPELUNG=JA`.
- **Automatic status cleanup:** If a previously marked candidate becomes a single remaining item after manual review in mAirList, the next scan automatically removes its `DOPPELUNG` attribute. A Smart Folder or filter using `DOPPELUNG = JA` therefore stays current on its own.
- **Duplicate lifecycle regression test:** The test covers marking, deliberately different durations, manual removal of one duplicate item, and automatic cleanup of the remaining flag.

### Safety
- **No automatic deletion:** The feature never decides which item should be removed. It writes review flags only; the final decision remains entirely with the user in the mAirList DB app.
- **Transaction, backup and integrity checks:** Candidates are fully calculated in memory first. Only real status changes trigger an SQLite integrity check, backup and atomic transaction, followed by a second integrity check.
- **Ignore lists are respected:** Stored folder exclusions for the selected database are also applied to duplicate detection.

### Changed
- **Official download link:** README files and the update notice now point to the official public Google Drive folder for ready-to-use standalone releases.
- **Version:** Application and Windows version resource updated to `0.63.00 BETA` / `0.63.0.0 Beta`.

## [0.62.05 Beta] - 2026-09-09
### Added
- **Resilient API fetching:** MusicBrainz and Discogs requests are retried up to three times for transient network errors, HTTP 429 and common 5xx responses. Tracks that still fail receive `FEHLER` status, remain pending and are retried on a later fetch.
- **Per-database workspace isolation:** CSV caches and logs now include a short hash of the full database path so identically named `.mldb` files in different folders can never share a workspace. Legacy 0.62.04 caches are migrated when that database is first selected.
- **Atomic CSV writes:** Session files are written completely to a temporary file and then atomically replaced, reducing the risk of half-written progress files after crashes or power loss.
- **SQLite integrity checks & Apply summary:** Planned field changes are counted before writing, and the database is checked with `PRAGMA integrity_check` both before and after Apply.
- **Regression tests:** A new `tests/` package validates safety-critical behavior with Python `unittest`.
- **Automated GitHub tests:** A GitHub Actions workflow runs `compileall` and the regression suite on Windows for pushes and pull requests. A `requirements.txt` documents the Python dependencies.

### Changed
- **GitHub safety:** A `.gitignore` prevents the local `Data/` folder, databases, backups and build artifacts from being committed to the public repository accidentally.
- **Friendlier database selection:** Invalid or incompatible database files no longer terminate the interactive program; the user can simply choose another file.
- **Beginner-friendly main menu:** Menu options now describe the actual action in plain language instead of leading with implementation terms such as Smart Fetch, Overnight or Apply. Option 5 explicitly states that automatic acceptance applies to safe Year/Genre matches.
- **Lyrics/song text excluded from workspace cache:** These attributes remain untouched in mAirList but are no longer copied into temporary CSV files.
- **Conflict-safe workspace migration:** Existing files in `Data` are no longer deleted during migration; conflicting copies are preserved with timestamped names.


## [0.62.04 Beta] - 2026-09-09
### Fixed
- **Full Fetch / Apply collision:** Full Fetch rows are now explicitly marked with `FORCE_APPLY`, allowing reviewed Full Fetch results to be written even when the `.mldb` still contains `RESTAURIERT: JA`. Normal Smart Fetch overwrite protection remains intact.
- **Complete cache reset:** When `RESTAURIERT` is manually removed in mAirList, all original fields are now refreshed from the `.mldb` (including Artist, Title, Year, Genre, Album, Label, Language, and Type) instead of refreshing only Artist/Title.
- **Discogs Master/Release IDs:** `master` search hits are now resolved through `main_release` to a real release ID before release details or label-code fallbacks are queried.
- **Thread-safe API throttling:** MusicBrainz and Discogs rate-limit state is now protected against parallel access.

### Optimized
- **Fewer MusicBrainz requests:** Artist and title spelling suggestions are fetched only once per track and then reused.
- **Confidence logic:** Year confidence now considers agreement between MusicBrainz and Discogs. Genre confidence is tracked separately so Auto Review no longer reuses year confidence for genre decisions.
- **Localized item types:** `Typ` suggestions now follow the detected German, English, or Dutch database language.
- **API diagnostics:** API exceptions and HTTP errors are now written to the log instead of being silently discarded.

### Documentation
- README files and manuals were synchronized with the current maintenance menu, language option [8], actual year-outlier logic, and Full Fetch workflow.
- Project credits were updated to ChatGPT.

## [0.62.03 Beta] - 2026-09-04
### Fixed
- **Smart Update Checker:** The internal update checker now correctly parses and compares semantic version numbers mathematically (e.g., `0.62.03` vs `0.62.02`) instead of relying on simple string inequality. This prevents false positive update alerts when running a local version that is newer than the remote GitHub repository.

## [0.62.02 Beta] - 2026-09-03
### Fixed
- **Cache Sync & Forced Reset:** Fixed a critical bug where manually removing the 'RESTAURIERT: JA' attribute in mAirList was ignored by the tool's cache. The Fetch phase now detects discrepancies and forces a complete re-fetch for these modified tracks.
- **Apply Overwrite Protection:** The Apply phase now cross-references the live `.mldb` database before writing. Tracks that are already marked as 'RESTAURIERT: JA' in mAirList are strictly excluded from the write process, preventing manual app edits from being overwritten by older CSV cache data.

### Changed
- **UI Polish:** Cleaned up the language selection prompt during the Review phase by removing redundant 'j' and 'Enter' hints for a cleaner terminal output.

## [0.62.00 Beta] - 2026-09-03
### Added
- **Smart Backup Cleanup:** The `Apply` phase now automatically manages the database backup files. It keeps the 5 most recent `.backup` files and silently deletes older ones to prevent the directory from cluttering over time.

## [0.61.00 Beta] - 2026-09-03
### Changed
- **Maintenance Menu Ergonomics:** Streamlined the Maintenance Menu by removing legacy, highly specific scripts (like "Platinum Notes" deletion and duplicate finder). The remaining essential options have been logically renumbered.
- **mAirList 8.1+ Compatibility:** The Genre standardizer [1] has been fundamentally rewritten. It now dynamically checks if mAirList uses the new native `genre` column (introduced in v8.1 Beta) or the legacy `item_attributes` tables, guaranteeing that Smart Folders sync correctly.

## [0.60.00 Beta] - 2026-09-03
### Added
- **FLAC-Tagger (Audio Metadata Injection):** Added a powerful new maintenance option [7] that writes verified metadata (Artist, Title, Year, Genre, Album, Label) directly from the database into the physical audio files (FLAC, MP3, AIFF) using the `mutagen` library. This serves as the ultimate backup if the database ever corrupts.
- **Smart Local Path Mapping:** The FLAC-Tagger includes an intelligent 'on-the-fly' path translator. If mAirList uses relative paths via Storage Locations, users can simply drag & drop their local base directories into the terminal. The tool will automatically locate and tag the files locally without modifying the database paths.

### Changed
- **Genre Expansion:** Added `Pop-Rock` to the `ALLOWED_GENRES` list to better support crossover scheduling. Synonyms like "pop rock" or "pop/rock" are now correctly mapped to this new category instead of defaulting to "Rock".

## [0.52.00 Beta] - 2026-09-02
### Added
- **Duplicate Detection (Maintenance):** Added a new, highly requested maintenance option [6] to find tracks with identical Artist/Title combinations. To ensure absolute database integrity, the tool does not move items but safely tags them with a new `DOPPELUNG` attribute set to `JA`, allowing users to easily filter and manage them within the mAirList GUI.
- **Discogs Master Release Logic:** API queries to Discogs now prioritize `type=master`. This explicitly fetches the true original release year ("erste bekannte Veröffentlichung") instead of the dates of later compilation re-releases.
- **Track Language Fetching:** Prepared the MusicBrainz API integration to retrieve the track language field (if provided by the database) to automatically populate the language attribute during the review phase.

### Changed
- **Google Drive Update Routing:** The built-in update checker now directly provides the Google Drive link to download the compiled, ready-to-use `.exe` ZIP package, bypassing the raw GitHub code repository.
- **Advanced Workspace Cleanup:** The `config.json` file is now automatically migrated to and loaded from the `Data` directory, ensuring the root folder remains completely clean (containing only the `.exe`).
- **Menu Ergonomics:** Clarified the prompt text when the fetch process pauses after 50 tracks to better guide the user. Swapped menu options [8] and [9] for a more intuitive layout.

### Fixed
- **Fetch Restoration Sync Bug:** Fixed a logic flaw where the tool prioritized old `_vorschlaege.csv` progress over the actual `.mldb` database state. Tracks already marked as `RESTAURIERT: JA` in the database are now strictly ignored, even if they appear as pending in an old session file.
- **Dummy Element Filtering:** The tool now explicitly ignores system-level mAirList items like `Dummy`, `Stream`, `Command`, `Silence`, and `Other` during the initial fetch phase to prevent useless API queries.
- **Case-Insensitive SQL Mapping:** Fixed a crash in the Maintenance menu (`no such column: ID`) by implementing a robust, case-insensitive `PRAGMA` table scanner. The tool now dynamically identifies the correct primary keys (`idx`/`ID` and `Item`/`ItemIdx`) across all different mAirList database versions.

## [0.51.01 Beta] - 2026-09-02
### Changed
- **Standalone Executable Migration (The "All-in-One" Update):** The tool has been completely refactored from a hybrid Batch/Python architecture into a fully self-contained Python application, designed to be distributed as a single compiled `.exe` file. Users no longer need to install Python or dependencies manually. `Restore.bat` has been deprecated and removed.
- **Integrated Interactive Menu:** The legacy Windows batch startup menu has been entirely replaced with a native, trilingual, `rich`-powered terminal interface directly embedded within `main.py`, offering a much cleaner and more robust user experience.

### Added
- **Persistent Language Selection:** The user's preferred interface language is now automatically saved to `config.json`. The initial language prompt is skipped on subsequent startups. A new Option `[9]` has been added to the main menu to change the language at any time.
- **Execution "Airbag" (Crash Prevention):** Implemented a global error handler at the application entry point. If the tool encounters a critical error when launched via double-click, it will no longer silently close the terminal window. Instead, it displays the full error traceback and waits for user input.
- **Dynamic Working Directory Detection:** The tool now intelligently detects its runtime environment (frozen `.exe` vs. standard `.py` script) and explicitly sets the correct working directory. This prevents `PermissionError` (e.g., `[WinError 5]`) when creating the `Data` folder if the tool is launched from a system context.

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