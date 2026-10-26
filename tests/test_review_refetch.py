import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import api
import main
import utils


class ReviewRefetchTests(unittest.TestCase):
    def check_outage(self, mb_failed, discogs_failed):
        proposals = {
            'Artist_Vorschlag': '', 'Title_Vorschlag': '',
            'Jahr_Vorschlag': '1997', 'Jahr_Konfidenz': 'mittel',
            'Album_Vorschlag': 'Compilation',
            'Genre_Vorschlag': 'Pop', 'Genre_Konfidenz': 'mittel',
            'Label_Vorschlag': 'Old label', 'Labelcode_Vorschlag': '123',
            'STYLE_Vorschlag': 'Old style', 'DISCOGS_RELEASE_ID_Vorschlag': '456',
            'ISRC_Vorschlag': 'OLD123', 'Sprache_Vorschlag': 'Englisch',
            'BPM_Vorschlag': '128', 'BPM_Quelle': 'AcousticBrainz (2/2)',
            'Typ_Vorschlag': '',
        }
        row = dict.fromkeys(utils.MLDB_ATTRIBUTE_FIELDS, '')
        row.update(proposals)
        row.update(ID='1', Artist='Electric Light Orchestra', Title="Don't Bring Me Down",
                   Jahr='1979', Album='Original album', Duration='180',
                   VORSCHLAG_STATUS='FERTIG', REVIEW_STATUS='')
        next_row = dict(row, ID='2')
        discogs = dict(genre='Rock', confidence='hoch', label='New label',
                       label_code='789', style='New style', discogs_id='987')
        mb_error = api.APIRequestError('HTTP 503', service='MusicBrainz', kind='server')
        discogs_error = api.APIRequestError('HTTP 503', service='Discogs', kind='server')
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'fetch.csv', Path(tmp) / 'final.csv'
            utils.save_safe_csv(pd.DataFrame([row, next_row]), source)
            with patch.object(utils, 'CURRENT_LANG', 'de'), \
                 patch.object(main.console, 'input', side_effect=[
                     '1979', 'o', '', '', '',  # manual year; retain original album
                     'o', 'o', '', '', '',    # next track must still be reviewed
                 ]), \
                 patch.object(main.console, 'print') as output, \
                 patch.object(api, 'fetch_musicbrainz_details',
                              side_effect=mb_error if mb_failed else None,
                              return_value=('1980', 'hoch', 'NEW123', 'API album', 'Deutsch')) as mb, \
                 patch.object(api, 'fetch_discogs_details',
                              side_effect=discogs_error if discogs_failed else None,
                              return_value=discogs) as dg:
                main.phase_review(source, target)
            result = pd.read_csv(target, dtype=str).fillna('')
        mb.assert_called_once()
        dg.assert_called_once()
        self.assertEqual(result['REVIEW_STATUS'].tolist(), ['JA', 'JA'])
        self.assertEqual(result.loc[0, 'Jahr'], '1979')
        self.assertEqual(result.loc[0, 'Album'], 'Original album')
        for field, key in [('Genre', 'genre'), ('Label', 'label'), ('Labelcode', 'label_code'),
                           ('STYLE', 'style'), ('DISCOGS_RELEASE_ID', 'discogs_id')]:
            expected = proposals[field + '_Vorschlag'] if discogs_failed else discogs[key]
            self.assertEqual(result.loc[0, field + '_Vorschlag'], expected)
            self.assertEqual(result.loc[0, field], expected)
        self.assertEqual(result.loc[0, 'Genre_Konfidenz'], 'mittel' if discogs_failed else 'hoch')
        for field, value in [('ISRC', 'NEW123'), ('Sprache', 'Deutsch')]:
            expected = proposals[field + '_Vorschlag'] if mb_failed else value
            self.assertEqual(result.loc[0, field + '_Vorschlag'], expected)
            self.assertEqual(result.loc[0, field], expected)
        if mb_failed and discogs_failed:
            for field, value in proposals.items():
                self.assertEqual(result.loc[0, field], value, field)
        warnings = [str(call.args[0]) for call in output.call_args_list
                    if call.args and 'Live-Re-Fetch fehlgeschlagen' in str(call.args[0])]
        self.assertEqual(len(warnings), int(mb_failed) + int(discogs_failed))
        for service, failed in [('MusicBrainz', mb_failed), ('Discogs', discogs_failed)]:
            self.assertEqual(any(service in warning for warning in warnings), failed)
        self.assertTrue(any('Manuelle Änderung erkannt' in str(call) for call in output.call_args_list))

    def test_musicbrainz_outage_keeps_discogs_results(self):
        self.check_outage(True, False)

    def test_discogs_outage_keeps_musicbrainz_results(self):
        self.check_outage(False, True)

    def test_both_outages_preserve_all_proposals(self):
        self.check_outage(True, True)
