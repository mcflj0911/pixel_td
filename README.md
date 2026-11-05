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
| 1 to 7 | Choose a unit (7 is the anti-air unit, which only shoots flyers) |
| Click a tile | Build, or select a unit on that tile. Click a pickup to collect it |
| U | Upgrade the selected unit (3 times) |
| A / B | Pick one of two ultimate forms at level 4. At level 4, A or B switches to the other form between rounds, for half the unit price |
| G | Reinforce an ultimate unit |
| X (twice) | Sell the selected unit |
| C | Combine the selected unit with an adjacent unit it has a recipe for. The two become one unit and a slot is freed. The price rises on harder difficulties |
| Space | Between rounds: start the next round now. During a round: toggle fast spawning (the enemies come out four times quicker). Not during the build time after a map change |
| F | Toggle game speed |
| P | Pause |
| Ctrl+Z | Undo the last build or sale (between rounds) |
| F5 | Save to the current slot (between rounds). Every cleared round also autosaves |
| L | Story log: every story line of this run |
| T | Cycle the text size (Small, Normal, Large) |
| F11 | Toggle fullscreen |
| F1 | Same as H: the help page, with tabs for the controls, the combinations and the units. The battle pauses while it is open. Left and right, or a click, change the tab |
| M, - and = | Mute, volume down and up |
| Esc | Quit (asks first) |

Every 10 rounds the route changes. Units the new route covers are refunded, and you get 60 seconds of real time to rebuild. Game speed and Space cannot shorten it.

On the title screen: arrows pick the map, D picks the difficulty, 1 to 3 pick a save slot, C continues
from that slot and A continues from the autosave. The title also shows the best round reached for each side on
the chosen difficulty. The briefing has a "don't show this again" option (D), and the choices above are remembered
between sessions in `settings.json`.

Best rounds are kept in `records.json`, and the autosave in `autosave.json`. Those files and the save slots are
written next to the game and are not part of the project (see `.gitignore`).

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
