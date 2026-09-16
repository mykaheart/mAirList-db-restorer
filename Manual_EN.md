# 📖 Manual: mAirList DB Restorer 0.66.00 BETA

The **mAirList DB Restorer** helps maintain local mAirList databases (`.mldb`). It reads existing metadata, researches missing or questionable information through MusicBrainz and Discogs, can fill missing BPM values from rekordbox, file tags and AcousticBrainz, and provides several maintenance functions for existing databases.

The Restorer is deliberately conservative: it first creates proposals, keeps reading, review and writing separate, and performs integrity checks and backups before safety-critical database changes.

> **Important:** The application is intended for **local SQLite databases (`.mldb`)**. Network databases are not supported at this time.

---

## 1. Core principle and safety boundaries

The Restorer may add or correct metadata, but it explicitly **does not** change certain technical fields:

- `Duration`, `Length` and `TotalDuration` are never recalculated or overwritten.
- Audio content is not analysed, converted or normalised.
- Lyrics are **not deleted from the mAirList database** by the normal Restorer workflow. They are merely excluded from the working CSV files in `Data` so those files remain small.
- Existing valid `BPM` values are not overwritten automatically.
- Duplicate maintenance only marks candidates; it never deletes items.
- Detected SQLite inconsistencies are reported but not repaired automatically.

The central rule is therefore:

> **The machine finds and proposes; the human decides on content changes.**

---

## 2. Installation and first-time setup

The release ZIP contains a standalone `Restorer.exe`. A Python installation is not required for normal use.

1. Extract the ZIP completely.
2. Start `Restorer.exe`.
3. Choose a language on first start: Deutsch, English or Nederlands.
4. Enter Discogs credentials and a contact e-mail address for MusicBrainz.

Credentials are stored locally in `Data/config.json`. Discogs key, Discogs secret and the MusicBrainz contact are only Base64-encoded there; this is **not cryptographic encryption**.

### Discogs credentials

Discogs access requires free developer credentials. Consumer Key and Consumer Secret can be created in the developer settings of a Discogs account.

### MusicBrainz contact

MusicBrainz requires a meaningful User-Agent with a way to contact the client operator. The Restorer therefore asks for a valid e-mail address. It is used only as part of the MusicBrainz User-Agent.

---

## 3. Always work on a database copy 🛡️

The Restorer detects many locking situations and refuses write operations when the database is visibly in use by another program. Even so:

**Never work directly on the production database that is currently open in mAirList.**

Recommended workflow:

1. Close mAirList or create a current copy of the `.mldb` file.
2. Work on that copy with the Restorer.
3. Verify the result in mAirList.
4. Only then replace or promote the production database.

Apply, duplicate maintenance and BPM maintenance additionally create a timestamped backup next to the database. The **five newest** Restorer backups are retained automatically.

---

## 4. The `Data` folder: workspaces, logs and configuration

The Restorer automatically creates a `Data` directory next to the application. It can contain:

- `config.json` – language, API credentials, ignore lists, custom language/genre shortcuts and the preferred rekordbox XML path per database.
- `*_vorschlaege.csv` – current Fetch workspace.
- `*_restauriert.csv` – reviewed workspace used by Apply.
- `*_bpm-review_YYYYMMDD-HHMMSS.csv` – complete BPM maintenance review list.
- `*.log` – timestamped run logs.

### Collision-safe workspaces

Workspace filenames contain the database name plus a short hash derived from the full database path. Two identically named `.mldb` files in different folders therefore cannot accidentally share the same workspace.

Older workspace files are migrated where possible. If the destination name already exists, the Restorer does not overwrite it; both copies are preserved.

### Lyrics

Lyrics columns are deliberately removed when workspace CSV files are written. This affects **only the Restorer workspace**. The corresponding values in the `.mldb` remain unchanged.

---

## 5. Main menu and recommended workflow

The normal metadata workflow is:

**[1] or [2] or [3] Fetch → [4] or [5] Review → [7] Apply**

Additional options:

- **[0]** select database
- **[6]** maintenance menu
- **[8]** change language
- **[9]** exit

---

## 6. Selecting a database and configuring ignore lists

After choosing **[0]**, type the `.mldb` path or drag the file into the console window.

Before the first Fetch, the Restorer asks for folders that should be ignored. Typical examples are `OAD`, jingles, news, advertising or any other area that should not go through metadata research.

