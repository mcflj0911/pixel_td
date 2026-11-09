"""The keys for the battle, which the player can change in settings.json.

Add a "keys" entry such as {"upgrade": "e", "start": "return"}. Names are pygame key names (letters, "space",
"return", "f5", ...). A name that is unknown, or already used by another action, falls back to the default. The
keys for choosing units (1-8), Esc, F1, R and the sound keys are fixed, so they stay the same for everyone.
"""
import pygame

DEFAULT_KEYS = {  # action: default key name. Actions are claimed in this order when two would share a key
    "pause": "p", "start": "space", "help": "h", "log": "l", "speed": "f", "save": "f5",
    "upgrade": "u", "reinforce": "g", "ultimate_a": "a", "ultimate_b": "b", "sell": "x", "combine": "c",
}
FIXED_KEYS = {"escape", "f1", "f11", "r", "m", "t", "minus", "equals", "kp_minus", "kp_plus",
              "1", "2", "3", "4", "5", "6", "7", "8"}  # Not available for rebinding

_codes = {}  # action -> pygame key code
_names = dict(DEFAULT_KEYS)  # action -> key name, as shown on screen


def _code(name):
    """The key code for a pygame key name, or None if there is no such key."""
    try:
        return pygame.key.key_code(name)
    except ValueError:
        return None


def apply_settings(overrides):
    """Use the keys in `overrides` (the "keys" part of settings.json), with the defaults for anything else.

    Actions are settled in DEFAULT_KEYS order. An action that would share a key with an earlier one goes back to its
    default. If even the default is taken, the action is left unbound and shows as NONE."""
    overrides = overrides if isinstance(overrides, dict) else {}
    wanted = {}
    for action, default in DEFAULT_KEYS.items():
        name = overrides.get(action)
        valid = isinstance(name, str) and name.lower() not in FIXED_KEYS and _code(name.lower()) is not None
        wanted[action] = name.lower() if valid else default
    chosen, codes, used = {}, {}, set()
    for action, default in DEFAULT_KEYS.items():
        for name in (wanted[action], default):
            code = _code(name)
            if code is not None and code not in used:
                chosen[action], codes[action] = name, code
                used.add(code)
                break
        else:
            chosen[action] = None  # Nothing free: unbound
    _codes.clear()
    _codes.update(codes)
    _names.clear()
    _names.update(chosen)


def action_for(key):
    """The battle action bound to this key code, or None."""
    for action, code in _codes.items():
        if code == key:
            return action
    return None


def label(action):
    """How the action's key is written on screen, e.g. "U" or "SPACE"."""
    name = _names[action]
    return "NONE" if name is None else name.upper().replace("_", " ")
