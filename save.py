"""Save files on disk. Each slot is one JSON file.

Writes go to a temporary file first and then replace the slot, so a crash or a full disk in the middle of a
save leaves the previous save intact.
"""
import json
import os

from config import SAVE_FILE

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_VERSION = 1
AUTOSAVE_FILE = "autosave.json"  # Written when each round is cleared


def save_path(slot):
    """Where save slot number `slot` (1 to SAVE_SLOTS) lives."""
    return os.path.join(SAVE_DIR, SAVE_FILE.format(slot))


def autosave_path():
    return os.path.join(SAVE_DIR, AUTOSAVE_FILE)


def write_save(path, data):
    """Write `data` to `path`. Returns (True, "Game saved") or (False, "Could not save the game")."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False, "Could not save the game"
    return True, "Game saved"


def read_save(path):
    """Returns (data, None) for a usable save. Otherwise (None, reason), where reason is one of:
    "empty" (no file), "unreadable" (not valid JSON or cannot be read) or "incompatible" (another version)."""
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return None, "empty"
    except (OSError, ValueError):
        return None, "unreadable"
    if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
        return None, "incompatible"
    return data, None
