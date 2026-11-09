wha# Pixel TD

A sandbox tower defense game in pygame. Build units on a route, survive rounds that never end, and fight
for the most rounds you can. Play as the humans defending the map against zombies, or as the zombies
attacking the humans. Each side has its own story: a briefing card before the first round, a line at the start
of every round, a story line for boss rounds, and an ending when the run is lost.

## Setup

```
pip install -r requirements.txt
python main.py
```

The game is written against `pygame-ce`. Sound needs `numpy`.

## Controls

| Key | Action |
| --- | --- |
| H / Z | On the title screen: open the story briefing for humans / zombies. Enter starts, Esc goes back. In a battle, H opens the help page |
| Drag a unit | Between rounds, press a unit and drag it to an empty tile to move it. Free, and Ctrl+Z takes the move back |
| 1 to 8 | Choose a unit (7 is the anti-air unit, which only shoots flyers; 8 is the rocket, which fires lingering missiles) |
| Click a tile | Build, or select a unit on that tile. Click a pickup to collect it |
| U | Upgrade the selected unit (3 times) |
| A / B | Pick one of two ultimate forms at level 4. At level 4, A or B switches to the other form between rounds, for half the unit price |
| G | Reinforce an ultimate unit |
| X (twice) | Sell the selected unit |
| C | Combine the selected unit with the adjacent unit(s) it has a recipe for. Two units make a pair, three make a trio, and four in a plus shape make an ultimate combination (a Bastion for humans, a Hive Colossus for zombies). Each unit taken in frees a slot. The result takes on a new look: mechanical parts for humans, bigger mutations for zombies. The price rises on harder difficulties |
| Space | Between rounds: start the next round now. During a round: toggle fast spawning (the enemies come out four times quicker). Not during the build time after a map change |
| F | Toggle game speed |
| P | Pause |
| Ctrl+Z | Undo the last build or sale (between rounds) |
| F5 | Save to the current slot (between rounds). Every cleared round also autosaves |
| L | Story log: every story line of this run |
| T | Cycle the text size (Small, Normal, Large) |
| F11 | Toggle fullscreen |
| F1 | Same as H: the help page, with tabs for the controls, the pairs, the trios and quads, the units and the damage types. The battle pauses while it is open. Left and right, or a click, change the tab |
| M, - and = | Mute, volume down and up |
| Esc | Quit (asks first) |

Every 10 rounds the route changes. Units the new route covers are refunded, and you get 60 seconds of real time to rebuild. Game speed and Space cannot shorten it.

On the title screen: arrows pick the map, D picks the difficulty, 1 to 3 pick a save slot, C continues
from that slot and A continues from the autosave. The title also shows the best round reached for each side on
the chosen difficulty. The briefing has a "don't show this again" option (D), and the choices above are remembered
between sessions in `settings.json`.

Best rounds are kept in `records.json`, and the autosave in `autosave.json`. Those files and the save slots are
kept in your user data folder (`%APPDATA%\PixelTD` on Windows, `~/.local/share/PixelTD` elsewhere), so Dropbox
cannot lock them mid-save. Saves left in the game's own folder by older versions are copied over on first start.
Set `PIXEL_TD_DATA` to use another folder. If a save fails, the message says why.

Battle keys can be changed: add a `"keys"` entry to `settings.json`, such as `{"keys": {"upgrade": "e"}}`. Names
are pygame key names. See `keymap.py`. Keys for 1 to 8, Esc, F1, R and the sound keys stay fixed.

The unit cap is 24, and it grows by 2 every 3 rounds from round 12 (up to 32), so late-game gold has a use.

## Charged attacks and combined shots

Every unit charges: every 10 kills fill the charge, shown as a bar above the unit, in the unit panel, and as a gold ring on the map. The next shot is a charged attack with three times the damage, two more pierce, a wider grenade blast, and a gold trail and impact. The meter stays full until that shot fires. Combined units have their own shot styles, so each combination looks different when it fires. Every unit also kicks back when it fires, by a different amount for each role.

## Damage types

Every shot has a damage type, set by its role: bullets (rifle, medic, spitter, shaman), armour-piercing rounds (marksman, lobber), explosions (grenades, mortars, rockets), burn (flamethrowers, and the fire or acid a rocket leaves behind) and flak (anti-air). Blasts always deal explosion damage, and fire or acid on the ground always deals burn damage.

Each enemy has strengths and weaknesses against these types. Some take x1.5 or more from a type, some take less. Armour still applies on top. A weakness shows its damage number in orange, a resistance in grey, and the enemy's hover card lists both. The Damage tab of the help page lists them all. The tables are `DAMAGE_TYPES`, the `dtype` of each role and the `vs` of each enemy in `config/combat.py`.

## Balance check

A bot plays real games headlessly and reports how far it gets:

```
python tools/balance.py --games 12 --difficulty Normal
```

## Tests

From the project folder:

```
python -m unittest discover -s tests -t .
```

## Project layout

| File | What it holds |
| --- | --- |
| `main.py` | Starts the game |
| `app.py` | The window, the screens (title, briefing, battle) and their keys and clicks, with one overlay at a time |
| `game.py` | Game rules and state: rounds, gold, building, upgrades, the round update |
| `history.py` | Undo for the build phase (placements and sales between rounds) |
| `save.py` | Save files: converting a run to and from its saved form, reading and error reasons |
| `paths.py` | Where saves and settings live, and copying saves over from older versions |
| `keymap.py` | The battle keys, and the changes made in `settings.json` |
| `atomic_json.py` | The atomic JSON read and write shared by the save, settings and records files |
| `settings.py` | Remembered settings and best-round records (safe defaults) |
| `display.py` | Fits the fixed-size game canvas into the window (fullscreen and resizing) |
| `units.py`, `enemies.py`, `projectiles.py` | Defenders, enemies and shots |
| `waves.py` | Round spawn schedules |
| `world.py` | Map generation and routes |
| `config/` | All tunable numbers: `view.py`, `combat.py`, `rules.py` |
| `render.py`, `camera.py`, `sprites.py` | The 3D-style view |
| `pickups.py` | Map pickups: gold, rage and freeze |
| `story.py` | The story for each side: briefing, round, boss and ending lines |
| `hud.py`, `screens.py`, `draw_kit.py` | HUD, full-screen menus (title, briefing, pause, help) and shared drawing helpers |
| `sounds.py`, `make_voices.py` | Sound effects and the generated voice clips |
| `ui.py` | Click areas for buttons |
| `tests/` | Unit tests |
