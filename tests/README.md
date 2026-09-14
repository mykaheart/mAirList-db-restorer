# Regression tests

The tests use Python's built-in `unittest` module; no extra test dependency is required.

Run from the project root:

```bash
python -m unittest discover -s tests -v
```

They cover the safety-critical behavior around cache separation, atomic CSV writes,
SQLite integrity checks, Full-Fetch apply protection, API request retries, track-level retries/error states, year filtering, and duplicate-flag lifecycle cleanup.

The suite also covers BPM in normal Fetch and in maintenance mode, rekordbox XML parsing and exact-path priority, protection of existing BPM even during Full Fetch, Review handling after manual identity changes, protected half/double-time conflict review, conservative AcousticBrainz consensus, overwrite protection, complete review-CSV output, diagnostic error classification, and AcousticBrainz rate-limit handling. The suite additionally covers 0.65 custom-genre persistence, mAirList XML generation, FLAC `.mmd` sidecars, MP3 `TXXX:mAirList` embedding and preservation of unrelated ID3 frames. Current suite: 37 tests.
