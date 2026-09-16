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
                # Deliberately different duration: still a review candidate.
                (2, 'Same Song', 'Same Artist', 'Music', 'b.flac', 224.0, 224.0),
                (3, 'Unique Song', 'Other Artist', 'Music', 'c.flac', 200.0, 200.0),
            ]
            create_test_db(path, rows=rows)

            conn = sqlite3.connect(path)
            conn.execute(
                "INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (3, 'DOPPELUNG', 'JA')"
            )
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
            flags = dict(conn.execute(
                "SELECT item, value FROM item_attributes WHERE name = 'DOPPELUNG'"
            ).fetchall())
            durations = dict(conn.execute('SELECT idx, duration FROM items').fetchall())
            conn.close()
            self.assertEqual(flags, {1: 'JA', 2: 'JA'})
            self.assertEqual(durations, {1: 180.0, 2: 224.0, 3: 200.0})

            # Simulate reviewing the group in mAirList and deleting the unwanted copy.
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

            with patch.object(main.console, 'input', return_value='5'), \
                 patch.object(main.utils, 'get_saved_ignored_folders', return_value=[]):
                main.phase_maintenance(path)

            conn = sqlite3.connect(path)
            flags = dict(conn.execute(
                "SELECT item, value FROM item_attributes WHERE name = 'DOPPELUNG'"
            ).fetchall())
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
        with patch.object(api, 'MB_MIN_INTERVAL', 0), \
             patch.object(api.time, 'sleep'), \
             patch.object(api.requests, 'get', side_effect=[requests.Timeout('boom'), response]) as getter:
            result = api.mb_get('https://example.invalid', {'q': 'x'})
        self.assertIs(result, response)
        self.assertEqual(getter.call_count, 2)


    def test_final_429_exposes_retry_after_for_track_retry(self):
        response = Mock()
        response.status_code = 429
        response.headers = {'Retry-After': '7'}
        with patch.object(api, 'API_MAX_ATTEMPTS', 1),              patch.object(api, 'MB_MIN_INTERVAL', 0),              patch.object(api.requests, 'get', return_value=response):
            with self.assertRaises(api.APIRequestError) as caught:
                api.mb_get('https://example.invalid', {'q': 'x'})
        self.assertEqual(caught.exception.kind, 'rate_limit')
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.retry_after, 7.0)

    def test_acousticbrainz_rate_headers_are_honored(self):
        response = Mock()
        response.status_code = 200
        response.headers = {
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset-In': '0.5',
        }
        response.json.return_value = {}
        api._last_acousticbrainz_request = 0.0
        with patch.object(api, 'ACOUSTICBRAINZ_MIN_INTERVAL', 0), \
             patch.object(api.time, 'sleep') as sleeper, \
             patch.object(api.requests, 'get', return_value=response):
            result = api.acousticbrainz_get('https://example.invalid')
        self.assertIs(result, response)
        sleeper.assert_called_with(0.55)

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
            with patch.object(main.db, 'verify_db_compatibility'), \
                 patch.object(main.db, 'is_db_locked', return_value=False), \
                 patch.object(main.utils, 'setup_ignored_folders', return_value=[]), \
                 patch.object(main.db, 'load_dataframe_from_mldb', return_value=input_df), \
                 patch.object(main.db, 'detect_db_language', return_value='de'), \
                 patch.object(main.api, 'suggest_artist_spelling', side_effect=api.APIRequestError('offline')):
                main.phase_fetch('dummy.mldb', fetch_csv, no_breaks=True)

            loaded = pd.read_csv(fetch_csv, dtype=str).fillna('')
            self.assertEqual(loaded.loc[0, 'VORSCHLAG_STATUS'], 'FEHLER')
            self.assertNotEqual(loaded.loc[0, 'VORSCHLAG_STATUS'], 'FERTIG')

    def test_transient_track_failure_is_retried_and_can_finish(self):
        input_df = pd.DataFrame([{
            'ID': '1', 'Artist': 'A', 'Title': 'T', 'ItemType': 'Music',
            'Filename': 'x.flac', 'Duration': '180', 'TotalDuration': '180',
            'Jahr': '', 'Genre': '', 'Album': '', 'STYLE': '', 'DISCOGS_RELEASE_ID': '',
            'Label': '', 'Labelcode': '', 'ISRC': '', 'Sprache': '', 'Typ': '', 'BPM': '',
            'RESTAURIERT': '', 'DOPPELUNG': ''
        }])
        discogs_empty = {
            'years': [], 'genre': '', 'discogs_id': '', 'style': '',
            'label': '', 'label_code': '', 'album': '', 'confidence': 'niedrig'
        }
        transient = api.APIRequestError(
            'MusicBrainz offline', service='MusicBrainz', kind='network'
        )
        with tempfile.TemporaryDirectory() as tmp:
            fetch_csv = os.path.join(tmp, 'fetch.csv')
            with patch.object(main.db, 'verify_db_compatibility'),                  patch.object(main.db, 'is_db_locked', return_value=False),                  patch.object(main.utils, 'setup_ignored_folders', return_value=[]),                  patch.object(main.db, 'load_dataframe_from_mldb', return_value=input_df),                  patch.object(main.db, 'detect_db_language', return_value='de'),                  patch.object(main.api, 'suggest_artist_spelling', return_value=''),                  patch.object(main.api, 'suggest_title_spelling', return_value=''),                  patch.object(main.api, 'fetch_musicbrainz_details', side_effect=[
                     transient, ('1999', 'hoch', '', '', '')
                 ]) as mb_fetch,                  patch.object(main.api, 'fetch_discogs_details', return_value=discogs_empty),                  patch.object(main, '_fetch_bpm_proposal_for_row', return_value=(None, '')),                  patch.object(main.time, 'sleep') as sleeper:
                main.phase_fetch('dummy.mldb', fetch_csv, no_breaks=True)

            loaded = pd.read_csv(fetch_csv, dtype=str).fillna('')
        self.assertEqual(loaded.loc[0, 'VORSCHLAG_STATUS'], 'FERTIG')
        self.assertEqual(loaded.loc[0, 'Jahr_Vorschlag'], '1999')
        self.assertEqual(mb_fetch.call_count, 2)
        sleeper.assert_called_once_with(2.0)

    def test_track_retry_uses_server_advertised_delay_when_longer(self):
        exc = api.APIRequestError(
            'rate limited', service='MusicBrainz', kind='rate_limit',
            status_code=429, retry_after=7.5
        )
        self.assertTrue(main._is_transient_fetch_error(exc))
        self.assertEqual(main._fetch_track_retry_delay(exc, 1), 7.5)
        non_transient = api.APIRequestError(
            'unauthorized', service='Discogs', kind='http', status_code=401
        )
        self.assertFalse(main._is_transient_fetch_error(non_transient))


