import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import requests

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import api
import db
import main
import utils


def create_test_db(path, rows=None):
    rows = rows or [
        (1, 'Song One', 'Artist One', 'Music', 'song1.flac', 180.0, 180.0),
        (2, 'Song Two', 'Artist Two', 'Music', 'song2.flac', 200.0, 200.0),
    ]
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute('CREATE TABLE config (name TEXT PRIMARY KEY, value TEXT)')
    cur.execute("INSERT INTO config(name, value) VALUES ('schemaversion', '25')")
    cur.execute('''CREATE TABLE items (
        idx INTEGER PRIMARY KEY,
        title TEXT,
        artist TEXT,
        type TEXT,
        filename TEXT,
        duration REAL,
        totalduration REAL
    )''')
    cur.execute('''CREATE TABLE item_attributes (
        item INTEGER,
        name TEXT,
        value TEXT,
        PRIMARY KEY(item, name)
    )''')
    cur.executemany('INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?)', rows)
    cur.executemany(
        'INSERT INTO item_attributes(item, name, value) VALUES (?, ?, ?)',
        [
            (1, 'Jahr', '1999'), (1, 'Genre', 'Pop'), (1, 'RESTAURIERT', 'JA'),
            (1, 'LYRICS', 'line 1\nline 2'),
            (2, 'Jahr', '2001'), (2, 'Genre', 'Rock'), (2, 'RESTAURIERT', 'JA'),
        ]
    )
    conn.commit()
    conn.close()


class WorkspaceTests(unittest.TestCase):
    def test_database_session_names_do_not_collide(self):
        a = main.get_db_session_name(os.path.join('A', 'Archiv.mldb'))
        b = main.get_db_session_name(os.path.join('B', 'Archiv.mldb'))
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith('Archiv_'))
        self.assertTrue(b.startswith('Archiv_'))

    def test_atomic_csv_excludes_lyrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'session.csv')
            frame = pd.DataFrame([
                {'ID': '1', 'Artist': 'A', 'LYRICS': 'huge\ntext', 'Songtext': 'more'}
            ])
            utils.save_safe_csv(frame, path)
            loaded = pd.read_csv(path, dtype=str)
            self.assertNotIn('LYRICS', loaded.columns)
            self.assertNotIn('Songtext', loaded.columns)
            self.assertEqual(loaded.loc[0, 'Artist'], 'A')
            self.assertFalse(any(name.startswith('.session.csv.tmp-') for name in os.listdir(tmp)))

    def test_legacy_cache_is_migrated_to_hashed_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, 'Archiv.mldb')
            Path(db_path).write_bytes(b'not-needed-for-name-test')
            old_path = os.path.join(tmp, 'Archiv_vorschlaege.csv')
            Path(old_path).write_text('ID\n1\n', encoding='utf-8')
            session_name = main.get_db_session_name(db_path)
            new_path = os.path.join(tmp, session_name + '_vorschlaege.csv')
            main._migrate_legacy_cache_for_db(db_path, session_name, tmp)
            self.assertFalse(os.path.exists(old_path))
            self.assertTrue(os.path.exists(new_path))


