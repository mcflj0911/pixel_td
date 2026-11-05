"""Settings and records kept between sessions: volume, the last choices on the title screen, display options and
the best round reached for each faction and difficulty.

Both are small JSON files next to the game. A missing or damaged file gives the defaults, so the game always starts.
"""
import json
import os

from config import DIFFICULTIES
from save import SAVE_DIR

SETTINGS_FILE = os.path.join(SAVE_DIR, "settings.json")
RECORDS_FILE = os.path.join(SAVE_DIR, "records.json")
TEXT_SCALES = {"Small": 0.9, "Normal": 1.0, "Large": 1.2}  # Font size multipliers, cycled with T
MAP_CHOICES = 6

DEFAULTS = {
    "map": 0,
    "difficulty": "Normal",
    "slot": 1,
    "volume": 1.0,
    "muted": False,
    "text_scale": "Normal",
    "fullscreen": False,
    "skip_briefing": False,
}


def _read_json(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path, data):
    """Write atomically, like the save files. Returns False if the disk refused."""
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
        return False
    return True


def load_settings(path=SETTINGS_FILE):
    """The saved settings, with anything missing or of the wrong type filled in from DEFAULTS."""
    data = _read_json(path)
    settings = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        value = data.get(key)
        is_number = isinstance(default, (int, float)) and not isinstance(default, bool)
        if is_number and isinstance(value, bool):
            continue  # True is an int in Python, but a number setting should not take it
        if isinstance(value, type(default)):
            settings[key] = value
    if settings["difficulty"] not in DIFFICULTIES:
        settings["difficulty"] = DEFAULTS["difficulty"]
    if settings["text_scale"] not in TEXT_SCALES:
        settings["text_scale"] = DEFAULTS["text_scale"]
    settings["map"] = min(max(settings["map"], 0), MAP_CHOICES - 1)
    settings["slot"] = min(max(settings["slot"], 1), 3)
    settings["volume"] = min(max(float(settings["volume"]), 0.0), 1.0)
    return settings


def save_settings(settings, path=SETTINGS_FILE):
    return _write_json(path, settings)


def load_records(path=RECORDS_FILE):
    """Best rounds, as {"human:Normal": 12, ...}."""
    data = _read_json(path)
    return {key: value for key, value in data.items() if isinstance(value, int) and not isinstance(value, bool)}


def best_round(records, faction, difficulty):
    return records.get(f"{faction}:{difficulty}", 0)


def record_round(records, faction, difficulty, wave):
    """Note a finished run. Returns True if it beat the best round for that faction and difficulty."""
    key = f"{faction}:{difficulty}"
    if wave > records.get(key, 0):
        records[key] = wave
        return True
    return False


def save_records(records, path=RECORDS_FILE):
    return _write_json(path, records)
