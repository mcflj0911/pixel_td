"""Full-screen menus drawn over the game: the title screen, the story briefing, pause, controls help and the quit prompt."""
import textwrap

import pygame

from config import (SCREEN_WIDTH, SCREEN_HEIGHT, UNIT_TYPES, ROLES, COMBINATIONS, ROLE_DESCRIPTIONS, FACTIONS,
                    ENEMY_TYPES, DAMAGE_TYPES, DAMAGE_NAMES, DAMAGE_NOTES, WEAK_HIT_COLOUR, RESIST_HIT_COLOUR,
                    CHARGE_KILLS, SHOT_NAMES, COMBO_KIT)
from keymap import label
from draw_kit import ACCENT, WHITE, GREY, BUTTON, draw_text, draw_panel, shade
from ui import (TITLE_MAP_RECT, TITLE_DIFF_RECT, TITLE_SLOT_RECT, HELP_PANEL, HELP_TAB_NAMES, HELP_TAB_RECTS,
                HELP_VIEW)
import story


def draw_briefing(screen, fonts, faction, skip=False):
    """The opening card for a faction: its story, before the first round. ENTER starts, ESC goes back."""
    shade(screen)
    cx = SCREEN_WIDTH // 2
    box = pygame.Rect(cx - 400, 60, 800, 600)
    draw_panel(screen, box, fill=(14, 16, 20), accent=True)
    content = story.STORY[faction]
    draw_text(screen, fonts["big"], content["title"], (cx, 92), ACCENT, anchor="center")
    draw_text(screen, fonts["small"], story.tagline(faction), (cx, 140), GREY, anchor="center")
    y = 180
    for paragraph in story.briefing(faction):
        for line in textwrap.wrap(paragraph, 92):
            draw_text(screen, fonts["small"], line, (cx - 360, y), WHITE)
            y += 24
        y += 14
    draw_text(screen, fonts["small"], f"[D] don't show this again: {'ON' if skip else 'OFF'}", (cx, 586), GREY,
              anchor="center")
    draw_text(screen, fonts["small"], "ENTER  begin          ESC  back", (cx, 616), ACCENT, anchor="center")


def draw_title(screen, fonts, setup):
    """Title screen drawn over the running demo battle. `setup` holds the map, difficulty and save slot picked
    so far, and `setup["saves"]` maps each slot to the round it holds (or None when empty)."""
    shade(screen)
    cx = SCREEN_WIDTH // 2
    draw_text(screen, fonts["big"], "PIXEL TD", (cx, 110), ACCENT, anchor="center")
    draw_text(screen, fonts["mid"], "SANDBOX DEFENSE", (cx, 160), WHITE, anchor="center")
    options = [("H", "PLAY AS HUMANS"), ("Z", "PLAY AS ZOMBIES")]
    for i, (key, text) in enumerate(options):
        rect = pygame.Rect(cx - 170, 220 + i * 60, 340, 50)
        draw_panel(screen, rect, fill=(36, 40, 50), accent=True)
        draw_text(screen, fonts["mid"], f"{key}   {text}", rect.center, WHITE, anchor="center")
    map_label = "Classic" if setup["map"] == 0 else f"Random {setup['map']}"
    draw_panel(screen, TITLE_MAP_RECT, fill=(28, 30, 38), slant=8)
    draw_text(screen, fonts["small"], f"< >  MAP {setup['map'] + 1}: {map_label}", TITLE_MAP_RECT.center, WHITE,
          anchor="center")
    draw_panel(screen, TITLE_DIFF_RECT, fill=(28, 30, 38), slant=8)
    draw_text(screen, fonts["small"], f"D   DIFFICULTY: {setup['difficulty'].upper()}", TITLE_DIFF_RECT.center, WHITE,
          anchor="center")
    slot = setup["slot"]
    saved = setup["saves"].get(slot)
    draw_panel(screen, TITLE_SLOT_RECT, fill=(28, 30, 38), slant=8)
    detail = f"round {saved}  (C continues)" if saved else "empty"
    draw_text(screen, fonts["small"], f"SAVE SLOT {slot}: {detail}", TITLE_SLOT_RECT.center, WHITE,
          anchor="center")
    if setup.get("notice"):
        draw_text(screen, fonts["small"], setup["notice"], (cx, 596), ACCENT, anchor="center")
    best = setup.get("best", {})
    if best:
        draw_text(screen, fonts["small"], f"BEST ROUND   Humans {best.get('human', 0)}   Zombies {best.get('zombie', 0)}"
                  f"   ({setup['difficulty']})", (cx, 402), ACCENT, anchor="center")
    autosave = setup.get("autosave")
    draw_panel(screen, pygame.Rect(cx - 170, 612, 340, 32), fill=(28, 30, 38), slant=8)
    auto_text = f"AUTOSAVE: round {autosave}  (A continues)" if autosave else "AUTOSAVE: none yet"
    draw_text(screen, fonts["small"], auto_text, (cx, 628), WHITE if autosave else GREY, anchor="center")
    draw_text(screen, fonts["tiny"], "Live demo battle: the AI builds and fights on its own", (cx, 662), GREY,
              anchor="center")
    draw_text(screen, fonts["tiny"], "1 2 3 save slot   T text size: " + setup.get("text_scale", "Normal").upper()
              + "   F11 fullscreen   Esc quits", (cx, 684), GREY, anchor="center")


