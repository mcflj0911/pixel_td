"""Save files on disk. Each slot is one JSON file.

Writes go to a temporary file first and then replace the slot, so a crash or a full disk in the middle of a
save leaves the previous save intact.
"""
import json
import os
from collections import Counter

from atomic_json import write_json_atomic
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
    if not write_json_atomic(path, data):
        return False, "Could not save the game"
    return True, "Game saved"


def run_to_data(game):
    """The saved form of a run: everything needed to carry on from the start of the next round."""
    return {
        "version": SAVE_VERSION,
        "faction": game.faction,
        "difficulty": game.difficulty,
        "map_index": game.map.index,
        "wave": game.wave,
        "gold": game.gold,
        "lives": game.lives,
        "kills": game.kills,
        "leaks": dict(game.leaks),
        "slot": game.slot,
        "units": [{"kind": u.kind, "x": u.x, "y": u.y, "level": u.level, "ultimate_index": u.ultimate_index,
                   "spent": u.spent, "damage": u.damage, "kills": u.kills,
                   "reinforce": u.reinforce} for u in game.units],
    }


def run_from_data(data):
    """Rebuild a Game from the saved form. Raises KeyError, TypeError, ValueError or IndexError if it is damaged."""
    # Imported here: game.py imports this module, so a top-level import would be circular
    from game import Game
    from config import ULTIMATES
    from units import Unit

    game = Game(data["faction"], data["map_index"], data["difficulty"])
    game.wave = data["wave"]
    game.gold = data["gold"]
    game.lives = data["lives"]
    game.kills = data["kills"]
    game.leaks = Counter(data.get("leaks", {}))
    for item in data["units"]:
        unit = Unit(game.faction, item["kind"], item["x"], item["y"])
        unit.level = item["level"]
        unit.spent = item["spent"]
        unit.damage = item.get("damage", 0.0)
        unit.kills = item.get("kills", 0)
        unit.reinforce = item.get("reinforce", 0)
        if unit.level == 4:
            unit.ultimate_index = item["ultimate_index"]
            unit.ultimate = ULTIMATES[unit.faction][unit.kind][unit.ultimate_index]
        game.units.append(unit)
        game.all_units.append(unit)
    return game


def read_save(path):
    """Returns (data, None) for a usable save. Otherwise (None, reason), where reason is one of:
    "empty" (no file), "unreadable" (not valid JSON or cannot be read) or "incompatible" (another version)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None, "empty"
    except (OSError, ValueError):
        return None, "unreadable"
    if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
        return None, "incompatible"
    return data, None
