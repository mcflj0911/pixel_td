import json
import os
import tempfile
import unittest
from unittest import mock

from game import Game
from save import SAVE_VERSION, read_save, save_path, write_save
from units import Unit


class SaveFileTests(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "slot.json")

    def tearDown(self):
        self.folder.cleanup()

    def test_successful_write_leaves_no_temp_file(self):
        self.assertEqual(write_save(self.path, {"version": SAVE_VERSION}), (True, "Game saved"))
        self.assertTrue(os.path.exists(self.path))
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_failed_write_keeps_the_previous_save(self):
        write_save(self.path, {"version": SAVE_VERSION, "wave": 3})
        with mock.patch("save.os.replace", side_effect=OSError("disk full")):
            ok, message = write_save(self.path, {"version": SAVE_VERSION, "wave": 9})
        self.assertFalse(ok)
        self.assertTrue(message.startswith("Could not save: "), message)
        self.assertIn("F5", message)
        data, reason = read_save(self.path)
        self.assertIsNone(reason)
        self.assertEqual(data["wave"], 3)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_missing_file_is_empty(self):
        self.assertEqual(read_save(self.path), (None, "empty"))

    def test_garbage_file_is_unreadable(self):
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertEqual(read_save(self.path), (None, "unreadable"))

    def test_other_version_is_incompatible(self):
        with open(self.path, "w") as f:
            json.dump({"version": SAVE_VERSION + 1, "wave": 2}, f)
        self.assertEqual(read_save(self.path), (None, "incompatible"))

    def test_load_slot_reports_the_reason(self):
        with open(self.path, "w") as f:
            json.dump({"version": SAVE_VERSION + 1}, f)
        game, reason = Game.load_slot(self.path)
        self.assertIsNone(game)
        self.assertEqual(reason, "incompatible")

    def test_load_slot_reports_missing_file_as_empty(self):
        self.assertEqual(Game.load_slot(self.path), (None, "empty"))

    def test_save_path_is_per_slot(self):
        self.assertNotEqual(save_path(1), save_path(2))
        self.assertTrue(save_path(3).endswith(".json"))


class UnitStatsCacheTests(unittest.TestCase):

    def test_stats_are_reused_while_nothing_changes(self):
        unit = Unit("human", "rapid", 1.5, 1.5)
        self.assertIs(unit.stats, unit.stats)

    def test_level_up_refreshes_the_stats(self):
        unit = Unit("human", "rapid", 1.5, 1.5)
        before = unit.stats["damage"]
        unit.level = 2
        self.assertGreater(unit.stats["damage"], before)

    def test_group_size_refreshes_the_stats(self):
        unit = Unit("human", "rapid", 1.5, 1.5)
        alone = unit.stats["damage"]
        unit.group = 3
        self.assertGreater(unit.stats["damage"], alone)

    def test_an_older_stats_copy_is_not_changed_by_an_upgrade(self):
        unit = Unit("human", "rapid", 1.5, 1.5)
        snapshot = unit.stats
        damage_before = snapshot["damage"]
        unit.level = 3
        self.assertEqual(snapshot["damage"], damage_before)


if __name__ == "__main__":
    unittest.main()
