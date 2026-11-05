import os
import tempfile
import unittest
from unittest import mock

from atomic_json import read_json, write_json_atomic


class AtomicJsonTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = os.path.join(self.folder.name, "data.json")

    def test_round_trip_keeps_non_ascii_text(self):
        self.assertTrue(write_json_atomic(self.path, {"name": "Zombie ümlaut"}))
        self.assertEqual(read_json(self.path), {"name": "Zombie ümlaut"})

    def test_missing_or_damaged_file_reads_as_none(self):
        self.assertIsNone(read_json(self.path))
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertIsNone(read_json(self.path))

    def test_a_refused_write_reports_false_and_keeps_the_old_file(self):
        write_json_atomic(self.path, {"v": 1})
        with mock.patch("atomic_json.os.replace", side_effect=OSError("disk full")):
            self.assertFalse(write_json_atomic(self.path, {"v": 2}))
        self.assertEqual(read_json(self.path), {"v": 1})
        self.assertFalse(os.path.exists(self.path + ".tmp"))


if __name__ == "__main__":
    unittest.main()
