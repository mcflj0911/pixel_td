"""Full-screen menus drawn over the game: the title screen, the story briefing, pause, controls help and the quit prompt."""
import textwrap

import pygame

from config import SCREEN_WIDTH, SCREEN_HEIGHT, UNIT_TYPES, ROLES, COMBINATIONS, ROLE_DESCRIPTIONS
from draw_kit import ACCENT, WHITE, GREY, BUTTON, draw_text, draw_panel, shade
from ui import TITLE_MAP_RECT, TITLE_DIFF_RECT, TITLE_SLOT_RECT, HELP_PANEL, HELP_TAB_NAMES, HELP_TAB_RECTS
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
    for i, (key, label) in enumerate(options):
        rect = pygame.Rect(cx - 170, 220 + i * 60, 340, 50)
        draw_panel(screen, rect, fill=(36, 40, 50), accent=True)
        draw_text(screen, fonts["mid"], f"{key}   {label}", rect.center, WHITE, anchor="center")
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


def _help_controls(screen, fonts, cx):
    lines = [
        ("Build", "Click a tile.  1-7 choose a unit.  Right-click clears the selection"),
        ("Units", "Click a unit to inspect it.  U upgrades (3 times), then A or B picks an ultimate"),
        ("Switch", "At level 4, A or B (or SWITCH) changes ultimate between rounds, at half price"),
        ("Reinforce", "G on an ultimate unit: +15% damage, up to 5 times, costs more each round"),
        ("Combine", "C fuses the selected unit with an adjacent partner (see Combinations)"),
        ("Sell", "X twice (within 3 seconds) to confirm.  Refunds 60% of what you spent"),
        ("Undo", "Ctrl+Z takes back the last build, sale or combine, between rounds only"),
        ("Pickups", "Gold, rage and freeze drop on the route during a round. Click the tile to collect"),
        ("Rounds", "SPACE starts now.  Otherwise they auto-start after 10 seconds"),
        ("Map change", "Every 10 rounds the route changes. 60 s to rebuild, SPACE cannot skip"),
        ("Time", "F speed.  P pause.  H or F1: this help (the battle pauses)"),
        ("Save", "F5 saves between rounds to the slot picked on the title screen"),
        ("Sound", "M mute.  - and = volume"),
        ("Quit", "Esc asks first"),
    ]
    for i, (key, text) in enumerate(lines):
        y = 150 + i * 27
        draw_text(screen, fonts["small"], key, (cx - 300, y), ACCENT)
        draw_text(screen, fonts["small"], text, (cx - 200, y), WHITE)


def _help_combinations(screen, fonts, cx):
    for col, (faction, heading) in enumerate((("human", "HUMANS"), ("zombie", "ZOMBIES"))):
        x = cx - 350 + col * 360
        draw_text(screen, fonts["small"], heading, (x, 150), ACCENT)
        y = 180
        for recipe in COMBINATIONS[faction].values():
            first, second = (UNIT_TYPES[faction][role]["name"] for role in recipe["roles"])
            draw_text(screen, fonts["small"], recipe["name"], (x, y), WHITE)
            draw_text(screen, fonts["tiny"], f"{first} + {second}", (x + 150, y + 4), GREY)
            draw_text(screen, fonts["tiny"], recipe["desc"], (x, y + 20), GREY)
            y += 62
    draw_text(screen, fonts["tiny"],
              "Combining costs half the two prices, more on Hard. Units at level 3 or less, once each",
              (cx, HELP_PANEL.bottom - 58), GREY, anchor="center")


def _help_units(screen, fonts, cx):
    for col, (faction, heading) in enumerate((("human", "HUMANS"), ("zombie", "ZOMBIES"))):
        x = cx - 350 + col * 360
        draw_text(screen, fonts["small"], heading, (x, 150), ACCENT)
        y = 180
        for role in ROLES:
            spec = UNIT_TYPES[faction][role]
            draw_text(screen, fonts["small"], spec["name"], (x, y), WHITE)
            draw_text(screen, fonts["tiny"], f"${spec['cost']}", (x + 320, y + 4), ACCENT, anchor="topright")
            lines = textwrap.wrap(ROLE_DESCRIPTIONS[role], 52)
            for i, line in enumerate(lines):
                draw_text(screen, fonts["tiny"], line, (x, y + 20 + i * 15), GREY)
            y += 20 + 15 * len(lines) + 8


def draw_help(screen, fonts, tab=0):
    """The help page: the controls, the combinations and the units, on tabs. `tab` is the one showing."""
    shade(screen, 225)
    cx = SCREEN_WIDTH // 2
    draw_panel(screen, HELP_PANEL, fill=(14, 16, 20), accent=True)
    draw_text(screen, fonts["big"], "HELP", (cx, 66), ACCENT, anchor="center")
    for i, (name, rect) in enumerate(zip(HELP_TAB_NAMES, HELP_TAB_RECTS)):
        active = i == tab
        draw_panel(screen, rect, fill=(70, 52, 104) if active else BUTTON, accent=active, slant=8)
        draw_text(screen, fonts["small"], name, rect.center, WHITE if active else GREY, anchor="center")
    if tab == 0:
        _help_controls(screen, fonts, cx)
    elif tab == 1:
        _help_combinations(screen, fonts, cx)
    else:
        _help_units(screen, fonts, cx)
    draw_text(screen, fonts["small"], "LEFT / RIGHT or click a tab.   H, F1 or Esc to close",
              (cx, HELP_PANEL.bottom - 22), GREY, anchor="center")


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
