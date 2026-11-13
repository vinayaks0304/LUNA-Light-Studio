"""Theme calculations remain testable without a GUI or Bluetooth device."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrstar.theme import contrast_ratio, stylesheet, theme_for_colour


class AdaptiveThemeTests(unittest.TestCase):
    def test_selected_hex_is_preserved_and_accents_follow_hue(self):
        for colour in ('#FF2255', '#0000FF', '#00FF00', '#FFE100', '#AB31E4'):
            with self.subTest(colour=colour):
                t = theme_for_colour(colour)
                self.assertEqual(t.selected, colour)
                self.assertGreaterEqual(contrast_ratio(t.accent, t.background), 4.5)
                self.assertGreaterEqual(contrast_ratio(t.on_accent, t.accent), 4.5)
                self.assertGreaterEqual(contrast_ratio(t.on_accent_hover, t.accent_hover), 4.5)
        self.assertNotEqual(theme_for_colour('#FF2255').accent,
                            theme_for_colour('#0000FF').accent)

    def test_greyscale_and_extreme_colours_are_readable(self):
        for colour in ('#000000', '#010101', '#FFFFFF', '#888888', '#001020', '#FFFF00'):
            with self.subTest(colour=colour):
                t = theme_for_colour(colour)
                self.assertGreaterEqual(contrast_ratio(t.accent, t.background), 4.5)
                self.assertGreaterEqual(contrast_ratio(t.on_accent, t.accent), 4.5)
                self.assertGreaterEqual(contrast_ratio(t.on_accent_hover, t.accent_hover), 4.5)
        self.assertNotEqual(theme_for_colour('#FFFFFF').accent,
                            theme_for_colour('#9568FF').accent)

    def test_stylesheet_uses_derived_colour_in_all_major_controls(self):
        t = theme_for_colour('#FF8A00')
        qss = stylesheet(t)
        self.assertIn('QPushButton#primary', qss)
        self.assertIn('QPushButton#nav[active=', qss)
        self.assertIn('QSlider::sub-page:horizontal', qss)
        self.assertIn('QFrame#themeChip', qss)
        self.assertIn(t.accent, qss)
        self.assertIn(t.selected, qss)
        self.assertNotIn('#8461e8', qss.lower())

    def test_invalid_colour_falls_back_to_default(self):
        self.assertEqual(theme_for_colour('invalid').selected, '#9568FF')
        self.assertEqual(theme_for_colour('#000000').selected, '#000000')


if __name__ == '__main__':
    unittest.main()
