import errno
import os
import tempfile
import unittest
from unittest import mock

from atomic_json import describe_error, write_json_checked
from paths import data_dir, migrate_saves


class DataFolderTests(unittest.TestCase):
    def setUp(self):
        self.old = tempfile.TemporaryDirectory()
        self.new = tempfile.TemporaryDirectory()
        self.addCleanup(self.old.cleanup)
        self.addCleanup(self.new.cleanup)

    def write(self, folder, name, text="{}"):
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write(text)

    def test_the_override_folder_is_used(self):
        with mock.patch.dict(os.environ, {"PIXEL_TD_DATA": self.new.name}):
            self.assertEqual(data_dir(), self.new.name)

    def test_old_saves_are_copied_once_and_never_overwrite(self):
        self.write(self.old.name, "savegame_1.json", "old slot")
        self.write(self.old.name, "settings.json", "old settings")
        self.write(self.new.name, "settings.json", "new settings")
        copied = migrate_saves(self.old.name, self.new.name)
        self.assertEqual(copied, ["savegame_1.json"])
        with open(os.path.join(self.new.name, "settings.json"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "new settings")
        self.assertEqual(migrate_saves(self.old.name, self.new.name), [])  # Second time: nothing to do


class WriteErrorTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = os.path.join(self.folder.name, "data.json")

    def test_a_locked_file_is_explained(self):
        with mock.patch("atomic_json.os.replace", side_effect=PermissionError("locked")):
            self.assertEqual(write_json_checked(self.path, {}), "another program is using the file")

    def test_a_full_disk_is_explained(self):
        err = OSError(errno.ENOSPC, "no space")
        self.assertEqual(describe_error(err), "the disk is full")

    def test_a_successful_write_returns_none(self):
        self.assertIsNone(write_json_checked(self.path, {"a": 1}))


if __name__ == "__main__":
    unittest.main()
