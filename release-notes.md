# Release v0.4.5

Short summary
- mAirList DB Restorer v0.4.4 — metadata repair tool for mAirList (Windows).

Included
- restore.py (source)
- Restore.bat

Usage
- Copy your .mldb file, place it in the folder, run Restore.bat and follow: fetch → review → apply.

Security
- config.json stores API keys base64-encoded (obfuscation only). Do NOT share config.json publicly.

Known issues
- Smart matching may still need manual checks for borderline cases.

Changelog
- See CHANGELOG.md