class BPMMaintenanceTests(unittest.TestCase):
    def test_acousticbrainz_consensus_accepts_close_values_and_rejects_half_double(self):
        selected = api.select_acousticbrainz_bpm([137.6, 138.1, 138.4])
        self.assertEqual(selected['bpm'], 138)
        self.assertEqual(selected['agree'], 3)
        self.assertIsNone(api.select_acousticbrainz_bpm([86.0, 172.0]))

    def test_musicbrainz_bpm_match_prefers_valid_isrc_recording(self):
        response = Mock()
        response.json.return_value = {
            'recordings': [{
                'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
                'title': 'Test Song',
                'length': 180500,
                'artist-credit': [{'name': 'Test Artist'}],
                'score': 100,
            }]
        }
        with patch.object(api, 'mb_get', return_value=response) as getter:
            match = api.find_musicbrainz_recording_for_bpm(
                'Test Artist', 'Test Song', isrc='DE-ABC-12-34567', local_duration_sec=180
            )
        self.assertEqual(match['mbid'], 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        self.assertEqual(match['matched_by'], 'ISRC')
        self.assertIn('isrc:DEABC1234567', getter.call_args.args[1]['query'])

    def test_acousticbrainz_bulk_parser_uses_consensus(self):
        mbid = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        count_response = Mock()
        count_response.json.return_value = {mbid: {'count': 3}}
        data_response = Mock()
        data_response.json.return_value = {
            mbid: {
                '0': {'rhythm': {'bpm': 127.7}},
                '1': {'rhythm': {'bpm': 128.2}},
                '2': {'rhythm': {'bpm': 255.8}},
            }
        }
        with patch.object(api, 'acousticbrainz_get', side_effect=[count_response, data_response]):
            result = api.fetch_acousticbrainz_bpms([mbid])
        self.assertEqual(result[mbid]['bpm'], 128)
        self.assertEqual(result[mbid]['agree'], 2)
        self.assertEqual(result[mbid]['total'], 3)


    def test_acousticbrainz_status_classifies_rate_limit_failure(self):
        mbid = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        error = api.APIRequestError(
            'AcousticBrainz: HTTP 429', service='AcousticBrainz',
            kind='rate_limit', status_code=429
        )
        with patch.object(api, 'acousticbrainz_get', side_effect=error):
            result, status = api.fetch_acousticbrainz_bpms([mbid], include_status=True)
        self.assertEqual(result, {})
        self.assertEqual(status[mbid]['status'], 'api_error')
        self.assertEqual(status[mbid]['kind'], 'rate_limit')
        self.assertEqual(status[mbid]['http_status'], 429)

    def test_bpm_review_csv_contains_full_review_fields(self):
        preview = [
            {
                'id': '10', 'artist': 'Artist', 'title': 'Song', 'bpm': 128,
                'source': 'AcousticBrainz (3/3)', 'source_name': 'AcousticBrainz',
                'consensus': '3/3',
                'mbid': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
                'matched_by': 'ISRC',
            },
            {
                'id': '11', 'artist': 'Other', 'title': 'Track', 'bpm': 111,
                'source': 'Datei-Tag', 'source_name': 'Datei-Tag',
                'consensus': '', 'mbid': '', 'matched_by': 'Datei-Tag',
            },
        ]
        with tempfile.TemporaryDirectory() as tmp, patch.object(main.utils, 'DATA_DIR', tmp):
            path = main._save_bpm_review_csv('/music/Test.mldb', preview)
            self.assertTrue(os.path.isfile(path))
            frame = pd.read_csv(path, dtype=str).fillna('')
        self.assertEqual(list(frame.columns), [
            'ID', 'Artist', 'Title', 'BPM', 'Existing_BPM', 'Source_BPM',
            'Source', 'Status', 'Consensus', 'MBID', 'Matched_By'
        ])
        self.assertEqual(len(frame), 2)
        self.assertEqual(frame.loc[0, 'Consensus'], '3/3')
        self.assertEqual(frame.loc[0, 'Matched_By'], 'ISRC')

    def test_bpm_scan_classifies_musicbrainz_network_failure(self):
        frame = pd.DataFrame([{
            'ID': '1', 'Artist': 'A', 'Title': 'One', 'ItemType': 'Music',
            'Filename': 'missing.flac', 'Duration': 180, 'ISRC': ''
        }])
        error = api.APIRequestError('offline', service='MusicBrainz', kind='network')
        with patch.object(main.utils, 'get_saved_ignored_folders', return_value=[]), \
             patch.object(main.db, 'load_dataframe_from_mldb', return_value=frame), \
             patch.object(main.db, 'get_bpm_flag_state', return_value={}), \
             patch.object(main.db, 'read_audio_bpm_metadata', return_value={
                 'path': None, 'bpm': None, 'mbid': '', 'file_status': 'not_found'
             }), \
             patch.object(main.api, 'find_musicbrainz_recording_for_bpm', side_effect=error):
            proposals, preview, stats = main._scan_bpm_candidates('dummy.mldb', [])
        self.assertEqual(proposals, {})
        self.assertEqual(preview, [])
        self.assertEqual(stats['errors'], 1)
        self.assertEqual(stats['diagnostics']['mb_network'], 1)
        self.assertEqual(stats['diagnostics']['file_unreachable'], 1)

    def test_apply_bpm_values_never_overwrites_existing_bpm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'bpm.mldb')
            create_test_db(path)
            conn = sqlite3.connect(path)
            conn.execute("INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (1, 'BPM', '99')")
            conn.commit()
            conn.close()

            result = db.apply_bpm_values(path, {'1': 120, '2': 130})
            self.assertEqual(result['written'], 1)
            self.assertEqual(result['skipped_existing'], 1)

            conn = sqlite3.connect(path)
            rows = dict(conn.execute(
                "SELECT item, value FROM item_attributes WHERE LOWER(name) = 'bpm'"
            ).fetchall())
            conn.close()
            self.assertEqual(rows, {1: '99', 2: '130'})

    def test_blank_or_invalid_bpm_attribute_is_treated_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'blank-bpm.mldb')
            create_test_db(path)
            conn = sqlite3.connect(path)
            conn.execute("INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (2, 'BPM', '')")
            conn.commit()
            conn.close()

            result = db.apply_bpm_values(path, {'2': 124})
            self.assertEqual(result['written'], 1)
            conn = sqlite3.connect(path)
            value = conn.execute(
                "SELECT value FROM item_attributes WHERE item = 2 AND name = 'BPM'"
            ).fetchone()[0]
            conn.close()
            self.assertEqual(value, '124')

    def test_bpm_scan_prefers_file_tag_and_uses_acousticbrainz_for_remaining_track(self):
        frame = pd.DataFrame([
            {'ID': '1', 'Artist': 'A', 'Title': 'One', 'ItemType': 'Music', 'Filename': 'one.flac', 'Duration': 180, 'ISRC': ''},
            {'ID': '2', 'Artist': 'B', 'Title': 'Two', 'ItemType': 'Music', 'Filename': 'two.flac', 'Duration': 200, 'ISRC': 'DEABC1234567'},
            {'ID': '3', 'Artist': 'C', 'Title': 'Three', 'ItemType': 'Music', 'Filename': 'three.flac', 'Duration': 210, 'ISRC': ''},
        ])
        file_meta = {
            'one.flac': {'path': 'one.flac', 'bpm': 111, 'mbid': ''},
            'two.flac': {'path': None, 'bpm': None, 'mbid': ''},
            'three.flac': {'path': None, 'bpm': None, 'mbid': ''},
        }
        def fake_match(artist, title, isrc='', local_duration_sec=0):
            if artist == 'B':
                return {'mbid': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'matched_by': 'ISRC'}
            return None

        with patch.object(main.utils, 'get_saved_ignored_folders', return_value=[]), \
             patch.object(main.db, 'load_dataframe_from_mldb', return_value=frame), \
             patch.object(main.db, 'get_bpm_flag_state', return_value={}), \
             patch.object(main.db, 'read_audio_bpm_metadata', side_effect=lambda fn, dirs: file_meta[fn]), \
             patch.object(main.api, 'find_musicbrainz_recording_for_bpm', side_effect=fake_match), \
             patch.object(main.api, 'fetch_acousticbrainz_bpms', return_value={
                 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa': {'bpm': 128, 'agree': 2, 'total': 2}
             }):
            proposals, preview, stats = main._scan_bpm_candidates('dummy.mldb', [])

        self.assertEqual(proposals, {'1': 111, '2': 128})
        self.assertEqual(stats['file'], 1)
        self.assertEqual(stats['acousticbrainz'], 1)
        self.assertEqual(stats['nomatch'], 1)
        self.assertEqual(len(preview), 2)


    def test_rekordbox_xml_parser_decodes_path_and_average_bpm(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<DJ_PLAYLISTS Version="1.0.0"><PRODUCT Name="rekordbox" Version="7" Company="AlphaTheta"/>'
            '<COLLECTION Entries="1"><TRACK TrackID="1" Name="Song" Artist="Artist" AverageBpm="128.49" '
            'Location="file://localhost/D:/Musik/Test%20Folder/Artist%20-%20Song.flac"/>'
            '</COLLECTION></DJ_PLAYLISTS>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'rekordbox.xml')
            Path(path).write_text(xml, encoding='utf-8')
            mapping, stats = main._load_rekordbox_bpm_xml(path)
        self.assertEqual(stats['entries'], 1)
        self.assertEqual(stats['valid_bpm'], 1)
        item = next(iter(mapping.values()))
        self.assertEqual(item['bpm'], 128)
        self.assertEqual(item['source_bpm'], 128.49)
        self.assertEqual(item['path'], r'D:\Musik\Test Folder\Artist - Song.flac')

    def test_bpm_scan_prefers_rekordbox_exact_path_before_other_sources(self):
        frame = pd.DataFrame([{
            'ID': '1', 'Artist': 'A', 'Title': 'One', 'ItemType': 'Music',
            'Filename': 'one.flac', 'Duration': 180, 'ISRC': ''
        }])
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<DJ_PLAYLISTS Version="1.0.0"><COLLECTION Entries="1">'
            '<TRACK TrackID="1" Name="One" Artist="A" AverageBpm="121.6" '
            'Location="file://localhost/D:/Music/one.flac"/>'
            '</COLLECTION></DJ_PLAYLISTS>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = os.path.join(tmp, 'rekordbox.xml')
            Path(xml_path).write_text(xml, encoding='utf-8')
            with patch.object(main.utils, 'get_saved_ignored_folders', return_value=[]), \
                 patch.object(main.db, 'load_dataframe_from_mldb', return_value=frame), \
                 patch.object(main.db, 'get_bpm_flag_state', return_value={}), \
                 patch.object(main.db, 'get_resolved_item_paths', return_value={'1': r'D:\Music\one.flac'}), \
                 patch.object(main.db, 'read_audio_bpm_metadata') as tag_reader, \
                 patch.object(main.api, 'find_musicbrainz_recording_for_bpm') as mb_lookup:
                proposals, preview, stats = main._scan_bpm_candidates(
                    'dummy.mldb', [], rekordbox_xml=xml_path
                )
        self.assertEqual(proposals, {'1': 122})
        self.assertEqual(stats['rekordbox'], 1)
        self.assertEqual(preview[0]['matched_by'], 'Dateipfad')
        self.assertEqual(preview[0]['source_bpm'], 121.6)
        tag_reader.assert_not_called()
        mb_lookup.assert_not_called()

    def test_existing_half_double_bpm_is_reviewed_but_not_overwritten(self):
        frame = pd.DataFrame([{
            'ID': '1', 'Artist': 'Band', 'Title': 'Track', 'ItemType': 'Music',
            'Filename': 'track.flac', 'Duration': 180, 'ISRC': ''
        }])
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<DJ_PLAYLISTS Version="1.0.0"><COLLECTION Entries="1">'
            '<TRACK TrackID="1" Name="Track" Artist="Band" AverageBpm="90.00" '
            'Location="file://localhost/D:/Music/track.flac"/>'
            '</COLLECTION></DJ_PLAYLISTS>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = os.path.join(tmp, 'rekordbox.xml')
            Path(xml_path).write_text(xml, encoding='utf-8')
            with patch.object(main.utils, 'DATA_DIR', tmp), \
                 patch.object(main.utils, 'get_saved_ignored_folders', return_value=[]), \
                 patch.object(main.db, 'load_dataframe_from_mldb', return_value=frame), \
                 patch.object(main.db, 'get_bpm_flag_state', return_value={'1': [('BPM', '180')]}), \
                 patch.object(main.db, 'get_resolved_item_paths', return_value={'1': r'D:\Music\track.flac'}):
                proposals, preview, stats = main._scan_bpm_candidates(
                    'dummy.mldb', [], rekordbox_xml=xml_path
                )
            review = pd.read_csv(stats['review_csv'], dtype=str).fillna('')
        self.assertEqual(proposals, {})
        self.assertEqual(preview, [])
        self.assertEqual(stats['rekordbox_conflicts'], 1)
        self.assertEqual(review.loc[0, 'Existing_BPM'], '180')
        self.assertEqual(review.loc[0, 'BPM'], '90')
        self.assertEqual(review.loc[0, 'Status'], 'HALF_DOUBLE_KONFLIKT')

    def test_phase_maintenance_bpm_creates_backup_and_writes_only_after_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'maintenance-bpm.mldb')
            create_test_db(path)
            proposals = {'2': 123}
            preview = [{'id': '2', 'artist': 'Artist Two', 'title': 'Song Two', 'bpm': 123, 'source': 'test'}]
            stats = {'missing': 1, 'existing': 0, 'file': 0, 'acousticbrainz': 1, 'nomatch': 0, 'errors': 0}

            with patch.object(main.console, 'input', side_effect=['6', '', '', 'j']), \
                 patch.object(main, '_scan_bpm_candidates', return_value=(proposals, preview, stats)):
                main.phase_maintenance(path)

            conn = sqlite3.connect(path)
            bpm = conn.execute(
                "SELECT value FROM item_attributes WHERE item = 2 AND LOWER(name) = 'bpm'"
            ).fetchone()
            conn.close()
            self.assertEqual(bpm[0], '123')
            backups = [name for name in os.listdir(tmp) if name.startswith('maintenance-bpm.mldb.backup-')]
            self.assertEqual(len(backups), 1)


