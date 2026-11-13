import sys
from pathlib import Path
import unittest
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrstar import protocol
from mrstar.effects import EFFECTS, EFFECT_IDS


class ProtocolTests(unittest.TestCase):
    def test_power_fix_exact_packets(self):
        self.assertEqual(protocol.power_frame(True), bytes.fromhex('BC 01 01 01 55'))
        self.assertEqual(protocol.power_frame(False), bytes.fromhex('BC 01 01 00 55'))

    def test_colour_and_brightness_preserved(self):
        self.assertEqual(protocol.colour_frame('#FF0000'), bytes.fromhex('BC 04 06 00 00 03 E8 00 00 55'))
        self.assertEqual(protocol.microphone_colour_frame('#FF0000'), bytes.fromhex('BC 09 06 00 00 03 E8 00 00 55'))
        self.assertEqual(protocol.brightness_frame(800), bytes.fromhex('BC 05 06 03 20 00 00 00 00 55'))
        self.assertEqual(protocol.pixel_count_frame(150), bytes.fromhex('BC 03 02 00 96 55'))
        self.assertEqual(protocol.channel_order_frame(0), bytes.fromhex('BC 02 01 01 55'))
        self.assertEqual(protocol.channel_order_frame(5), bytes.fromhex('BC 02 01 06 55'))

    def test_58_effects_and_ids(self):
        self.assertEqual(len(EFFECTS), 58)
        self.assertEqual(len({e.id for e in EFFECTS}), 58)
        self.assertEqual([len(v) for v in EFFECT_IDS.values()], [12,10,10,8,8,10])
        self.assertEqual(protocol.effect_frame(55), bytes.fromhex('BC 06 02 00 37 55'))
        self.assertEqual(protocol.effect_frame(56), bytes.fromhex('BC 06 02 00 38 55'))
        self.assertEqual(protocol.effect_frame(93), bytes.fromhex('BC 06 02 00 5D 55'))
        self.assertEqual(protocol.effect_speed_frame(50), bytes.fromhex('BC 08 01 32 55'))
        self.assertEqual(protocol.effect_direction_frame(True), bytes.fromhex('BC 07 01 00 55'))
        self.assertEqual(protocol.effect_direction_frame(False), bytes.fromhex('BC 07 01 01 55'))

    def test_microphone(self):
        self.assertEqual(protocol.microphone_source_frame(True), bytes.fromhex('BC 0F 01 01 55'))
        self.assertEqual(protocol.microphone_source_frame(False), bytes.fromhex('BC 0F 01 00 55'))
        self.assertEqual(protocol.microphone_mode_frame('Disco'), bytes.fromhex('BC 11 01 04 55'))
        self.assertEqual(protocol.microphone_sensitivity_frame(100), bytes.fromhex('BC 12 01 64 55'))

    def test_timer_clock_and_schedule(self):
        t = datetime(2026,11,13,23,7,8)
        self.assertEqual(protocol.clock_frame(t), bytes.fromhex('BC 0B 07 07 EA 0B 0D 17 07 08 55 05'))
        self.assertEqual(protocol.timer_read_frame(), bytes.fromhex('BC 0C 01 01 55'))
        days = [True, False, True, False, True, False, False]
        self.assertEqual(protocol.timer_frame('on', True, days, 7, 30),
                         bytes.fromhex('BC 0D 06 01 01 01 15 07 1E 55'))
        self.assertEqual(protocol.timer_frame('off', False, days, 23, 0),
                         bytes.fromhex('BC 0D 06 01 00 00 95 17 00 55'))
        result = protocol.parse_timer_notification(bytes.fromhex('BC 0D 06 01 01 01 15 07 1E 55'))
        self.assertEqual(result.kind, 'on')
        self.assertTrue(result.enabled)
        self.assertEqual(result.weekdays, tuple(days))
        self.assertEqual((result.hour, result.minute), (7,30))
        self.assertIsNone(protocol.parse_timer_notification(bytes.fromhex('BC 06 02 00 37 55')))
        self.assertIsNone(protocol.parse_timer_notification(bytes.fromhex('BC 0D 06 01 01 01 15 25 1E 55')))


if __name__ == '__main__':
    unittest.main()