class DatabaseSafetyTests(unittest.TestCase):
    def test_schema_probe_does_not_create_missing_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, 'does-not-exist.mldb')
            self.assertIsNone(db.get_schema_version(missing))
            self.assertFalse(os.path.exists(missing))

    def test_integrity_check_and_lyrics_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'test.mldb')
            create_test_db(path)
            ok, details = db.check_integrity(path)
            self.assertTrue(ok, details)
            frame = db.load_dataframe_from_mldb(path, [])
            self.assertNotIn('LYRICS', frame.columns)
            self.assertEqual(frame.loc[frame['ID'] == '1', 'Jahr'].iloc[0], '1999')

    def test_full_fetch_override_does_not_disable_normal_apply_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, 'test.mldb')
            create_test_db(db_path)
            final_csv = os.path.join(tmp, 'test_restauriert.csv')
            fetch_csv = os.path.join(tmp, 'test_vorschlaege.csv')

            frame = pd.DataFrame([
                {
                    'ID': '1', 'Artist': 'Changed One', 'Title': 'Song One',
                    'Jahr': '1999', 'Genre': 'Pop', 'REVIEW_STATUS': 'JA',
                    'FORCE_APPLY': 'JA', 'RESTAURIERT': 'JA'
                },
                {
                    'ID': '2', 'Artist': 'Should Stay Two', 'Title': 'Song Two',
                    'Jahr': '2001', 'Genre': 'Rock', 'REVIEW_STATUS': 'JA',
                    'FORCE_APPLY': '', 'RESTAURIERT': 'JA'
                },
            ])
            utils.save_safe_csv(frame, final_csv)
            utils.save_safe_csv(frame, fetch_csv)

            with patch.object(main.console, 'input', return_value='JA'):
                main.phase_apply(db_path, final_csv)

            conn = sqlite3.connect(db_path)
            rows = dict(conn.execute('SELECT idx, artist FROM items').fetchall())
            conn.close()
            self.assertEqual(rows[1], 'Changed One')
            self.assertEqual(rows[2], 'Artist Two')


class DuplicateMaintenanceTests(unittest.TestCase):
    def test_duplicate_flags_follow_current_database_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'duplicates.mldb')
            rows = [
                (1, 'Same Song', 'Same Artist', 'Music', 'a.flac', 180.0, 180.0),
                (2, 'Same Song', 'Same Artist', 'Music', 'b.flac', 224.0, 224.0),
                (3, 'Unique Song', 'Other Artist', 'Music', 'c.flac', 200.0, 200.0),
            ]
            create_test_db(path, rows=rows)

            conn = sqlite3.connect(path)
            conn.execute("INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (3, 'DOPPELUNG', 'JA')")
            conn.commit()
            conn.close()

            frame = db.load_dataframe_from_mldb(path, [])
            groups = db.find_duplicate_groups(frame)
            candidate_ids = set().union(*groups) if groups else set()
            self.assertEqual(candidate_ids, {'1', '2'})

            result = db.apply_duplicate_flags(path, candidate_ids)
            self.assertEqual(result['new'], 2)
            self.assertEqual(result['removed'], 1)

            conn = sqlite3.connect(path)
            flags = dict(conn.execute("SELECT item, value FROM item_attributes WHERE name = 'DOPPELUNG'").fetchall())
            durations = dict(conn.execute('SELECT idx, duration FROM items').fetchall())
            conn.close()
            self.assertEqual(flags, {1: 'JA', 2: 'JA'})
            self.assertEqual(durations, {1: 180.0, 2: 224.0, 3: 200.0})

            conn = sqlite3.connect(path)
            conn.execute('DELETE FROM item_attributes WHERE item = 2')
            conn.execute('DELETE FROM items WHERE idx = 2')
            conn.commit()
            conn.close()

            frame = db.load_dataframe_from_mldb(path, [])
            groups = db.find_duplicate_groups(frame)
            candidate_ids = set().union(*groups) if groups else set()
            self.assertEqual(candidate_ids, set())

            result = db.apply_duplicate_flags(path, candidate_ids)
            self.assertEqual(result['removed'], 1)
            self.assertEqual(db.get_duplicate_flag_state(path), {})

    def test_duplicate_detection_uses_file_path_and_valid_isrc(self):
        frame = pd.DataFrame([
            {'ID': '10', 'Artist': 'Alpha', 'Title': 'One', 'ItemType': 'Music', 'Filename': r'C:\\Music\\same.flac', 'ISRC': ''},
            {'ID': '11', 'Artist': 'Beta', 'Title': 'Two', 'ItemType': 'Music', 'Filename': r'c:/music/same.flac', 'ISRC': ''},
            {'ID': '20', 'Artist': 'Gamma', 'Title': 'Three', 'ItemType': 'Music', 'Filename': 'g.flac', 'ISRC': 'DEABC1234567'},
            {'ID': '21', 'Artist': 'Delta', 'Title': 'Four', 'ItemType': 'Music', 'Filename': 'd.flac', 'ISRC': 'DE-ABC-12-34567'},
            {'ID': '30', 'Artist': 'Unique', 'Title': 'Track', 'ItemType': 'Music', 'Filename': 'u.flac', 'ISRC': 'invalid'},
        ])
        groups = [set(group) for group in db.find_duplicate_groups(frame)]
        self.assertIn({'10', '11'}, groups)
        self.assertIn({'20', '21'}, groups)
        self.assertFalse(any('30' in group for group in groups))