class BPMFetchIntegrationTests(unittest.TestCase):
    def _discogs_empty(self):
        return {
            'years': [], 'genre': '', 'discogs_id': '', 'style': '',
            'label': '', 'label_code': '', 'album': '', 'confidence': 'niedrig'
        }

    def test_normal_fetch_uses_rekordbox_bpm_as_proposal(self):
        input_df = pd.DataFrame([{
            'ID': '1', 'Artist': 'Artist One', 'Title': 'Song One', 'ItemType': 'Music',
            'Filename': 'song1.flac', 'Duration': '180', 'TotalDuration': '180',
            'Jahr': '', 'Genre': '', 'Album': '', 'STYLE': '', 'DISCOGS_RELEASE_ID': '',
            'Label': '', 'Labelcode': '', 'ISRC': '', 'Sprache': '', 'Typ': '', 'BPM': '',
            'RESTAURIERT': '', 'DOPPELUNG': ''
        }])
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<DJ_PLAYLISTS Version="1.0.0"><COLLECTION Entries="1">'
            '<TRACK TrackID="1" Name="Song One" Artist="Artist One" AverageBpm="128.49" '
            'Location="file://localhost/D:/Music/song1.flac"/>'
            '</COLLECTION></DJ_PLAYLISTS>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = os.path.join(tmp, 'rekordbox.xml')
            Path(xml_path).write_text(xml, encoding='utf-8')
            fetch_csv = os.path.join(tmp, 'fetch.csv')
            with patch.object(main.db, 'verify_db_compatibility'), \
                 patch.object(main.db, 'is_db_locked', return_value=False), \
                 patch.object(main.utils, 'setup_ignored_folders', return_value=[]), \
                 patch.object(main.db, 'load_dataframe_from_mldb', return_value=input_df), \
                 patch.object(main.db, 'detect_db_language', return_value='de'), \
                 patch.object(main.db, 'get_bpm_flag_state', return_value={}), \
                 patch.object(main.db, 'get_resolved_item_paths', return_value={'1': r'D:\\Music\\song1.flac'}), \
                 patch.object(main.api, 'suggest_artist_spelling', return_value=''), \
                 patch.object(main.api, 'suggest_title_spelling', return_value=''), \
                 patch.object(main.api, 'fetch_musicbrainz_details', return_value=('', 'niedrig', '', '', '')), \
                 patch.object(main.api, 'fetch_discogs_details', return_value=self._discogs_empty()), \
                 patch.object(main.db, 'read_audio_bpm_metadata') as tag_reader, \
                 patch.object(main.api, 'find_musicbrainz_recording_for_bpm') as bpm_mb:
                main.phase_fetch('dummy.mldb', fetch_csv, no_breaks=True, rekordbox_xml=xml_path)
            loaded = pd.read_csv(fetch_csv, dtype=str).fillna('')

        self.assertEqual(loaded.loc[0, 'BPM_Vorschlag'], '128')
        self.assertEqual(loaded.loc[0, 'BPM_Quelle'], 'rekordbox XML')
        self.assertEqual(loaded.loc[0, 'VORSCHLAG_STATUS'], 'FERTIG')
        tag_reader.assert_not_called()
        bpm_mb.assert_not_called()

    def test_normal_fetch_protects_existing_valid_bpm_even_on_full_fetch(self):
        input_df = pd.DataFrame([{
            'ID': '1', 'Artist': 'Artist One', 'Title': 'Song One', 'ItemType': 'Music',
            'Filename': 'song1.flac', 'Duration': '180', 'TotalDuration': '180',
            'Jahr': '', 'Genre': '', 'Album': '', 'STYLE': '', 'DISCOGS_RELEASE_ID': '',
            'Label': '', 'Labelcode': '', 'ISRC': '', 'Sprache': '', 'Typ': '', 'BPM': '90',
            'RESTAURIERT': 'JA', 'DOPPELUNG': ''
        }])
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<DJ_PLAYLISTS Version="1.0.0"><COLLECTION Entries="1">'
            '<TRACK TrackID="1" Name="Song One" Artist="Artist One" AverageBpm="180.00" '
            'Location="file://localhost/D:/Music/song1.flac"/>'
            '</COLLECTION></DJ_PLAYLISTS>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = os.path.join(tmp, 'rekordbox.xml')
            Path(xml_path).write_text(xml, encoding='utf-8')
            fetch_csv = os.path.join(tmp, 'fetch.csv')
            with patch.object(main.db, 'verify_db_compatibility'), \
                 patch.object(main.db, 'is_db_locked', return_value=False), \
                 patch.object(main.utils, 'setup_ignored_folders', return_value=[]), \
                 patch.object(main.db, 'load_dataframe_from_mldb', return_value=input_df), \
                 patch.object(main.db, 'detect_db_language', return_value='de'), \
                 patch.object(main.db, 'get_bpm_flag_state', return_value={'1': [('BPM', '90')]}), \
                 patch.object(main.db, 'get_resolved_item_paths', return_value={'1': r'D:\\Music\\song1.flac'}), \
                 patch.object(main.api, 'suggest_artist_spelling', return_value=''), \
                 patch.object(main.api, 'suggest_title_spelling', return_value=''), \
                 patch.object(main.api, 'fetch_musicbrainz_details', return_value=('', 'niedrig', '', '', '')), \
                 patch.object(main.api, 'fetch_discogs_details', return_value=self._discogs_empty()), \
                 patch.object(main.db, 'read_audio_bpm_metadata') as tag_reader:
                main.phase_fetch('dummy.mldb', fetch_csv, full=True, no_breaks=True, rekordbox_xml=xml_path)
            loaded = pd.read_csv(fetch_csv, dtype=str).fillna('')

        self.assertEqual(loaded.loc[0, 'BPM'], '90')
        self.assertEqual(loaded.loc[0, 'BPM_Vorschlag'], '')
        self.assertEqual(loaded.loc[0, 'FORCE_APPLY'], 'JA')
        tag_reader.assert_not_called()

    def test_apply_dataframe_writes_bpm_attribute(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'bpm-fetch.mldb')
            create_test_db(path)
            frame = pd.DataFrame([{
                'ID': '2', 'Artist': 'Artist Two', 'Title': 'Song Two', 'BPM': '123'
            }])
            db.apply_dataframe_to_mldb(frame, path, mark_restauriert=False)
            conn = sqlite3.connect(path)
            value = conn.execute(
                "SELECT value FROM item_attributes WHERE item = 2 AND name = 'BPM'"
            ).fetchone()
            conn.close()
        self.assertEqual(value[0], '123')

    def test_review_clears_acousticbrainz_bpm_after_manual_identity_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            fetch_csv = os.path.join(tmp, 'fetch.csv')
            final_csv = os.path.join(tmp, 'final.csv')
            frame = pd.DataFrame([{
                'ID': '1', 'Artist': 'Old Artist', 'Title': 'Song',
                'Artist_Vorschlag': 'Old Artist', 'Title_Vorschlag': '',
                'Jahr_Vorschlag': '', 'Jahr_Konfidenz': '',
                'Genre_Vorschlag': '', 'Genre_Konfidenz': '',
                'Album_Vorschlag': '', 'Label_Vorschlag': '',
                'Labelcode_Vorschlag': '', 'ISRC_Vorschlag': '',
                'STYLE_Vorschlag': '', 'DISCOGS_RELEASE_ID_Vorschlag': '',
                'Sprache_Vorschlag': '', 'Typ_Vorschlag': '',
                'BPM_Vorschlag': '128', 'BPM_Quelle': 'AcousticBrainz (2/2)',
                'VORSCHLAG_STATUS': 'FERTIG', 'REVIEW_STATUS': '', 'FORCE_APPLY': '',
                'Duration': '180', 'TotalDuration': '180',
                'Jahr': '', 'Genre': '', 'Album': '', 'Label': '', 'Sprache': '',
                'STYLE': '', 'DISCOGS_RELEASE_ID': '', 'Labelcode': '', 'ISRC': '',
                'Typ': '', 'BPM': '', 'RESTAURIERT': '', 'DOPPELUNG': ''
            }])
            utils.save_safe_csv(frame, fetch_csv)
            with patch.object(main.console, 'input', side_effect=['Correct Artist', '', '', '', '']), \
                 patch.object(main.api, 'fetch_musicbrainz_details', return_value=('', 'niedrig', '', '', '')), \
                 patch.object(main.api, 'fetch_discogs_details', return_value=self._discogs_empty()):
                main.phase_review(fetch_csv, final_csv, auto_hoch=False)
            loaded = pd.read_csv(final_csv, dtype=str).fillna('')
        self.assertEqual(loaded.loc[0, 'Artist'], 'Correct Artist')
        self.assertEqual(loaded.loc[0, 'BPM_Vorschlag'], '')
        self.assertEqual(loaded.loc[0, 'BPM'], '')