def draw_pause(screen, fonts, game=None):
    shade(screen)
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    draw_text(screen, fonts["big"], "PAUSED", (cx, cy - 110), ACCENT, anchor="center")
    if game is not None:
        draw_text(screen, fonts["mid"], f"ROUND {game.wave}     LIVES {game.lives}     GOLD {game.gold}",
                  (cx, cy - 50), WHITE, anchor="center")
        draw_text(screen, fonts["small"], f"KILLS {game.kills}     UNITS {len(game.units)}     MAP {game.map.index + 1}",
                  (cx, cy - 16), GREY, anchor="center")
        if not game.wave_active and game.status == "playing":
            parts = [f"{n} {name}" for name, n in game.next_round_preview()]
            for i, line in enumerate(textwrap.wrap("NEXT ROUND: " + ", ".join(parts), 70)[:2]):
                draw_text(screen, fonts["small"], line, (cx, cy + 16 + i * 22), WHITE, anchor="center")
    draw_text(screen, fonts["small"], "P to resume", (cx, cy + 80), GREY, anchor="center")


HELP_LAYER_H = 2000  # The help tabs are drawn this tall, then the part in view is copied to the page
_help_layer = None  # Made once, then reused every frame


def _help_controls(screen, fonts, cx):
    """Returns the y below the last line."""
    k = label  # The keys are shown as the player has bound them
    lines = [
        ("Build", "Click a tile.  1-8 choose a unit.  Right-click clears the selection"),
        ("Units", f"Click a unit to inspect it.  {k('upgrade')} upgrades (3 times), then "
                  f"{k('ultimate_a')} or {k('ultimate_b')} picks an ultimate"),
        ("Switch", f"At level 4, {k('ultimate_a')} or {k('ultimate_b')} (or SWITCH) changes ultimate between rounds"),
        ("Reinforce", f"{k('reinforce')} on an ultimate unit: +15% damage, up to 5 times, costs more each round"),
        ("Combine", f"{k('combine')} fuses the selected unit with its neighbours (see Pairs and Trios & quads)"),
        ("Charge", f"Every unit charges: {CHARGE_KILLS} kills fill it, and the next shot is a charged attack"),
        ("Move", "Drag a unit to an empty tile between rounds. It is free, and Ctrl+Z takes the move back"),
        ("Sell", f"{k('sell')} twice (within 3 seconds) to confirm.  Refunds 60% of what you spent"),
        ("Undo", "Ctrl+Z takes back the last build, sale or combine, between rounds only"),
        ("Pickups", "Gold, rage and freeze drop on the route in a round. Click the tile to collect"),
        ("Rounds", f"{k('start')} starts now.  Otherwise they auto-start after 10 seconds"),
        ("Map change", f"Every 10 rounds the route changes. 60 s to rebuild, {k('start')} cannot skip"),
        ("Time", f"{k('speed')} speed.  {k('pause')} pause.  {k('help')} or F1: this help (the battle pauses)"),
        ("Save", f"{k('save')} saves between rounds to the slot picked on the title screen"),
        ("Sound", "M mute.  - and = volume"),
        ("Quit", "Esc asks first.  Keys can be changed in settings.json (see keymap.py)"),
    ]
    for i, (key, text) in enumerate(lines):
        y = 150 + i * 27
        draw_text(screen, fonts["small"], key, (cx - 300, y), ACCENT)
        draw_text(screen, fonts["small"], text, (cx - 200, y), WHITE)
    return 150 + len(lines) * 27


