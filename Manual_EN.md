# 📖 Manual: mAirList DB Restorer

Welcome to the official manual for the **mAirList DB Restorer**! This tool was developed to save you hundreds of hours of tedious manual work in the cue editor by fully automatically searching for and adding missing metadata (years, genres, albums, labels) via the MusicBrainz and Discogs APIs.

Thanks to the "All-in-One" architecture, the program is ready to use immediately – without any complicated installation! To ensure everything runs smoothly, please perform the following brief setup once.

---

## 1. Preparation & Installation

The tool is a completely standalone application (`.exe`). You do not need to install Python or any code libraries. Simply download the current ZIP file, extract it to a location of your choice, and start the file **`mAirList-DB-Restorer.exe`**.

### Step 1.1: Generate Discogs API Keys
To be allowed to access the huge Discogs database, the script requires a free API key.
1. Create a free account on [discogs.com](https://www.discogs.com) (if you don't already have one) and log in.
2. Click on your profile picture in the top right and select **Settings**.
3. Go to the very bottom of the left menu to **Developers**.
4. Click on the **"Create an App"** (or Generate Token) button.
5. Enter any name for the app (e.g., "mAirList Restorer").
6. You will now receive two important cryptic character strings: The **Consumer Key** and the **Consumer Secret**.
7. Copy these two values. When starting the `.exe` for the very first time, the program will ask for them and store them locally in the `Data` folder. The values are only Base64-obfuscated there; they are not cryptographically encrypted.

---

## 2. The Golden Rule: Backups! 🛡️

The most important thing when working with databases is data security. The mAirList DB Restorer intervenes deeply in the structure and rewrites metadata fully automatically.

⚠️ **NEVER work with the active database file (`.mldb`) that mAirList has open at this moment!**
When mAirList is running, it locks the database file. If the tool now tries to simultaneously write new genres or years into this file, the database can, in the worst case, be irreparably damaged. Although the script has a built-in protection that detects locked files, it is better to be safe than sorry.

### The Safe Workflow:
1. Close mAirList or open the Windows Explorer and navigate to the folder where your `.mldb` file is located.
2. Copy the file (e.g., `Archiv.mldb`) and paste it in a safe place, like your **Desktop**.
3. Start the `Restorer.exe`.
4. When the script asks you for the path to the database in the menu, **do not painstakingly type it in**!
5. 💡 **Pro-Tip:** Simply click on the copied `.mldb` file on your desktop, hold down the mouse button, and **drag and drop the file directly into the window**. Press `Enter`. The path is now perfectly entered!
6. When you are finished with the tool and have saved all new metadata in the copy, close mAirList, replace the old file with your new, edited copy, and restart mAirList.

---

## 3. The Workflow: Restoring Metadata

At the first start, the tool asks you for your preferred language (German, English, Dutch). The script remembers this setting for the future. You can change it at any time via Option **[8]** in the main menu; Option **[9]** exits the program.
As soon as you have loaded your database copy, the interactive menu guides you through the process and displays the recommended workflow **1 → 4/5 → 7**. *Note: The script automatically creates a `Data` folder. Workspace files are saved atomically and separated by the full database path, so two identically named `.mldb` files cannot share the same cache.*

### Step 3.1: Define Folder Exceptions (Ignore-List)
Before the script begins its search during the first fetch, it asks you for folders that should be **consistently ignored** (e.g., folders for Jingles, News, Drops, or Advertising).
*   **Child's play input:** You can simply drag and drop the physical folder from the Windows Explorer in here or type the exact name of a virtual mAirList folder. Press `Enter` with an empty input when you are done with the list.
*   **Individual per database:** The script is smart and remembers this exception list individually for exactly this loaded `.mldb` file!
*   **Customizable at any time:** If you start the tool later again with the same database, it shows you the current ignore list and asks you whether you want to keep it or create a new one.

### Step 3.2: Fetch Metadata (Fetch)
In this phase, the script searches for the matching metadata for your tracks via the APIs of MusicBrainz and Discogs. Your original values remain completely untouched!

*   **[1] Search new/unprocessed tracks:** Checks only tracks that are not yet restored and pauses after each batch of 50. The workspace can be resumed at any time.
*   **[2] Search all pending tracks without pauses:** Performs the same work as option 1 but runs to the end without 50-track pauses – useful for large libraries or overnight runs.
*   **[3] Re-check every track from scratch:** Ignores the `RESTAURIERT` flag and fetches fresh suggestions for **ALL** tracks. After review, these deliberately refreshed values may overwrite already-restored rows; the normal overwrite protection remains active for options 1/2.

If MusicBrainz or Discogs is temporarily unavailable, the Restorer automatically retries the request. If it still fails, the track is **not marked as finished**; it remains pending and will be tried again in a later fetch.

> **Tip:** You can cancel the fetch process at any time with the key combination `Ctrl + C`. The script securely saves your progress up to that point, and you can continue at exactly this point the next time you start!

### Step 3.3: Review Data (Review)
Choose **[4] Review every suggestion yourself** or **[5] Review with automatic assistance**. Option 4 is fully manual. Option 5 automatically accepts only high-confidence **Year/Genre** matches; all other fields remain reviewable.

*   **Confirm:** If you like a suggestion (e.g., the year), simply press `Enter`. The tool accepts the value and jumps to the next field.
*   **Keep original (`O` key):** Next to the suggestion, you will always see your original database value in gray. Is your own value better? Simply type an `o` (for original) and press `Enter`.
*   **Custom text:** The suggestion is wrong, but so is your original value? Simply type in your desired text.
*   **Live Re-Fetch:** If you type your own text for Artist, Title, Year, or Album (e.g., to correct a typo in the artist name), the script immediately fires off a new API search in the background and adjusts Labels, Genres, and ISRC live to your correction!
*   **Oops, typo?** Type a `<` or `b` (for Back) and press `Enter` to jump back one track.

### Step 3.4: Maintenance
Under Option **[6]** you will find the maintenance tools. You can standardize genres, correct capitalization and apostrophes in Artist/Title, or use the file tagger to write verified database metadata into local FLAC, MP3, and AIFF files. Combined option **[4]** runs the genre and text-case tasks sequentially.

Maintenance option **[5] Mark duplicate candidates / refresh status** scans for current review candidates. Music items are candidates when they share the same normalized Artist/Title pair, the same stored file path, or the same valid ISRC. Different durations deliberately do not suppress the flag because alternate edits or versions should be reviewed by a human in the mAirList DB app.

Found items only receive the attribute `DOPPELUNG=JA`; **no item is ever deleted automatically**. After reviewing the candidates in mAirList, run the same function again. If a previously marked item no longer has a matching partner, the Restorer automatically removes its `DOPPELUNG` attribute. This makes the attribute especially useful for a Smart Folder or database filter using `DOPPELUNG = JA`. Before any actual change, the Restorer checks SQLite integrity, creates a backup, and synchronizes the flags in a single transaction.

### Step 3.5: Save in mAirList (Apply)
When you have checked all tracks, select **[7] Write verified changes to the database copy**. Before writing, the Restorer shows a summary of planned field changes and runs an SQLite integrity check. Only after your confirmation does it create a backup and perform the bulk write. The database integrity is checked again afterwards.

*   The script automatically sets the internal attribute `RESTAURIERT` to `JA` (YES) for each track.
*   Tracks with this flag will be automatically skipped during future runs.
*   If you notice later during live operation that a track has wrong tags after all? Simply delete the "RESTAURIERT" attribute for this track in mAirList. The next time the script runs, the tool will recognize the track as "new" and load it again.