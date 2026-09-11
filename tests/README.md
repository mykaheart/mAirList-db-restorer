# Regression tests

The tests use Python's built-in `unittest` module; no extra test dependency is required.

Run from the project root:

```bash
python -m unittest discover -s tests -v
```

They cover the safety-critical behavior around cache separation, atomic CSV writes,
SQLite integrity checks, Full-Fetch apply protection, API retries/error states, year filtering, and duplicate-flag lifecycle cleanup.