class LogicRegressionTests(unittest.TestCase):
    def test_year_outlier_filter(self):
        self.assertEqual(utils.filter_valid_years(['1988', '1988', '2004']), '1988')
        self.assertEqual(utils.filter_valid_years(['1945', '2004', '2005']), '2004')


if __name__ == '__main__':
    unittest.main()


class Version065GenreAndFileBackupTests(unittest.TestCase):
    def test_custom_genre_memory_keeps_rock_pop_shortcuts_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, 'config.json')
            old_config = utils.CONFIG_FILE
            old_custom = list(utils.CUSTOM_GENRES)
            try:
                utils.CONFIG_FILE = config_path
                utils.CUSTOM_GENRES = []
                utils.add_custom_genre('Funk')
                utils.add_custom_genre('rock')  # fixed quick choice; must not duplicate
                mapping = utils.get_genre_quick_map()
                self.assertEqual(mapping['1'], 'Rock')
                self.assertEqual(mapping['2'], 'Pop')
                self.assertIn('Funk', mapping.values())
                with open(config_path, 'r', encoding='utf-8') as handle:
                    import json
                    config = json.load(handle)
                self.assertEqual(config['CUSTOM_GENRES'], ['Funk'])
            finally:
                utils.CONFIG_FILE = old_config
                utils.CUSTOM_GENRES = old_custom

    def test_mairlist_xml_matches_observed_mmd_shape_and_filters_internal_attributes(self):
        item = {
            'title': 'Drop Allgemein 1', 'artist': 'Rainbow Radio', 'type': 'Drop',
            'duration': 11.821, 'amplification': 2.51524408001096,
            'level_peak': -3.948, 'level_truepeak': -3.926, 'level_loudness': -20.515,
        }
        attributes = [
            ('Jahr', '2026'), ('Genre', 'Drop'), ('Sprache', 'Deutsch'),
            ('RESTAURIERT', 'JA'), ('DOPPELUNG', 'JA'), ('LYRICS', 'do not copy'),
        ]
        markers = [
            ('CueIn', 0.068), ('Ramp1', 3.648), ('StartNext', 11.338),
            ('FadeOut', 11.437), ('CueOut', 11.468),
        ]
        xml = db._build_mairlist_xml(item, attributes, markers, declaration=True)
        self.assertTrue(xml.startswith('<?xml version="1.0" encoding="UTF-8"?>'))
        self.assertIn('<Amplification>2,51524408001096</Amplification>', xml)
        self.assertIn('<Duration>11.821</Duration>', xml)
        self.assertIn('<Marker Type="CueIn" Position="0.068"/>', xml)
        self.assertIn('<Marker Type="CueOut" Position="11.468"/>', xml)
        self.assertIn('<Peak>-3.948</Peak>', xml)
        self.assertIn('<TruePeak>-3.926</TruePeak>', xml)
        self.assertIn('<Loudness>-20.515</Loudness>', xml)
        self.assertIn('<Name>Genre</Name><Value>Drop</Value>', xml)
        self.assertIn('<Name>Sprache</Name><Value>Deutsch</Value>', xml)
        self.assertNotIn('RESTAURIERT', xml)
        self.assertNotIn('DOPPELUNG', xml)
        self.assertNotIn('LYRICS', xml)

    @staticmethod
    def _create_tagger_db(path, filename):
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute('CREATE TABLE config (name TEXT PRIMARY KEY, value TEXT)')
        cur.execute("INSERT INTO config(name, value) VALUES ('schemaversion', '25')")
        cur.execute('''CREATE TABLE items (
            idx INTEGER PRIMARY KEY, title TEXT, artist TEXT, type TEXT, filename TEXT,
            duration REAL, amplification REAL, level_peak REAL, level_truepeak REAL,
            level_loudness REAL
        )''')
        cur.execute('''CREATE TABLE item_attributes (
            item INTEGER, name TEXT, value TEXT, PRIMARY KEY(item, name)
        )''')
        cur.execute('''CREATE TABLE item_cuemarkers (
            item INTEGER, type TEXT, value REAL, PRIMARY KEY(item, type)
        )''')
        cur.execute(
            'INSERT INTO items VALUES (1,?,?,?,?,?,?,?,?,?)',
            ('Test Title', 'Test Artist', 'Music', filename, 123.456, 1.25, -4.1, -3.9, -14.2)
        )
        cur.executemany('INSERT INTO item_attributes VALUES (?,?,?)', [
            (1, 'Jahr', '2004'), (1, 'Genre', 'Rock'), (1, 'Album', 'Album'),
            (1, 'Label', 'Label'), (1, 'Sprache', 'Deutsch'), (1, 'BPM', '128'),
            (1, 'ISRC', 'DEABC0400001'), (1, 'RESTAURIERT', 'JA'),
        ])
        cur.executemany('INSERT INTO item_cuemarkers VALUES (?,?,?)', [
            (1, 'CueIn', 0.125), (1, 'Ramp1', 12.5), (1, 'StartNext', 120.1),
            (1, 'FadeOut', 121.2), (1, 'CueOut', 122.9),
        ])
        conn.commit()
        conn.close()

    def test_full_tagger_writes_flac_portable_tags_and_mmd_sidecar(self):
        class FLAC(dict):
            def save(self):
                self.saved = True

        with tempfile.TemporaryDirectory() as tmp:
            media = os.path.join(tmp, 'song.flac')
            Path(media).write_bytes(b'placeholder')
            db_path = os.path.join(tmp, 'test.mldb')
            self._create_tagger_db(db_path, media)
            fake_audio = FLAC()
            fake_audio.saved = False
            with patch('mutagen.File', return_value=fake_audio):
                count = db.run_maintenance_file_tagger(db_path, metadata_mode=2, base_dirs=[])
            self.assertEqual(count, 1)
            self.assertEqual(fake_audio['artist'], ['Test Artist'])
            self.assertEqual(fake_audio['genre'], ['Rock'])
            self.assertEqual(fake_audio['language'], ['Deutsch'])
            self.assertEqual(fake_audio['bpm'], ['128'])
            self.assertEqual(fake_audio['isrc'], ['DEABC0400001'])
            self.assertTrue(fake_audio.saved)
            sidecar = media + '.mmd'
            self.assertTrue(os.path.exists(sidecar))
            text = Path(sidecar).read_text(encoding='utf-8')
            self.assertIn('<Duration>123.456</Duration>', text)
            self.assertIn('<Marker Type="Ramp1" Position="12.500"/>', text)
            self.assertIn('<Loudness>-14.200</Loudness>', text)
            self.assertNotIn('RESTAURIERT', text)

    def test_full_tagger_embeds_only_mairlist_txxx_and_preserves_other_id3(self):
        from mutagen.id3 import ID3, TXXX

        class MP3:
            def __init__(self):
                self.tags = ID3()
                self.tags.add(TXXX(encoding=3, desc='KeepMe', text=['foreign']))
                self.saved = False
            def save(self):
                self.saved = True
            def add_tags(self):
                if self.tags is None:
                    self.tags = ID3()

        with tempfile.TemporaryDirectory() as tmp:
            media = os.path.join(tmp, 'song.mp3')
            Path(media).write_bytes(b'placeholder')
            db_path = os.path.join(tmp, 'test.mldb')
            self._create_tagger_db(db_path, media)
            fake_audio = MP3()
            with patch('mutagen.File', return_value=fake_audio):
                count = db.run_maintenance_file_tagger(db_path, metadata_mode='full', base_dirs=[])
            self.assertEqual(count, 1)
            self.assertTrue(fake_audio.saved)
            self.assertEqual(fake_audio.tags['TXXX:KeepMe'].text, ['foreign'])
            m = fake_audio.tags['TXXX:mAirList']
            self.assertIn('<Marker Type="CueIn" Position="0.125"/>', m.text[0])
            self.assertIn('<Amplification>1,25</Amplification>', m.text[0])
            self.assertEqual(str(fake_audio.tags['TLAN'].text[0]), 'Deutsch')
            self.assertEqual(str(fake_audio.tags['TBPM'].text[0]), '128')
            self.assertEqual(str(fake_audio.tags['TSRC'].text[0]), 'DEABC0400001')

