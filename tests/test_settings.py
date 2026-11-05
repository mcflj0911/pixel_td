import json
import os
import tempfile
import unittest

import display
from config import SPEEDS, BASIC_PER_ROUND
from settings import (DEFAULTS, TEXT_SCALES, best_round, load_records, load_settings, record_round,
                      save_records, save_settings)
from waves import preview


class SettingsFileTests(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "settings.json")

    def tearDown(self):
        self.folder.cleanup()

    def test_missing_file_gives_the_defaults(self):
        self.assertEqual(load_settings(self.path), DEFAULTS)

    def test_damaged_file_gives_the_defaults(self):
        with open(self.path, "w") as f:
            f.write("{nope")
        self.assertEqual(load_settings(self.path), DEFAULTS)

    def test_settings_round_trip(self):
        settings = dict(DEFAULTS, volume=0.4, muted=True, difficulty="Hard", map=3, slot=2,
                        text_scale="Large", fullscreen=True, skip_briefing=True)
        self.assertTrue(save_settings(settings, self.path))
        self.assertEqual(load_settings(self.path), settings)

    def test_wrong_types_and_unknown_values_are_replaced(self):
        with open(self.path, "w") as f:
            json.dump({"volume": "loud", "difficulty": "Impossible", "text_scale": "Huge", "map": 99,
                       "slot": 0, "muted": 1, "skip_briefing": "yes"}, f)
        settings = load_settings(self.path)
        self.assertEqual(settings["volume"], DEFAULTS["volume"])
        self.assertEqual(settings["difficulty"], DEFAULTS["difficulty"])
        self.assertEqual(settings["text_scale"], DEFAULTS["text_scale"])
        self.assertEqual(settings["map"], 5)
        self.assertEqual(settings["slot"], 1)
        self.assertEqual(settings["muted"], DEFAULTS["muted"])  # 1 is not a bool
        self.assertEqual(settings["skip_briefing"], DEFAULTS["skip_briefing"])

    def test_volume_is_clamped(self):
        with open(self.path, "w") as f:
            json.dump({"volume": 7.5}, f)
        self.assertEqual(load_settings(self.path)["volume"], 1.0)


class RecordsTests(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "records.json")

    def tearDown(self):
        self.folder.cleanup()

    def test_only_a_better_round_counts_as_a_record(self):
        records = {}
        self.assertTrue(record_round(records, "human", "Normal", 8))
        self.assertFalse(record_round(records, "human", "Normal", 5))
        self.assertTrue(record_round(records, "human", "Normal", 9))
        self.assertEqual(best_round(records, "human", "Normal"), 9)

    def test_each_faction_and_difficulty_keeps_its_own_best(self):
        records = {}
        record_round(records, "human", "Normal", 9)
        record_round(records, "zombie", "Normal", 4)
        record_round(records, "human", "Hard", 2)
        self.assertEqual(best_round(records, "human", "Normal"), 9)
        self.assertEqual(best_round(records, "zombie", "Normal"), 4)
        self.assertEqual(best_round(records, "human", "Hard"), 2)
        self.assertEqual(best_round(records, "zombie", "Hard"), 0)

    def test_records_round_trip_and_ignore_damage(self):
        records = {"human:Normal": 7}
        save_records(records, self.path)
        self.assertEqual(load_records(self.path), records)
        with open(self.path, "w") as f:
            json.dump({"human:Normal": "seven", "zombie:Normal": True, "ok": 3}, f)
        self.assertEqual(load_records(self.path), {"ok": 3})


class DisplayTests(unittest.TestCase):

    def test_canvas_keeps_its_proportions_and_is_centred(self):
        x, y, w, h = display.fit(1920, 1080, 1000, 720)
        self.assertEqual(h, 1080)
        self.assertAlmostEqual(w / h, 1000 / 720, places=2)
        self.assertEqual(x, (1920 - w) // 2)
        self.assertEqual(y, 0)

    def test_a_window_of_the_same_shape_fills_it(self):
        self.assertEqual(display.fit(1000, 720, 1000, 720), (0, 0, 1000, 720))

    def test_window_clicks_map_back_onto_the_canvas(self):
        dest = display.fit(2000, 1440, 1000, 720)  # Exactly twice the size
        self.assertEqual(display.to_canvas((dest[0] + 200, dest[1] + 100), dest, 1000, 720), (100, 50))

    def test_clicks_in_the_black_bars_fall_outside_the_canvas(self):
        dest = display.fit(1920, 1080, 1000, 720)
        cx, cy = display.to_canvas((2, 2), dest, 1000, 720)
        self.assertTrue(cx < 0 or cy < 0)


class TextScaleTests(unittest.TestCase):

    def test_text_scales_go_small_normal_large(self):
        self.assertEqual(list(TEXT_SCALES), ["Small", "Normal", "Large"])
        self.assertEqual(TEXT_SCALES["Normal"], 1.0)


class SessionOptionTests(unittest.TestCase):

    def test_speed_key_cycles_through_one_to_four(self):
        self.assertEqual(SPEEDS, (1, 2, 3, 4))

    def test_basic_enemies_grow_by_the_configured_amount_each_round(self):
        self.assertEqual(preview("zombie", 11)["walker"], 4 + BASIC_PER_ROUND * 11)


if __name__ == "__main__":
    unittest.main()
