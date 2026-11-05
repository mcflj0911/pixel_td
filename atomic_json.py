"""Small JSON file helpers shared by the save files and the settings and records files.

Writes go to a temporary file that then replaces the target, so a crash or a full disk in the middle of a write
leaves the previous file intact. Reads never raise: a missing or damaged file gives None.
"""
import json
import os


def write_json_atomic(path, data):
    """Write `data` to `path`. Returns True on success, False if the disk refused."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    return True


def read_json(path):
    """The parsed JSON value in `path`, or None if the file is missing, unreadable or not valid JSON."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None
