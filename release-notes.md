# Release v0.4.7 Beta

Short summary
- mAirList DB Restorer v0.4.7 Beta — metadata repair tool for mAirList (Windows).
- Now fully bilingual! (Supports German & English UI/CLI via batch selection).

Included
- restore.py (source)
- Restore.bat
- Windows standalone EXE (built by GitHub Actions) inside release ZIP

Usage
- Copy your .mldb file, place it in the folder, run Restore.bat, choose your language and follow: fetch → review → apply.

Security
- config.json stores API keys base64-encoded (obfuscation only). Do NOT share config.json publicly.

Known issues
- Smart matching may still need manual checks for borderline cases.
- APIs often do not provide reliable data for 'Album', 'Label', or 'Language' (especially for compilations or DJ promos). These fields will default to empty and can be easily filled during the manual review.

Changelog
- [NEW] Bilingual support (German/English) seamlessly integrated into the batch menu and Python script.
- [NEW] Added 'Sprache' (Language) as a supported attribute in the review and database applying process.
- [UPDATE] The review process now explicitly asks for Album, Label, and Language, even if the API found no suggestions.
- [FIX] Resolved a visual bug where empty data frames from Pandas were displayed as 'nan' during the review.
- [UPDATE] Credits updated to reflect the awesome teamwork!
- See CHANGELOG.md for all historical updates.
