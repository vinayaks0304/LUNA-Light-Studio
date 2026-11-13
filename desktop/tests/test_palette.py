"""Saved-colour persistence tests (no Qt, BLE, or hardware required)."""
import json
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrstar.palette import clean_name, dump_palette, load_palette, normalise_hex


class PaletteTests(unittest.TestCase):
    def test_round_trip_preserves_names_and_colours(self):
        saved = [
            {'name': 'Evening blue', 'hex': '#1769FF'},
            {'name': 'Soft pink', 'hex': '#ff80bb'},
            {'name': 'Café light', 'hex': 'F0AA21'},
        ]
        encoded = dump_palette(saved)
        self.assertEqual(load_palette(encoded), [
            {'name': 'Evening blue', 'hex': '#1769FF'},
            {'name': 'Soft pink', 'hex': '#FF80BB'},
            {'name': 'Café light', 'hex': '#F0AA21'},
        ])
        self.assertEqual(json.loads(encoded)[0]['name'], 'Evening blue')

    def test_corrupt_settings_are_ignored(self):
        for raw in ('', 'not JSON', 'null', '{}', 'true', '42', None, []):
            with self.subTest(raw=raw):
                self.assertEqual(load_palette(raw), [])

    def test_invalid_and_duplicate_colours_are_ignored(self):
        raw = json.dumps([
            {'name': 'first', 'hex': '#abc123'},
            {'name': 'duplicate', 'hex': 'ABC123'},
            {'name': 'bad', 'hex': '#12345Z'},
            {'name': 'not hex', 'hex': 'red'},
            'wrong type',
            {'name': 'last', 'hex': '#001122'},
        ])
        self.assertEqual(load_palette(raw), [
            {'name': 'first', 'hex': '#ABC123'},
            {'name': 'last', 'hex': '#001122'},
        ])

    def test_names_are_cleaned_without_losing_unicode(self):
        self.assertEqual(clean_name('  My   purple\n  lights  ', 'fallback'), 'My purple lights')
        self.assertEqual(clean_name('  ', '#FFFFFF'), '#FFFFFF')
        self.assertEqual(clean_name('é' * 100, '#FFFFFF'), 'é' * 36)

    def test_strict_hex_validation(self):
        self.assertEqual(normalise_hex('#ff0099'), '#FF0099')
        self.assertEqual(normalise_hex('00AACC'), '#00AACC')
        for invalid in ('#FFF', '#11223344', '#XXYYZZ', ' #112233 ', 42, None):
            with self.subTest(invalid=invalid):
                self.assertIsNone(normalise_hex(invalid))

    def test_delete_and_rename_serialisation(self):
        palette = load_palette(dump_palette([
            {'name': 'Pink', 'hex': '#FF0088'},
            {'name': 'Blue', 'hex': '#0055FF'},
        ]))
        palette[1]['name'] = 'Midnight blue'
        palette.pop(0)
        self.assertEqual(load_palette(dump_palette(palette)),
                         [{'name': 'Midnight blue', 'hex': '#0055FF'}])


if __name__ == '__main__':
    unittest.main()
