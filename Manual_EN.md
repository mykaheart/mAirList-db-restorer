# 📖 Manual: mAirList DB Restorer[cite: 6]

Welcome to the official manual for the **mAirList DB Restorer**![cite: 6] This tool was developed to save you hundreds of hours of tedious manual work in the cue editor by fully automatically searching for and adding missing metadata (years, genres, albums, labels) via the MusicBrainz and Discogs APIs.[cite: 6]

Thanks to the "All-in-One" architecture, the program is ready to use immediately – without any complicated installation![cite: 6] To ensure everything runs smoothly, please perform the following brief setup once.[cite: 6]

---

## 1. Preparation & Installation[cite: 6]

The tool is a completely standalone application (`.exe`).[cite: 6] You do not need to install Python or any code libraries.[cite: 6] Simply download the current ZIP file, extract it to a location of your choice, and start the file **`mAirList-DB-Restorer.exe`**.[cite: 6]

### Step 1.1: Generate Discogs API Keys[cite: 6]
To be allowed to access the huge Discogs database, the script requires a free API key.[cite: 6]
1. Create a free account on [discogs.com](https://www.discogs.com) (if you don't already have one) and log in.[cite: 6]
2. Click on your profile picture in the top right and select **Settings**.[cite: 6]
3. Go to the very bottom of the left menu to **Developers**.[cite: 6]
4. Click on the **"Create an App"** (or Generate Token) button.[cite: 6]
5. Enter any name for the app (e.g., "mAirList Restorer").[cite: 6]
6. You will now receive two important cryptic character strings: The **Consumer Key** and the **Consumer Secret**.[cite: 6]
7. Copy these two values.[cite: 6] When starting the `.exe` for the very first time, the program will ask you for them and save them securely locally.[cite: 6]

---

## 2. The Golden Rule: Backups! 🛡️[cite: 6]

The most important thing when working with databases is data security.[cite: 6] The mAirList DB Restorer intervenes deeply in the structure and rewrites metadata fully automatically.[cite: 6]

⚠️ **NEVER work with the active database file (`.mldb`) that mAirList has open at this moment!**[cite: 6]
When mAirList is running, it locks the database file.[cite: 6] If the tool now tries to simultaneously write new genres or years into this file, the database can, in the worst case, be irreparably damaged.[cite: 6] Although the script has a built-in protection that detects locked files, it is better to be safe than sorry.[cite: 6]

### The Safe Workflow:[cite: 6]
1. Close mAirList or open the Windows Explorer and navigate to the folder where your `.mldb` file is located.[cite: 6]
2. Copy the file (e.g., `Archiv.mldb`) and paste it in a safe place, like your **Desktop**.[cite: 6]
3. Start the `Restorer.exe`.[cite: 6]
4. When the script asks you for the path to the database in the menu, **do not painstakingly type it in**![cite: 6]
5. 💡 **Pro-Tip:** Simply click on the copied `.mldb` file on your desktop, hold down the mouse button, and **drag and drop the file directly into the window**.[cite: 6] Press `Enter`.[cite: 6] The path is now perfectly entered![cite: 6]
6. When you are finished with the tool and have saved all new metadata in the copy, close mAirList, replace the old file with your new, edited copy, and restart mAirList.[cite: 6]

---

## 3. The Workflow: Restoring Metadata[cite: 6]

At the first start, the tool asks you for your preferred language (German, English, Dutch).[cite: 6] The script remembers this setting for the future.[cite: 6] You can change it at any time via Option **[9]** in the main menu.[cite: 6]
As soon as you have loaded your database copy, the interactive menu guides you logically through the entire process.[cite: 6] *Note: The script automatically creates a folder called `Data` in which it neatly stores all logs and intermediate saves.*[cite: 6]

### Step 3.1: Define Folder Exceptions (Ignore-List)[cite: 6]
Before the script begins its search during the first fetch, it asks you for folders that should be **consistently ignored** (e.g., folders for Jingles, News, Drops, or Advertising).[cite: 6]
*   **Child's play input:** You can simply drag and drop the physical folder from the Windows Explorer in here or type the exact name of a virtual mAirList folder.[cite: 6] Press `Enter` with an empty input when you are done with the list.[cite: 6]
*   **Individual per database:** The script is smart and remembers this exception list individually for exactly this loaded `.mldb` file![cite: 6]
*   **Customizable at any time:** If you start the tool later again with the same database, it shows you the current ignore list and asks you whether you want to keep it or create a new one.[cite: 6]

### Step 3.2: Fetch Metadata (Fetch)[cite: 6]
In this phase, the script searches for the matching metadata for your tracks via the APIs of MusicBrainz and Discogs.[cite: 6] Your original values remain completely untouched![cite: 6]

*   **[1] Smart Fetch (Standard):** The tool only checks tracks that have *not* yet been restored.[cite: 6] To avoid overwhelming you with a huge list, the script automatically pauses after 50 loaded tracks.[cite: 6] You can then switch directly to the review or load the next 50.[cite: 6]
*   **[2] Smart Fetch (Overnight):** Perfect for massive databases.[cite: 6] The script loads all new tracks in one go without pausing.[cite: 6] Ideal for letting the PC work overnight.[cite: 6]
*   **[3] Full Fetch (Reset & Overnight):** The script ignores the "RESTAURIERT" (RESTORED) flag and completely re-fetches the data for **ALL** tracks in the database.[cite: 6]

> **Tip:** You can cancel the fetch process at any time with the key combination `Ctrl + C`.[cite: 6] The script securely saves your progress up to that point, and you can continue at exactly this point the next time you start![cite: 6]

### Step 3.3: Review Data (Review)[cite: 6]
Choose Option **[4]** or **[5]**.[cite: 6] Here, the tool presents you with each track individually and suggests the metadata found on the internet.[cite: 6]

*   **Confirm:** If you like a suggestion (e.g., the year), simply press `Enter`.[cite: 6] The tool accepts the value and jumps to the next field.[cite: 6]
*   **Keep original (`O` key):** Next to the suggestion, you will always see your original database value in gray.[cite: 6] Is your own value better?[cite: 6] Simply type an `o` (for original) and press `Enter`.[cite: 6]
*   **Custom text:** The suggestion is wrong, but so is your original value?[cite: 6] Simply type in your desired text.[cite: 6]
*   **Live Re-Fetch:** If you type your own text for Artist, Title, Year, or Album (e.g., to correct a typo in the artist name), the script immediately fires off a new API search in the background and adjusts Labels, Genres, and ISRC live to your correction![cite: 6]
*   **Oops, typo?** Type a `<` or `b` (for Back) and press `Enter` to jump back one track.[cite: 6]

### Step 3.4: Maintenance[cite: 6]
Under Option **[6]** you will find powerful tools for mass editing.[cite: 6] Here you can, among other things, standardize messy genres, repair incorrect capitalization (Title Case), delete old attributes like "Lyrics" (to shrink the database), or have the English mAirList Item Types (e.g., "Music") fully automatically translated into your local language.[cite: 6]

### Step 3.5: Save in mAirList (Apply)[cite: 6]
When you have checked all tracks, select Option **[7] Save** in the main menu.[cite: 6] Only now does the script open your database copy and write the new, clean metadata into it using a fast bulk process.[cite: 6]

*   The script automatically sets the internal attribute `RESTAURIERT` to `JA` (YES) for each track.[cite: 6]
*   Tracks with this flag will be automatically skipped during future runs.[cite: 6]
*   If you notice later during live operation that a track has wrong tags after all?[cite: 6] Simply delete the "RESTAURIERT" attribute for this track in mAirList.[cite: 6] The next time the script runs, the tool will recognize the track as "new" and load it again.[cite: 6]