class Version066SpeedAndStartupTests(unittest.TestCase):
    def test_speed_group_boundaries_are_exact(self):
        self.assertEqual(db.speed_group_for_bpm('100'), 'Langsam')
        self.assertEqual(db.speed_group_for_bpm('100.1'), 'Medium')
        self.assertEqual(db.speed_group_for_bpm('129.9'), 'Medium')
        self.assertEqual(db.speed_group_for_bpm('130'), 'Schnell')
        self.assertEqual(db.speed_group_for_bpm('181'), 'Schnell')
        self.assertIsNone(db.speed_group_for_bpm('n/a'))

    def test_speed_scan_only_proposes_missing_classifications(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'speed.mldb')
            rows = [
                (1, 'Slow', 'A', 'Music', '1.flac', 100.0, 100.0),
                (2, 'Manual', 'B', 'Music', '2.flac', 100.0, 100.0),
                (3, 'Medium', 'C', 'Music', '3.flac', 100.0, 100.0),
                (4, 'Fast', 'D', 'Music', '4.flac', 100.0, 100.0),
            ]
            create_test_db(path, rows=rows)
            conn = sqlite3.connect(path)
            conn.executemany(
                'INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (?, ?, ?)',
                [(1, 'BPM', '100'), (2, 'BPM', '181'), (3, 'BPM', '129'), (4, 'BPM', '130')]
            )
            conn.execute(
                "INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (2, 'Geschwindigkeit', 'Medium')"
            )
            conn.commit()
            conn.close()

            proposals, stats = db.scan_speed_group_candidates(path)
            self.assertEqual(proposals, {'1': 'Langsam', '3': 'Medium', '4': 'Schnell'})
            self.assertEqual(stats['with_bpm'], 4)
            self.assertEqual(stats['existing'], 1)
            self.assertEqual(stats['candidates'], 3)
            self.assertEqual((stats['slow'], stats['medium'], stats['fast']), (1, 1, 1))

    def test_speed_apply_rechecks_and_never_overwrites_existing_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'speed.mldb')
            create_test_db(path)
            conn = sqlite3.connect(path)
            conn.executemany(
                'INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (?, ?, ?)',
                [(1, 'BPM', '95'), (2, 'BPM', '140')]
            )
            conn.execute(
                "INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (2, 'Geschwindigkeit', 'Medium')"
            )
            conn.commit()
            conn.close()

            result = db.apply_speed_groups(path, {'1': 'Langsam', '2': 'Schnell'})
            self.assertEqual(result['written'], 1)
            self.assertEqual(result['skipped_existing'], 1)
            conn = sqlite3.connect(path)
            values = dict(conn.execute(
                "SELECT item, value FROM item_attributes WHERE LOWER(name) = 'geschwindigkeit' ORDER BY item"
            ).fetchall())
            conn.close()
            self.assertEqual(values[1], 'Langsam')
            self.assertEqual(values[2], 'Medium')

    def test_database_and_source_folders_persist_without_losing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, 'config.json')
            db_path = os.path.join(tmp, 'Automation.mldb')
            source_a = os.path.join(tmp, 'Music')
            source_b = os.path.join(tmp, 'More Music')
            os.makedirs(source_a)
            os.makedirs(source_b)
            old_config = utils.CONFIG_FILE
            try:
                utils.CONFIG_FILE = config_path
                Path(config_path).write_text('{"LANG":"de","CUSTOM_GENRES":["Funk"]}', encoding='utf-8')
                utils.save_database_context(db_path)
                saved = utils.save_source_folders(db_path, [source_a, source_a, source_b])
                self.assertEqual(saved, [os.path.abspath(source_a), os.path.abspath(source_b)])
                self.assertEqual(utils.get_last_database(), os.path.abspath(db_path))
                self.assertEqual(utils.get_saved_source_folders(db_path), saved)
                import json
                config = json.loads(Path(config_path).read_text(encoding='utf-8'))
                self.assertEqual(config['LANG'], 'de')
                self.assertEqual(config['CUSTOM_GENRES'], ['Funk'])
            finally:
                utils.CONFIG_FILE = old_config

    def test_activate_database_saves_last_database_and_prepares_session_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, 'Automation.mldb')
            Path(db_path).write_bytes(b'dummy')
            with patch.object(main.db, 'verify_db_compatibility', return_value=25), \
                 patch.object(main.utils, 'save_database_context') as save_context, \
                 patch.object(main, 'setup_logging', return_value=('Automation_deadbeef', tmp)):
                active = main._activate_database(db_path)
            self.assertEqual(active[0], os.path.abspath(db_path))
            self.assertTrue(active[1].endswith('Automation_deadbeef_vorschlaege.csv'))
            self.assertTrue(active[2].endswith('Automation_deadbeef_restauriert.csv'))
            save_context.assert_called_once_with(os.path.abspath(db_path))