def _help_recipes(screen, fonts, cx, sizes, footer, row=42, shot_below=False):
    """Combinations with the given numbers of units, for both factions, with the units they join and what they do.
    `row` is the height of each entry. With `shot_below` the shot style gets a line of its own under the description.
    Returns the y below the last line, footer included."""
    bottom = 176
    for col, (faction, heading) in enumerate((("human", "HUMANS"), ("zombie", "ZOMBIES"))):
        x = cx - 350 + col * 360
        draw_text(screen, fonts["small"], heading, (x, 150), ACCENT)
        y = 176
        for recipe in COMBINATIONS[faction].values():
            if len(recipe["roles"]) not in sizes:
                continue
            names = " + ".join(UNIT_TYPES[faction][role]["short"] for role in recipe["roles"])
            draw_text(screen, fonts["small"], recipe["name"], (x, y), WHITE)
            draw_text(screen, fonts["tiny"], names, (x + 340, y + 4), GREY, anchor="topright")
            draw_text(screen, fonts["tiny"], recipe["desc"], (x, y + 20), GREY)
            if shot_below:
                draw_text(screen, fonts["tiny"], f"Shots: {SHOT_NAMES[recipe['shot']]}", (x, y + 34), ACCENT)
            else:
                draw_text(screen, fonts["tiny"], SHOT_NAMES[recipe["shot"]], (x + 340, y + 20), ACCENT,
                          anchor="topright")
            y += row
        bottom = max(bottom, y)
    draw_text(screen, fonts["tiny"], footer, (cx, bottom + 12), GREY, anchor="center")
    return bottom + 30


def _help_pairs(screen, fonts, cx):
    return _help_recipes(screen, fonts, cx, sizes=(2,), row=46, shot_below=True,
                         footer="Combine with C: a unit and one neighbour make a pair. Half the prices, more on Hard")


def _help_big_combos(screen, fonts, cx):
    return _help_recipes(screen, fonts, cx, sizes=(3, 4), row=52, shot_below=True,
                         footer="Trios need two neighbours, quads three (a plus shape). The biggest that fits is used")


def _help_units(screen, fonts, cx):
    """Returns the y below the longest column."""
    bottom = 180
    for col, (faction, heading) in enumerate((("human", "HUMANS"), ("zombie", "ZOMBIES"))):
        x = cx - 350 + col * 360
        draw_text(screen, fonts["small"], heading, (x, 150), ACCENT)
        y = 180
        for role in ROLES:
            spec = UNIT_TYPES[faction][role]
            draw_text(screen, fonts["small"], spec["name"], (x, y), WHITE)
            draw_text(screen, fonts["tiny"], f"${spec['cost']}   {DAMAGE_NAMES[spec['dtype']]}   {CHARGE_KILLS} kills",
                      (x + 320, y + 4), ACCENT, anchor="topright")
            lines = textwrap.wrap(ROLE_DESCRIPTIONS[role], 52)
            for i, line in enumerate(lines):
                draw_text(screen, fonts["tiny"], line, (x, y + 20 + i * 15), GREY)
            y += 20 + 15 * len(lines) + 3
        bottom = max(bottom, y)
    return bottom


