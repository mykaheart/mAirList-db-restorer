# Changelog

All notable changes to this project will be documented in this file.

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