The ignore list may contain:

- physical paths,
- virtual mAirList folder names,
- partial folder names.

It is stored **per database path** in `config.json`. On a later run it can be kept or rebuilt.

The saved ignore list is also used by duplicate and BPM maintenance. The simple genre and case-normalisation maintenance functions work directly on the relevant database fields and do not use this ignore list.

---

## 7. Fetch: researching metadata

### [1] New/open tracks in batches of 50

Fetches only pending titles. After every 50 processed tracks the run can pause and switch to Review. Progress is saved atomically at regular intervals.

### [2] All open tracks without pauses

Uses the same logic as [1] but without the 50-track breaks. Useful for longer unattended runs.

### [3] Full Fetch

Re-checks all relevant tracks, including tracks that already have `RESTAURIERT=JA`.

A Full Fetch refreshes the current database state into the workspace first. Rows are internally marked `FORCE_APPLY=JA` so intentionally re-reviewed metadata may later be written despite the normal restored-track protection.

**Important:** Existing valid BPM values remain protected even during Full Fetch.

### Which items are excluded from the normal Fetch?

System/non-music types such as `Dummy`, `Stream`, `Command`, `Silence` and `Other` are filtered from the normal API Fetch. Your ignore list is applied as well.

### Which fields can be researched or proposed?

| Field | Behaviour |
| --- | --- |
| Artist | spelling/cleaning proposal |
| Title | spelling/cleaning proposal |
| Year | MusicBrainz + Discogs with plausibility/outlier logic |
| Genre | Discogs, then mapped to the Restorer genre set |
| Album | Discogs or MusicBrainz |
| STYLE | Discogs styles |
| DISCOGS_RELEASE_ID | selected Discogs reference |
| Label | Discogs |
| Labelcode | Discogs/MusicBrainz helper lookup where available |
| ISRC | MusicBrainz |
| Language | is not blindly inferred from a MusicBrainz release language; without a reliable source it remains under manual control |
| Type | proposed only when the attribute is empty, based on the internal mAirList item type |
| BPM | rekordbox XML → file tag → MusicBrainz/AcousticBrainz |

### Duration matching

Where possible, local track duration is used as an identification aid. It is **never modified**.

### Release year and outliers

The Restorer collects plausible release years and filters extreme single outliers. The objective is the original or earliest plausible release year rather than a later compilation year.

### API errors and resume

MusicBrainz, Discogs and AcousticBrainz requests use retry/rate-limit handling. In addition, normal Fetch restarts the **entire track lookup** after transient failures: up to three automatic retries with increasing delays of 2, 5 and 10 seconds. Track-level retries are limited to network/timeouts, HTTP 429 and retryable 5xx responses. Server `Retry-After` or available rate-limit reset hints are honoured and may extend the delay. Non-transient 4xx or logic errors are not retried pointlessly. Only after these automatic retries are exhausted does the track remain pending (`FEHLER`) for a later Fetch.

`Ctrl+C` ends a Fetch in a controlled way and saves the current workspace.

---

## 8. BPM in the normal Fetch

Since 0.64, BPM lookup is part of the normal Fetch workflow.

### Selecting rekordbox XML

Before a normal Fetch you can provide a rekordbox XML export. The selected path is stored **per database** and shown as the default next time.

- `Enter` accepts the displayed default path.
- `-` disables XML use and clears the saved path for that database.
- If no saved path exists, the Restorer also looks for `rekordbox.xml` next to the application or in the `Data` directory.
- If the XML is missing or invalid, the metadata Fetch continues and BPM falls back to the other sources.

### Source priority

For a track without a valid BPM:

1. **rekordbox XML** – `AverageBpm`, only when `Location` resolves to the exact same file path.
2. **Audio file tag** – for example ID3 `TBPM` or Vorbis/FLAC `BPM`/`tempo`.
3. **MusicBrainz Recording ID** – preferably from a valid ISRC, otherwise conservative Artist/Title/duration matching.
4. **AcousticBrainz** – Low-Level BPM only for a safely identified MusicBrainz recording.

rekordbox matching performs **no fuzzy Artist/Title matching**. The file path is the identity.

### Protection of existing BPM

If the live database already contains a valid BPM, no new BPM proposal is created for that item, including during Full Fetch.

### Review behaviour