def _help_upgrades(screen, fonts, cx):
    """Every combination's own upgrade path (levels 2 and 3) and its two ultimate forms, for both factions.
    It is long, which is why the help page scrolls. Returns the y below the longest column."""
    bottom = 176
    for col, (faction, heading) in enumerate((("human", "HUMANS"), ("zombie", "ZOMBIES"))):
        x = cx - 350 + col * 360
        draw_text(screen, fonts["small"], heading, (x, 150), ACCENT)
        y = 176
        for recipe_id, recipe in COMBINATIONS[faction].items():
            kit = COMBO_KIT[faction][recipe_id]
            draw_text(screen, fonts["small"], recipe["name"], (x, y), WHITE)
            y += 22
            steps = (("Lv 2", kit["path"][0]), ("Lv 3", kit["path"][1]),
                     ("Lv 4 A", kit["ultimates"][0]), ("Lv 4 B", kit["ultimates"][1]))
            for tag, step in steps:
                lines = textwrap.wrap(f"{step['name']}: {step['desc']}", 38)[:2]
                draw_text(screen, fonts["tiny"], tag, (x, y + 2), ACCENT)
                for i, line in enumerate(lines):  # The name is bright, the rest of the line dimmer
                    draw_text(screen, fonts["tiny"], line, (x + 50, y + 2 + i * 13), WHITE if i == 0 else GREY)
                y += 14 + 13 * (len(lines) - 1)
            y += 8
        bottom = max(bottom, y)
    return bottom


def _damage_users(dtype):
    """The units that deal this damage type, from both factions, with no repeats."""
    names = []
    for faction in FACTIONS:
        for role in ROLES:
            spec = UNIT_TYPES[faction][role]
            if spec["dtype"] == dtype and spec["name"] not in names:
                names.append(spec["name"])
    return ", ".join(names)


def _damage_enemies(dtype, weak):
    """The enemies that take more (weak=True) or less damage of this type, with the multiplier, from both factions.
    Empty when there are none."""
    found = {}
    for faction in FACTIONS:
        for spec in ENEMY_TYPES[faction].values():
            factor = spec.get("vs", {}).get(dtype, 1.0)
            if factor != 1.0 and (factor > 1.0) == weak:
                found.setdefault(spec["name"], factor)
    return ", ".join(f"{name} x{factor:g}" for name, factor in found.items())


def _help_damage(screen, fonts, cx):
    """Returns the y below the footer."""
    x = cx - 330
    draw_text(screen, fonts["tiny"],
              "Every shot deals one damage type. Some enemies take more of a type, some less. Armour still applies on top.",
              (cx, 150), GREY, anchor="center")
    y = 176
    for dtype in DAMAGE_TYPES:
        name = DAMAGE_NAMES[dtype] + (f"  ({DAMAGE_NOTES[dtype]})" if dtype in DAMAGE_NOTES else "")
        draw_text(screen, fonts["small"], name, (x, y), WHITE)
        draw_text(screen, fonts["tiny"], f"Dealt by: {_damage_users(dtype)}", (x + 14, y + 24), GREY)
        weak = _damage_enemies(dtype, weak=True)
        resist = _damage_enemies(dtype, weak=False)
        draw_text(screen, fonts["tiny"], f"Strong against: {weak or 'nothing special'}", (x + 14, y + 40),
                  WEAK_HIT_COLOUR if weak else GREY)
        draw_text(screen, fonts["tiny"], f"Resisted by: {resist or 'nothing special'}", (x + 14, y + 55),
                  RESIST_HIT_COLOUR if resist else GREY)
        y += 72
    draw_text(screen, fonts["tiny"],
              "Blasts always deal explosion damage. Fire and acid left on the ground always deal burn damage.",
              (cx, y + 8), GREY, anchor="center")
    return y + 30


HELP_DRAWERS = (_help_controls, _help_pairs, _help_big_combos, _help_units, _help_upgrades, _help_damage)


