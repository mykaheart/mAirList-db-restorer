# mAirList DB Restorer v0.62.03 BETA
**The intelligent metadata repair tool for local mAirList databases**

*(Note: German and Dutch documentation / manuals are available in the repository!)*

### 🚀 Quick Download
For everyone who wants to get started right away without installing Python: Simply download the ready-to-use, pre-compiled `.exe` version including manuals!
👉 **[Download mAirList-DB-Restorer (ZIP) via Google Drive](https://drive.google.com/file/d/1lV2qG7nSj28BKC2W5FoPn4bgfqqsDjdM/view?usp=sharing)**

*(The remaining source code in this repository is intended for developers and enthusiasts who wish to compile the script themselves or transparently view the code).*

---

Anyone who maintains a music database knows the problem: Missing years, empty genre fields, incomplete label codes, or missing albums. The *mAirList DB Restorer* takes this tedious manual work off your hands and automatically brings your database attributes up to speed.

The tool analyzes your local mAirList SQLite database (`.mldb`), searches for missing metadata via the **MusicBrainz** and **Discogs** APIs, and safely writes your approved values back into the database.

---

## 🛠️ Core Features

This script doesn't just search blindly; it uses multiple safety nets and logic to avoid incorrect tags and offer the perfect workflow:

*   **Smart Cleaning & VIP Lists:** Artist and title are cleaned before the API search (e.g., "feat.", "ft."). Notorious spellings (like "AC/DC") are prioritized via a hardcoded VIP dictionary.
*   **Duration Matching (Maxi Detection):** The script compares the retrieved API hits with the *actual local track duration* (+/- tolerance for cue points). This accurately detects extended versions or rare radio edits.
*   **Outlier Filter (Median & Gap Logic):** Since APIs often contain erroneous user entries, the script calculates the median of all found release years and ignores absurd outliers (e.g., a release year of 1945 for a 2004 track).
*   **OAD Protection (Ignore Lists):** Virtual and physical folders named, for example, "OAD" (On Air Design) or "Jingles" can be strictly excluded from the search.
*   **Ergonomic Review Process:** All API suggestions can be reviewed, adjusted, or rejected with a single keystroke (reverting to the original value) in a fast terminal workflow before being saved to the database.
*   **Mass Editing (Maintenance Mode):** A separate menu allows for deep database interventions, such as retrospectively standardizing hundreds of genres, correcting capitalization (Title Case), or deleting old attributes ("Platinum Notes", "Lyrics").

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

## 🤖 Transparency Regarding Origin

A frank word about the code: The functional concept, workflow, and architecture of this tool were created by human hands (Myka Vormeng). The pure programming and writing of the Python code were largely done by the Artificial Intelligence *Google Gemini*. 

The focus of this project is on what the tool does for the mAirList community and how many hours of tedious manual work (clicking in the cue editor) it can save you.

---

## 🆘 Support & Feature Requests

We handle technical support, bug reports, or requests for new features **exclusively** via the following two official channels:

1.  The **Issues function** here on GitHub.
2.  The official release thread in the **mAirList Forum**.

*(Please refrain from sending private messages or emails regarding support requests).*