A new `BPM_Vorschlag` is shown in normal Review and automatically copied to `BPM`. The source is retained in the workspace as `BPM_Quelle`. The source itself is not written as a mAirList attribute.

A BPM-only failure does not make the rest of the metadata unusable. If the track identity is manually changed during Review, a BPM proposal previously obtained through AcousticBrainz is discarded for safety; rekordbox and file-tag BPM remain tied to the concrete file. The other metadata can still proceed normally, and missing BPM can later be filled separately with maintenance option [6].

---

## 9. `RESTAURIERT`, resume and reset behaviour

After a successful Apply, the Restorer sets `RESTAURIERT=JA` on written tracks.

Normal later Fetch runs protect and skip those tracks.

If you remove the `RESTAURIERT` attribute from a track in mAirList, the `.mldb` becomes the source of truth on the next run. The stale workspace status is reset and that track's original fields are refreshed from the database before it is fetched again.

Full Fetch is the explicit exception. It marks the working rows `FORCE_APPLY=JA` so deliberately re-reviewed metadata can be written even for already restored tracks. `FORCE_APPLY` is cleared after successful Apply.

---

## 10. Review: checking proposals

### [4] Manual Review

Each open, successfully fetched track is shown individually.

For interactive fields:

- **Enter** – accept proposal.
- **o** – keep original value.
- **custom text** – enter your own value.
- **`<` or `b`** – go back one track.

### [5] Review with automation

High-confidence Year and Genre proposals may be accepted automatically. Other fields remain reviewable like in manual mode.

### Live re-fetch

If Artist, Title, Year or Album is changed manually, the Restorer performs a targeted new MusicBrainz/Discogs lookup so dependent proposals such as Genre, Label, Labelcode, ISRC, STYLE and Discogs ID follow the corrected identity.

### Automatically accepted technical fields

When a safe proposal exists, `STYLE`, `DISCOGS_RELEASE_ID`, `Labelcode`, `ISRC`, `Type` and `BPM` are copied into the reviewed workspace without another individual prompt. Existing BPM has already been protected earlier and therefore receives no new proposal.

### Genre shortcuts and genre memory

Manual genre review offers numeric shortcuts. The list deliberately starts with **`1=Rock`** and **`2=Pop`**, followed by the other Restorer core genres. Free-text genres are stored under `CUSTOM_GENRES` in `Data/config.json` and become numeric choices for subsequent tracks.

This memory is **UI-only**: a custom genre does not extend `ALLOWED_GENRES` and does not modify automatic synonym/normalization rules. A one-off manual genre therefore cannot silently change future API decisions.

### Language

MusicBrainz does not provide a reliable recording-language value in this workflow, so the Restorer does not derive language from an arbitrary release-language field. Existing values are preserved and language can be set manually in Review. Frequently used custom languages are stored in `config.json`.

---

## 11. Apply: writing reviewed changes safely to `.mldb`

Option **[7]** writes only tracks whose Review is complete.

Before writing, the Restorer performs:

1. restored-track protection check.
2. explicit `FORCE_APPLY=JA` exceptions for Full Fetch rows.
3. SQLite `integrity_check`.
4. summary of actual field changes, including BPM.
5. safety confirmation.
6. timestamped `.mldb` backup.
7. cleanup of old Restorer backups, retaining the newest five.
8. batched database writes.
9. second SQLite integrity check.
10. workspace synchronisation and `RESTAURIERT=JA` update.

If the integrity check fails **before** writing, nothing is changed. Messages such as `wrong # of entries in index ...` generally indicate a pre-existing SQLite/index problem. The Restorer intentionally does not repair database structures automatically.

---

## 12. Maintenance menu [6]

The maintenance menu contains direct database/file maintenance actions and is separate from the normal Fetch/Review/Apply workflow.

> **Warning:** Simple maintenance options [1]–[4] write directly. Make your own database/file copy first. The more complex options [5] and [6] include additional integrated integrity/backup safeguards.

### Maintenance [1] – Standardise genres

Existing genres are mapped to the Restorer's core categories, currently including:

`Pop`, `EDM`, `Blues`, `Hiphop`, `Rap`, `Rock`, `Classic Rock`, `Pop-Rock`, `R and B`, `Soul`, `Reggae`.

A native genre field and a genre attribute are both handled when present in the database schema.

### Maintenance [2] – Fix case and apostrophes