def draw_help(screen, fonts, tab=0, scroll=0):
    """The help page: the controls, the combinations, the units, the upgrades and the damage types, on tabs. `tab` is
    the one showing, and `scroll` how far down its content is. Returns the most the page can scroll (0 when it fits)."""
    global _help_layer
    shade(screen, 225)
    cx = SCREEN_WIDTH // 2
    draw_panel(screen, HELP_PANEL, fill=(14, 16, 20), accent=True)
    draw_text(screen, fonts["big"], "HELP", (cx, 66), ACCENT, anchor="center")
    for i, (name, rect) in enumerate(zip(HELP_TAB_NAMES, HELP_TAB_RECTS)):
        active = i == tab
        draw_panel(screen, rect, fill=(70, 52, 104) if active else BUTTON, accent=active, slant=8)
        draw_text(screen, fonts["small"], name, rect.center, WHITE if active else GREY, anchor="center")

    # The tab is drawn onto a tall layer in page coordinates, then the part in view is copied across. The layer grows
    # if a tab is taller than it, and the tab is drawn again
    height = HELP_LAYER_H
    while True:
        if _help_layer is None or _help_layer.get_height() < height:
            _help_layer = pygame.Surface((SCREEN_WIDTH, height))
        _help_layer.fill((14, 16, 20))
        bottom = HELP_DRAWERS[tab](_help_layer, fonts, cx)
        if bottom + 16 <= _help_layer.get_height():
            break
        height = bottom + 64
    max_scroll = max(0, bottom + 16 - HELP_VIEW.bottom)
    scroll = max(0, min(scroll, max_scroll))
    screen.blit(_help_layer, HELP_VIEW.topleft, area=pygame.Rect(HELP_VIEW.x, HELP_VIEW.y + scroll, HELP_VIEW.w,
                                                                 HELP_VIEW.h))
    if max_scroll:  # A scroll bar: its thumb is the part of the page in view
        track = pygame.Rect(HELP_VIEW.right + 6, HELP_VIEW.y, 5, HELP_VIEW.h)
        pygame.draw.rect(screen, BUTTON, track)
        content = bottom + 16 - HELP_VIEW.y
        thumb_h = max(24, int(HELP_VIEW.h * HELP_VIEW.h / content))
        thumb_y = track.y + int((track.h - thumb_h) * scroll / max_scroll)
        pygame.draw.rect(screen, ACCENT, (track.x, thumb_y, track.w, thumb_h))

    draw_text(screen, fonts["small"], "LEFT / RIGHT change tab.   UP / DOWN or the wheel scroll.   H, F1 or Esc close",
              (cx, HELP_PANEL.bottom - 22), GREY, anchor="center")
    return max_scroll


def draw_quit_prompt(screen, fonts):
    """Shown when Esc is pressed. Y quits; N or Esc goes back to the game."""
    shade(screen)
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    box = pygame.Rect(cx - 200, cy - 80, 400, 160)
    draw_panel(screen, box, fill=(36, 40, 50), accent=True)
    draw_text(screen, fonts["mid"], "QUIT THE GAME?", (cx, cy - 40), WHITE, anchor="center")
    draw_text(screen, fonts["small"], "Unsaved progress will be lost", (cx, cy - 10), GREY, anchor="center")
    draw_text(screen, fonts["small"], "Y  quit        N / Esc  keep playing", (cx, cy + 30), ACCENT, anchor="center")


def draw_log(screen, fonts, lines):
    """The story log (L): the story lines of this run, newest at the bottom."""
    shade(screen, 225)
    cx = SCREEN_WIDTH // 2
    box = pygame.Rect(cx - 380, 90, 760, 500)
    draw_panel(screen, box, fill=(14, 16, 20), accent=True)
    draw_text(screen, fonts["big"], "STORY LOG", (cx, 116), ACCENT, anchor="center")
    if not lines:
        draw_text(screen, fonts["small"], "Nothing yet. The story starts with the first round.", (cx, 300),
                  GREY, anchor="center")
    y = 170
    for line in lines[-12:]:
        for wrapped in textwrap.wrap(line, 84):
            draw_text(screen, fonts["small"], wrapped, (cx - 340, y), WHITE)
            y += 26
        y += 8
    draw_text(screen, fonts["small"], "L or Esc to close", (cx, 572), GREY, anchor="center")
