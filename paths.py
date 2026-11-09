"""Where the game keeps its saves, settings and records.

They live in a folder for the player's user account (the PixelTD folder inside %APPDATA% on Windows), not in the game's own folder.
A game folder inside Dropbox gets its files locked while they sync, which made saves fail. Set PIXEL_TD_DATA to
choose another folder.
"""
import glob
import os
import shutil

APP_FOLDER = "PixelTD"
PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
OWN_FILES = ("autosave.json", "settings.json", "records.json")  # Plus the savegame_N.json slots


def data_dir():
    """The folder for saved data. Falls back to the game's own folder if the user folder cannot be made."""
    override = os.environ.get("PIXEL_TD_DATA")
    if override:
        return override
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    path = os.path.join(base, APP_FOLDER)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return PROJECT_FOLDER
    return path


def migrate_saves(old_folder=PROJECT_FOLDER, new_folder=None):
    """Copy saves left in the game's own folder by older versions into the data folder. Never overwrites a file
    that is already there. Returns the names copied."""
    new_folder = new_folder or data_dir()
    if os.path.abspath(old_folder) == os.path.abspath(new_folder):
        return []
    names = list(OWN_FILES) + [os.path.basename(p) for p in glob.glob(os.path.join(old_folder, "savegame_*.json"))]
    copied = []
    for name in names:
        source = os.path.join(old_folder, name)
        target = os.path.join(new_folder, name)
        if os.path.exists(source) and not os.path.exists(target):
            try:
                shutil.copy2(source, target)
                copied.append(name)
            except OSError:
                pass
    return copied