Artist and Title are normalised to consistent apostrophes and smart capitalisation. This function writes directly to the corresponding `items` fields.

### Maintenance [3] – File tagger and mAirList metadata backup

The tagger uses **reviewed values from the database** and offers two modes:

1. **Portable audio tags only**
2. **Portable audio tags + full mAirList metadata backup**

Mutagen support currently covers FLAC, Ogg Vorbis, MP3 and AIFF.

Portable tags include Artist, Title, Year/Date, Genre, Album, Label/Publisher, Language, BPM and ISRC.

In mode 2 the Restorer additionally backs up mAirList data already present in the `.mldb`. It **does not re-analyze audio** and does not calculate new cues or loudness values. Existing `Amplification`, every `item_cuemarkers` entry, Peak, True Peak, Loudness and useful mAirList/user attributes are copied.

**MP3 and AIFF:** the metadata block is stored directly as `TXXX:mAirList`. Only that mAirList frame is replaced; unrelated ID3 frames, artwork and other embedded data are preserved.

**FLAC and Ogg Vorbis:** mAirList does not interpret an arbitrary `MAIRLIST` Vorbis comment as cue/analysis metadata. The Restorer therefore creates the supported sidecar using the exact audio filename plus `.mmd`, for example `Song.flac.mmd`. It contains the same `<PlaylistItem>` XML model used by mAirList itself.

The `.mmd` file is written atomically and only when its content changes. `Duration` is read **only from the database**; it is never recalculated from audio and is never changed in the database.

Restorer-internal attributes (`RESTAURIERT`, `DOPPELUNG`, `FORCE_APPLY`) and Lyrics/Songtext fields are excluded from this file backup.

Because mAirList often stores filenames relative to Storage Locations, the tagger asks for local base folders. Audio files are modified directly and there is no undo mechanism, so a file backup is recommended.

### Maintenance [4] – Combined run

Runs **maintenance [1] and [2] only**. The file tagger is not part of this combined action.

---

## 13. Maintenance [5] – Duplicate candidates

Duplicate checking is a **review aid**, not an automatic deletion feature.

Music items are linked as candidates when at least one strong criterion matches:

- same normalised Artist + Title,
- same stored file path,
- same valid ISRC.

Different durations deliberately do not prevent a match because Radio Edits, album versions, remasters or other variants should be judged by a human afterwards.

### What is written?

Candidate items receive:

`DOPPELUNG=JA`

No track is deleted automatically and no candidate is declared “wrong”.

On a later scan, the state is rebuilt from the current database. If a previous partner no longer exists, the stale `DOPPELUNG` flag is removed.

### Suggested Smart Folder in mAirList

Make `DOPPELUNG` available as a standard attribute and use a filter such as:

- Attribute: `DOPPELUNG`
- Condition: `is one of`
- Value: `JA`

### Safety

When a change is needed:

1. integrity check
2. backup
3. one database transaction for the new state
4. second integrity check

---

## 14. Maintenance [6] – Fill missing BPM directly

This option remains available for BPM-only maintenance even though BPM lookup is also integrated into normal Fetch.

It operates only on file-backed music items without a valid BPM.

### rekordbox XML

The same per-database saved rekordbox XML selection used by normal Fetch can be reused. rekordbox provides `AverageBpm`; the Restorer accepts it only when the file path matches exactly.

### Fallbacks

If rekordbox does not provide a match:

1. read BPM from the local audio tag.
2. identify a MusicBrainz recording through ISRC or conservative matching.
3. query AcousticBrainz Low-Level BPM.

When multiple AcousticBrainz analyses exist, only a tight consensus is accepted. Ambiguous Half-/Double-Time situations are rejected.

### Preview, diagnostics and review CSV

Before writing, maintenance shows a preview and summary. It also creates a complete BPM review CSV in `Data` containing, among other columns:

- ID
- Artist
- Title
- proposed BPM
- existing BPM
- original source BPM
- Source
- Status
- AcousticBrainz consensus
- Recording MBID
- matching method

Non-matches and errors are split by cause, such as:

- audio file unreachable
- file tag unreadable
- no unique MusicBrainz recording
- MusicBrainz network/timeout, 429, 5xx or other HTTP error
- AcousticBrainz has no dataset entry
- AcousticBrainz entry has no usable BPM
- no safe AcousticBrainz consensus
- AcousticBrainz network/rate-limit/server error

