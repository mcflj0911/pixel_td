"""Small JSON file helpers shared by the save files and the settings and records files.

Writes go to a temporary file that then replaces the target, so a crash or a full disk in the middle of a write
leaves the previous file intact. Reads never raise: a missing or damaged file gives None.
"""
import errno
import json
import os


def describe_error(err):
    """A short, player-facing reason for a failed write."""
    if isinstance(err, PermissionError):
        return "another program is using the file"
    if getattr(err, "errno", None) == errno.ENOSPC:
        return "the disk is full"
    if isinstance(err, FileNotFoundError):
        return "the save folder is missing"
    return "the disk refused the write"


def write_json_checked(path, data):
    """Write `data` to `path`. Returns None on success, otherwise the reason the write failed."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, path)
    except OSError as err:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return describe_error(err)
    return None


def write_json_atomic(path, data):
    """Write `data` to `path`. Returns True on success, False if the disk refused."""
    return write_json_checked(path, data) is None


def read_json(path):
    """The parsed JSON value in `path`, or None if the file is missing, unreadable or not valid JSON."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None