class Version066SpeedMaintenanceIntegrationTests(unittest.TestCase):
    def test_speed_maintenance_creates_backup_and_only_fills_missing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'speed-maintenance.mldb')
            rows = [
                (1, 'Slow', 'A', 'Music', '1.flac', 100.0, 100.0),
                (2, 'Protected', 'B', 'Music', '2.flac', 100.0, 100.0),
                (3, 'Fast', 'C', 'Music', '3.flac', 100.0, 100.0),
            ]
            create_test_db(path, rows=rows)
            conn = sqlite3.connect(path)
            conn.executemany(
                'INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (?, ?, ?)',
                [(1, 'BPM', '100'), (2, 'BPM', '145'), (3, 'BPM', '130')]
            )
            conn.execute(
                "INSERT OR REPLACE INTO item_attributes(item, name, value) VALUES (2, 'Geschwindigkeit', 'Medium')"
            )
            conn.commit()
            conn.close()

            with patch.object(main.console, 'input', side_effect=['7', 'j']):
                main.phase_maintenance(path)

            conn = sqlite3.connect(path)
            values = dict(conn.execute(
                "SELECT item, value FROM item_attributes WHERE LOWER(name) = 'geschwindigkeit' ORDER BY item"
            ).fetchall())
            conn.close()
            self.assertEqual(values, {1: 'Langsam', 2: 'Medium', 3: 'Schnell'})
            backups = [name for name in os.listdir(tmp) if name.startswith('speed-maintenance.mldb.backup-')]
            self.assertEqual(len(backups), 1)
            ok, details = db.check_integrity(path)
            self.assertTrue(ok, details)

class Version066ConfigMigrationTests(unittest.TestCase):
    def test_last_database_can_be_inferred_from_single_legacy_database_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, 'config.json')
            db_path = os.path.join(tmp, 'Automation.mldb')
            old_config = utils.CONFIG_FILE
            try:
                utils.CONFIG_FILE = config_path
                import json
                Path(config_path).write_text(json.dumps({
                    'DB_REKORDBOX_XML': {db_path: os.path.join(tmp, 'rekordbox.xml')},
                    'DB_IGNORES': {db_path: ['OAD']},
                }), encoding='utf-8')
                self.assertEqual(utils.get_last_database(), db_path)
            finally:
                utils.CONFIG_FILE = old_config