### Half-/Double-Time conflicts

If a valid BPM already exists and rekordbox reports a materially different value, nothing is overwritten. Typical 2:1 cases such as `180 ↔ 90` are listed in the review CSV as `HALF_DOUBLE_KONFLIKT`.

This is intentionally a warning only: different DJ/analysis programs may count the same musical pulse in Half- or Double-Time.

### Safety

After explicit confirmation:

1. integrity check
2. backup
3. atomic BPM transaction
4. live protection against BPM values that appeared during the scan
5. second integrity check

`RESTAURIERT` is **not changed** by BPM maintenance.

AcousticBrainz uses at least a 1.05-second base interval and also observes dynamic rate-limit headers.

---

## 15. rekordbox workflow for large libraries

For high BPM coverage:

1. Import the music library into rekordbox.
2. Let rekordbox analyse all tracks.
3. Export the Collection as rekordbox XML.
4. Select that XML in normal Fetch or maintenance [6].
5. rekordbox can be analysed/exported again later; if the export stays at the same path, the Restorer automatically reuses the saved path next time.

The Restorer never writes back to the rekordbox library.

---

## 16. Errors and diagnostics

### Database is locked

mAirList or another program is holding the `.mldb` open. Close the application or use a real copy.

### SQLite integrity check fails

The Restorer aborts the write. The inconsistency existed before the attempted write. No automatic REINDEX/repair operation is performed.

### API errors

Transient metadata API failures trigger up to three complete track-level retries in normal Fetch (2/5/10 s; server `Retry-After` is honoured). A track remains pending only if the failure persists after those retries. Non-transient 4xx errors are not automatically retried. A BPM-only fallback failure does not prevent the other metadata from being reviewed; BPM can be added later through maintenance [6].

### Audio file not found

File-tag/BPM lookup and the file tagger need local paths that can be resolved. BPM matching can resolve mAirList Storage Locations from the database; the file tagger additionally allows manual base directories.

### rekordbox XML does not match

Only exact file paths are accepted. If files were moved after export or storage paths differ, the Restorer falls back to the next BPM source.

---

## 17. Command line for developers/power users

Normal release use is through the interactive menu. In Python/source operation, phases such as `fetch`, `review`, `apply`, `maintenance` and `check_update` are also available.

Fetch supports, among others:

- `--full`
- `--no-breaks`
- `--rekordbox-xml <path>`
- `--lang de|en|nl`

The interactive EXE workflow remains the recommended method.

---

## 18. What the Restorer intentionally does not do

- no track-duration changes
- no audio analysis or loudness calculation
- no audio format conversion
- no automatic duplicate deletion
- no automatic SQLite repair
- no derivation of vocal language from an unreliable MusicBrainz release field
- no automatic overwrite of existing valid BPM
- no mAirList network-database support

---

## 19. Tests and release safety

The source includes regression tests covering workspace separation, Lyrics exclusion, Apply protection, Full-Fetch override, duplicate state, BPM consensus, exact rekordbox path matching, Half-/Double-Time protection, API retry/rate limits including track-level retry and backup/confirmation logic.

For developers:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions additionally runs a compile check and the regression suite on Windows.

---

## 20. Licence and support

mAirList DB Restorer is **source-available freeware**. Exact usage and redistribution terms are defined in `LICENSE`.

Please use the official project channels for bug reports and feature requests: GitHub Issues or the official release thread in the mAirList forum.

### Maintenance [7] – Fill missing speed groups

This function uses mAirList's existing standard **`Geschwindigkeit`** attribute with the values `Langsam`, `Medium` and `Schnell`. It fills **only items without an existing classification**. Existing values are treated as authoritative/manual decisions and are never changed.

- up to and including **100 BPM** → `Langsam`
- **above 100 and below 130 BPM** → `Medium`
- **130 BPM and above** → `Schnell`

Before writing, the Restorer shows candidate counts per group, checks database integrity, creates a backup and checks integrity again afterwards. Immediately before each write it re-checks whether a classification has appeared in the meantime.

### Remember last database and source folders

After a valid database selection the Restorer stores the path as `LAST_DATABASE` in `Data/config.json`. On the next interactive start it can be reused directly. Local base/source folders for relative mAirList Storage paths are stored per database under `DB_SOURCE_FOLDERS` and are automatically reused by both the file tagger and BPM maintenance.
