# mAirList DB Restorer v0.66.00 BETA
**The intelligent metadata repair tool for local mAirList databases**

*(Note: German and Dutch documentation / manuals are available in the repository!)*

### 🚀 Quick Download
For everyone who wants to get started right away without installing Python: Simply download the ready-to-use, pre-compiled `.exe` version including manuals!
👉 **[Download mAirList-DB-Restorer (ZIP) via Google Drive](https://drive.google.com/drive/folders/18SmIOBFbSM5apwS6FA3F72-syLvBAftj?usp=drive_link)**

*(The remaining source code in this repository is intended for developers and enthusiasts who wish to compile the script themselves or transparently view the code).*

---

Anyone who maintains a music database knows the problem: Missing years, empty genre fields, incomplete label codes, or missing albums. The *mAirList DB Restorer* takes this tedious manual work off your hands and automatically brings your database attributes up to speed.

The tool analyzes your local mAirList SQLite database (`.mldb`), searches for missing metadata via the **MusicBrainz** and **Discogs** APIs, and safely writes your approved values back into the database.

---

## 🛠️ Core Features

This script doesn't just search blindly; it uses multiple safety nets and logic to avoid incorrect tags and offer the perfect workflow:

*   **Smart Cleaning & VIP Lists:** Artist and title are cleaned before the API search (e.g., "feat.", "ft."). Notorious spellings (like "AC/DC") are prioritized via a hardcoded VIP dictionary.
*   **Duration Matching (Maxi Detection):** The script compares the retrieved API hits with the *actual local track duration* (+/- tolerance for cue points). This accurately detects extended versions or rare radio edits.
*   **Outlier Filter (Gap Logic):** Retrieved release years are sorted and checked for implausible single outliers. If the oldest year is more than eight years earlier than the next result and occurs only once, it is discarded. This catches typical bad entries in community-maintained databases.
*   **OAD Protection (Ignore Lists):** Virtual and physical folders named, for example, "OAD" (On Air Design) or "Jingles" can be strictly excluded from the search.
*   **Ergonomic Review Process:** All API suggestions can be reviewed, adjusted, or rejected with a single keystroke (reverting to the original value) in a fast terminal workflow before being saved to the database. Custom genres are remembered like custom languages in `config.json`; genre shortcuts start with `1=Rock`, `2=Pop`.
*   **File tagger & metadata disaster backup:** Maintenance [3] writes portable tags (including Genre, Language, BPM and ISRC) to FLAC/Ogg/MP3/AIFF. Optionally it also backs up mAirList cues, Peak/True Peak/Loudness and normalization: `TXXX:mAirList` inside MP3/AIFF, matching `.mmd` sidecars for FLAC/Ogg.
*   **Hardening & Resume Safety:** Individual API requests are retried automatically; transient network/429/5xx failures additionally restart the complete track lookup up to three times with 2/5/10-second backoff. Only then does the track remain pending. Session CSV files are written atomically and separated per database path so workspaces cannot be corrupted or mixed between identically named databases.
*   **Safer Apply:** Before final writing, the Restorer shows a change summary, checks SQLite integrity, creates a backup, and checks the database again after writing.
*   **Duplicate Scan:** Maintenance can mark current duplicate candidates based on matching Artist/Title pairs, file paths, or valid ISRCs with `DOPPELUNG=JA`. A later scan automatically removes resolved flags; the Restorer never deletes items automatically.
*   **Speed groups from BPM:** Maintenance [7] fills only missing mAirList standard `Geschwindigkeit` attributes: up to 100 BPM = `Langsam`, 101–129 = `Medium`, 130+ = `Schnell`. Existing classifications are always preserved.
*   **Startup & source-folder convenience:** The last used database is remembered in `Data/config.json` and offered again on the next start. Local source/base folders are stored per database and automatically reused by the tagger and BPM maintenance.
*   **BPM restoration in normal Fetch + maintenance:** Since 0.64, the BPM chain also runs as part of normal Fetch. The primary source is an optional rekordbox XML export remembered per database: `AverageBpm` is matched only by exact file path. Audio-file BPM tags are next, with MusicBrainz + AcousticBrainz as the final fallback. Existing valid BPM is protected even during Full Fetch. Maintenance option [6] remains available for fast BPM-only follow-up with a review CSV, cause-specific diagnostics and half/double-time conflict reporting.

---

## ⚠️ Important Notes & Disclaimer (Please read!)

*   **LOCAL DATABASES:** This tool currently works **exclusively with local SQLite databases (`.mldb`)** from mAirList. (Support for network databases is planned for future updates).
*   **LANGUAGE COMPATIBILITY:** Field mapping when writing to the database is currently optimized for **German, English, and Dutch** mAirList installations. (More languages will follow upon request).
*   **NO GUARANTEE:** Neither the MusicBrainz or Discogs APIs, nor the algorithms of this tool, are infallible. Due to the gigantic amount of different spellings, remixes, and name similarities, incorrect metadata may be provided. **Use at your own risk!**
*   **ALWAYS WORK WITH A COPY:** Because the tool writes directly to the database without an "Undo" function, you must **NEVER** work on the active file currently opened by mAirList in the background. *Always* use a copy of your `.mldb` file for the tool!

---

## 📖 User Manual

Detailed step-by-step instructions for installation and use can be found separately in the repository (`Manual_EN.md` or in the downloaded ZIP archive).

---

## 🧪 Development & Tests

A `requirements.txt` is included for developers. The safety-critical regression suite needs no additional test framework and can be run with:

```bash
python -m unittest discover -s tests -v
```

On pushes and pull requests, GitHub Actions automatically runs a compile check and the regression tests on Windows.

---

## 📜 License

The mAirList DB Restorer is released as **source-available freeware**. The source code may be reviewed and modified for personal or internal use. Redistribution, re-uploading, mirroring, selling, or publishing modified or unmodified copies is not permitted without prior written permission. Official downloads may be provided through any distribution channel explicitly designated by the copyright holder. See `LICENSE` for details.

## 🤖 Transparency Regarding Origin

A frank word about the code: The functional concept, workflow, and architecture of this tool were created by human hands (Myka Vormeng). The pure programming and writing of the Python code were largely done by the Artificial Intelligence *ChatGPT*. 

The focus of this project is on what the tool does for the mAirList community and how many hours of tedious manual work (clicking in the cue editor) it can save you.

---

## 🆘 Support & Feature Requests

We handle technical support, bug reports, or requests for new features **exclusively** via the following two official channels:

1.  The **Issues function** here on GitHub.
2.  The official release thread in the **mAirList Forum**.

*(Please refrain from sending private messages or emails regarding support requests).*