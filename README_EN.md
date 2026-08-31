# mAirList DB Restorer v0.50.27 Beta
**The Intelligent Metadata Repair Tool for Local mAirList Databases**

Anyone who maintains a music database knows the problem: missing release years, empty genre fields, incomplete label codes, or missing album titles. The *mAirList DB Restorer* automates this tedious manual work and gets your database attributes in perfect shape.

The tool analyzes your local mAirList SQLite database (`.mldb`), searches for the missing metadata via the **MusicBrainz** and **Discogs** APIs, and safely writes the approved values back into the database.

---

## 🛠️ Core Features

This script doesn't just search blindly; it uses several safety nets and logic systems to avoid incorrect tags and provide the perfect workflow:

*   **Smart Cleaning & VIP Lists:** Artist and title are cleaned before searching (e.g., "feat.", "ft."). Notorious spellings (like "AC/DC") are prioritized via a hardcoded VIP dictionary.
*   **Duration Matching (Maxi Detection):** The script compares the API search results with the *actual local track duration* (+/- tolerance for cue points). This allows it to accurately detect Extended Versions or rare Radio Edits.
*   **Outlier Filter (Median & Gap Logic):** Since APIs often contain incorrect user entries, the script calculates the average of all found release years and ignores absurd outliers (e.g., a release year of 1945 for a 2004 track).
*   **OAD Protection (Ignore Lists):** Virtual and physical folders named, for example, "OAD" (On Air Design) or "Jingles" can be strictly excluded from the search.
*   **Ergonomic Review Process:** All API suggestions can be reviewed, adjusted, or rejected with a single keystroke (reverting to the original value) in a fast terminal workflow before saving to the database.
*   **Mass Editing (Maintenance Mode):** A separate menu allows for deep database operations, such as standardizing hundreds of genres retroactively, correcting text casing (Title Case), or deleting old attributes ("Platinum Notes", "Lyrics").

---

## ⚠️ Important Notes & Disclaimer (Please Read!)

*   **LOCAL DATABASES:** This tool currently works **exclusively with local SQLite databases (`.mldb`)** from mAirList. (Support for network databases is planned for future updates).
*   **LANGUAGE COMPATIBILITY:** The field mapping when writing to the database is currently optimized for **German, English, and Dutch** mAirList installations. (More languages will follow upon request).
*   **NO GUARANTEE:** Neither the MusicBrainz or Discogs APIs nor the algorithms of this tool are flawless. Due to the massive amount of different spellings, remixes, and identical names, incorrect metadata can be returned. **Use at your own risk!**
*   **ALWAYS WORK ON A COPY:** Since the tool writes directly to the database without an "Undo" function, you must **NEVER** work on the active file currently open in mAirList. *Always* use a copy of your `.mldb` file for this tool!

---

## 📖 User Manual

Detailed step-by-step instructions for installation and usage can be found separately in the repository (`Manual_EN.md`).

---

## 🤖 Transparency on Development

A candid word about the code: The functional concept, workflow, and architecture of this tool originate from a human (Myka Vormeng). The actual programming and writing of the Python code were significantly executed by the Artificial Intelligence *Google Gemini*.

The focus of this project is on what the tool achieves for the mAirList community and how many hours of tedious manual labor (clicking in the Cue Editor) it can save you.

---

## 🆘 Support & Feature Requests

We handle technical support, bug reports, or requests for new features **exclusively** via the following two official channels:

1.  The **Issues feature** here on GitHub.
2.  The official release thread in the **mAirList Forum**.

*(Please refrain from sending private messages or emails regarding support requests).*