class DuplicateMaintenanceIntegrationTests(unittest.TestCase):
    def test_phase_maintenance_duplicate_scan_creates_backup_and_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'maintenance.mldb')
            rows = [
                (1, 'Same Song', 'Same Artist', 'Music', 'a.flac', 180.0, 180.0),
                (2, 'Same Song', 'Same Artist', 'Music', 'b.flac', 181.0, 181.0),
            ]
            create_test_db(path, rows=rows)

            with patch.object(main.console, 'input', return_value='5'), patch.object(main.utils, 'get_saved_ignored_folders', return_value=[]):
                main.phase_maintenance(path)

            conn = sqlite3.connect(path)
            flags = dict(conn.execute("SELECT item, value FROM item_attributes WHERE name = 'DOPPELUNG'").fetchall())
            conn.close()
            self.assertEqual(flags, {1: 'JA', 2: 'JA'})
            backups = [name for name in os.listdir(tmp) if name.startswith('maintenance.mldb.backup-')]
            self.assertEqual(len(backups), 1)


class APIRetryTests(unittest.TestCase):
    def setUp(self):
        api._last_mb_request = 0.0
        api._last_discogs_request = 0.0

    def test_musicbrainz_transient_error_is_retried(self):
        response = Mock()
        response.status_code = 200
        response.headers = {}
        response.json.return_value = {'artists': []}
        with patch.object(api, 'MB_MIN_INTERVAL', 0), patch.object(api.time, 'sleep'), patch.object(api.requests, 'get', side_effect=[requests.Timeout('boom'), response]) as getter:
            result = api.mb_get('https://example.invalid', {'q': 'x'})
        self.assertIs(result, response)
        self.assertEqual(getter.call_count, 2)

    def test_permanent_api_failure_marks_track_as_error_not_finished(self):
        input_df = pd.DataFrame([{
            'ID': '1', 'Artist': 'A', 'Title': 'T', 'ItemType': 'Music',
            'Filename': 'x.flac', 'Duration': '180', 'TotalDuration': '180',
            'Jahr': '', 'Genre': '', 'Album': '', 'STYLE': '', 'DISCOGS_RELEASE_ID': '',
            'Label': '', 'Labelcode': '', 'ISRC': '', 'Sprache': '', 'Typ': '',
            'RESTAURIERT': '', 'DOPPELUNG': ''
        }])
        with tempfile.TemporaryDirectory() as tmp:
            fetch_csv = os.path.join(tmp, 'fetch.csv')
            with patch.object(main.db, 'verify_db_compatibility'), patch.object(main.db, 'is_db_locked', return_value=False), patch.object(main.utils, 'setup_ignored_folders', return_value=[]), patch.object(main.db, 'load_dataframe_from_mldb', return_value=input_df), patch.object(main.db, 'detect_db_language', return_value='de'), patch.object(main.api, 'suggest_artist_spelling', side_effect=api.APIRequestError('offline')):
                main.phase_fetch('dummy.mldb', fetch_csv, no_breaks=True)

            loaded = pd.read_csv(fetch_csv, dtype=str).fillna('')
            self.assertEqual(loaded.loc[0, 'VORSCHLAG_STATUS'], 'FEHLER')
            self.assertNotEqual(loaded.loc[0, 'VORSCHLAG_STATUS'], 'FERTIG')


class LogicRegressionTests(unittest.TestCase):
    def test_year_outlier_filter(self):
        self.assertEqual(utils.filter_valid_years(['1988', '1988', '2004']), '1988')
        self.assertEqual(utils.filter_valid_years(['1945', '2004', '2005']), '2004')


if __name__ == '__main__':
    unittest.main()
