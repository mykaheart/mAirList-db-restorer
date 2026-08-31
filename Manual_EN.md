# 📖 User Manual: mAirList DB Restorer

Welcome to the official manual for the **mAirList DB Restorer**! This tool was designed to save you hundreds of hours of tedious manual work in the cue editor by automatically searching for and adding missing metadata (years, genres, albums, labels) via the MusicBrainz and Discogs APIs.

To ensure everything runs smoothly, please complete the following brief setup once.

---

## 1. Preparation & Installation

Since this tool is a Python script, your computer requires the appropriate environment to run it. The setup only takes about 5 minutes.

### Step 1.1: Install Python
1. Download the latest version of **Python** for Windows: [python.org/downloads](https://www.python.org/downloads/)
2. Run the downloaded `.exe` file.
3. ⚠️ **EXTREMELY IMPORTANT:** Before clicking "Install Now", make sure to check the box at the bottom that says **"Add Python to PATH"**! If this box is unchecked, the script will fail to start later.
4. Click "Install Now" and wait for the installation to finish.

### Step 1.2: Install Required Libraries
The script relies on external libraries (e.g., for the colorful terminal menu or CSV export). These must be installed once.
1. Press `Windows Key + R` on your keyboard.
2. Type `cmd` into the small window and press `Enter`. (The black Windows Command Prompt will open).
3. Copy the following command, paste it into the black window, and press `Enter`:
   `pip install pandas requests rich`
4. Windows will now download the required packages. Once finished, you can close the window.

### Step 1.3: Generate Discogs API Keys
To access the massive Discogs database, the script requires a (free) API key.
1. Create a free account on [discogs.com](https://www.discogs.com) (if you don't have one) and log in.
2. Click on your profile picture in the top right corner and select **Settings**.
3. In the left menu, go all the way down to **Developers**.
4. Click the **"Create an App"** button (or Generate Token).
5. Enter any name for the app (e.g., "mAirList Restorer").
6. You will receive two important cryptographic strings: The **Consumer Key** and the **Consumer Secret**.
7. Copy both values. The very first time you run `Restore.bat`, the script will ask for them and save them securely and masked.

---

## 2. The Golden Rule: Backups! 🛡️

The most important aspect of working with databases is data security. The mAirList DB Restorer dives deep into the structure and modifies metadata fully automatically.

⚠️ **NEVER work with the active database file (`.mldb`) that mAirList currently has open!**

When mAirList is running, it locks the database file. If the Python script attempts to write new genres or release years to this file at the same time, the database can be irreparably corrupted in the worst-case scenario.

### The Secure Workflow:
1. Close mAirList or open Windows Explorer and navigate to the folder where your `.mldb` file is located.
2. Copy the file (e.g., `Archive.mldb`) and paste it in a safe place, such as your **Desktop**.
3. Start `Restore.bat`.
4. When the script asks for the path to the database, **do not type it out manually**!
5. 💡 **Pro Tip:** Simply click and hold the copied `.mldb` file on your desktop, and **drag & drop it directly into the black console window**. Press `Enter`. The path is now perfectly configured.
6. Once you are finished with the tool and all new metadata is saved in the copy, close mAirList, replace the old file with your new, edited copy, and relaunch mAirList.

---

## 3. The Workflow: Restoring Metadata

Once you have launched `Restore.bat` and selected your database copy, the main menu will guide you logically through the entire process.

### Step 3.1: Define Folder Exceptions (Ignore List)
Before the script begins searching during the initial fetch, it asks you for folders that should be **consistently ignored** (e.g., folders for jingles, news, drops, or commercials).
*   **Child’s play input:** You can simply drag and drop the physical folder from Windows Explorer into the window or type the exact name of a virtual mAirList folder. Press `Enter` on an empty line when you are finished with the list.
*   **Individual per database:** The script is smart and saves this exception list individually for precisely that loaded `.mldb` file!
*   **Customizable at any time:** If you launch the tool later with the same database, it will display the current ignore list and ask whether you want to keep it or recreate it.

### Step 3.2: Fetch Metadata (Fetch)
In this phase, the script uses the MusicBrainz and Discogs APIs to search for matching metadata for your tracks. Your original values remain completely untouched! You have three options:

*   **[1] Smart Fetch (Standard):** The tool checks only tracks that have *not* been restored yet. To prevent overwhelming you with a massive list, the script automatically pauses after loading 50 tracks. You can then jump straight to the review or load the next 50.
*   **[2] Smart Fetch (Overnight):** Perfect for huge databases. The script loads all new tracks in one go without pauses. Ideal for letting your PC run overnight.
*   **[3] Full Fetch (Reset & Overnight):** The script ignores the "RESTAURIERT" flag and completely re-fetches data for **ALL** tracks in the database.

> **Tip:** You can abort the fetch process at any time by pressing `Ctrl + C`. The script safely saves your current progress, allowing you to resume exactly where you left off the next time you start it!

### Step 3.3: Review Data (Review)
Here, the tool presents you with each track individually and proposes the metadata found on the internet.

*   **Confirm:** If you like a suggestion (e.g., the year), simply press `Enter`. The tool adopts the value and moves to the next field.
*   **Keep Original (`O` Key):** Next to the suggestion, you will always see your original database value displayed in gray. Is your own value better? Simply type `o` (for Original) and press `Enter`.
*   **Custom Text:** The suggestion is wrong, but your original value is too? Just type your desired text.
*   **Live Re-Fetch:** If you type a custom correction for Artist, Title, Year, or Album (e.g., correcting a typo in the artist's name), the script instantly triggers a new API search in the background and dynamically updates labels, genres, and ISRCs to match your correction!
*   **Oops, typo?** Type `<` or `b` (for Back) and press `Enter` to jump back one track.

### Step 3.4: Save to mAirList (Apply)
Once you have reviewed all tracks, select option **[7] Apply** in the main menu. Only then does the script open your database copy and write the new, clean metadata into it.

*   The script automatically sets the internal attribute `RESTAURIERT` to `JA` for each processed track.
*   Tracks with this flag will be automatically skipped during future runs.
*   Did you notice during live broadcasting later that a track still has incorrect tags? Simply delete the "RESTAURIERT" attribute for that track in mAirList. On the next script run, the tool will recognize the track as "new" and fetch it again.

---

## 4. The Maintenance Menu (Mass Editing)

Via option **[6] Maintenance** in the main menu, you access a powerful special utility for deep database operations.

⚠️ **WARNING:** All functions in this menu write **directly** to the database. There is no preceding review step and no "Undo"!

*   **[1] Standardize Genres:** Scans the entire database and aligns messy genres (e.g., "Deep House" or "Trance") to a clean core category (e.g., "EDM").
*   **[2] Fix Case & Apostrophes:** Repairs incorrect quotation marks (´, `, ‘ become ') in artist and title names. Additionally, "Title Case" is applied (every word starts with a capital letter). Exceptions like "AC/DC" or "a-ha" are protected by a VIP list.
*   **[3] Delete 'Platinum Notes' & 'Lyrics':** DJ software often clutters mAirList with invisible attributes like lengthy lyrics. This option deletes this data completely and noticeably shrinks your database file size.

---

## 5. FAQ & Troubleshooting

**Why is the tool not jumping to the next track during the review?**
The tool is waiting for input. For empty fields, simply press `Enter` to move to the next step.

**Why is the script not finding my jingle packages?**
That is intentional! The script features a built-in OAD protection (On Air Design). It automatically ignores all tracks located in folders present on your ignore list.

**The script is showing colorful error messages (timeouts) during fetching!**
Don't panic, the "airbag" has deployed. If the Discogs or MusicBrainz servers fail to respond temporarily (timeout), the script will not crash. It logs the error, skips that single track, and proceeds seamlessly with the next one.