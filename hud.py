import math
import textwrap

import pygame

import story
from config import (SCREEN_WIDTH, SCREEN_HEIGHT, MAP_COLS, MAP_ROWS, UNIT_TYPES, ROLES, START_LIVES, ULTIMATES,
                    AIR_ROLES, REINFORCE_MAX, START_COLOUR, END_COLOUR, SELL_REFUND, MAX_UNITS, RESPEC_COST,
                    SELL_CONFIRM_SECONDS, AUTO_START_SECONDS, MAP_BUILD_SECONDS)
from draw_kit import (HUD_EDGE, ACCENT, WHITE, GREY, RED, GREEN, DIM, BUTTON, draw_text, draw_panel, dim_colour,
                      shade)
from sprites import unit_sprite
from ui import ROLE_RECTS, PANEL, UPGRADE_RECT, ULT_RECTS, SELL_RECT, COMBINE_RECT
from units import group_multiplier, squad_multiplier

MINI_POS = (16, 16)
MINI_W, MINI_H = 150, 112
ROUND_RECT = pygame.Rect(380, 10, 240, 62)
PREVIEW_RECT = pygame.Rect(380, 78, 240, 62)  # What the next round brings, shown between rounds
TAG_X = PREVIEW_RECT.x - 6 - 84  # Warning tags sit to the left of the preview, clear of the text
POINTS_RECT = pygame.Rect(770, 10, 214, 62)
LIVES_RECT = pygame.Rect(16, 628, 118, 70)
HINT_Y = 606

# --- TOP ---

def _draw_round(screen, game, fonts, speed):
    draw_panel(screen, ROUND_RECT, accent=True)
    label = f"ROUND {game.wave}" if game.wave else "READY"
    draw_text(screen, fonts["mid"], label, (ROUND_RECT.centerx, ROUND_RECT.y + 22), anchor="midtop")
    if game.wave_active:
        state = "IN PROGRESS"
    elif game.status == "playing" and game.countdown_locked:
        state = f"MAP BUILD {math.ceil(game.countdown)}s"
    elif game.status == "playing":
        state = f"NEXT IN {math.ceil(game.countdown)}s"
    else:
        state = ""
    draw_text(screen, fonts["tiny"], f"{state}   x{speed}   MAP {game.map.index + 1}",
          (ROUND_RECT.centerx, ROUND_RECT.bottom - 6), GREY, anchor="midbottom")
    if not game.wave_active and game.status == "playing":
        full = MAP_BUILD_SECONDS if game.countdown_locked else AUTO_START_SECONDS
        ratio = max(0.0, min(1.0, game.countdown / full))
        pygame.draw.rect(screen, ACCENT, (ROUND_RECT.x, ROUND_RECT.bottom - 3, ROUND_RECT.w * ratio, 3))


def _draw_preview(screen, game, fonts):
    """Between rounds: what the next round brings, so the player can prepare."""
    if game.wave_active or game.status != "playing":
        return
    draw_panel(screen, PREVIEW_RECT, slant=8)
    parts = [f"{n} {name}" for name, n in game.next_round_preview()]
    lines = textwrap.wrap("NEXT: " + ", ".join(parts), 32)[:3]
    for i, line in enumerate(lines):
        draw_text(screen, fonts["tiny"], line, (PREVIEW_RECT.x + 12, PREVIEW_RECT.y + 6 + i * 18), WHITE)
    for i, tag in enumerate(game.next_round_warnings()):
        tag_rect = pygame.Rect(TAG_X, PREVIEW_RECT.y + i * 26, 84, 22)
        draw_panel(screen, tag_rect, slant=6)
        draw_text(screen, fonts["tiny"], tag, tag_rect.center, RED if tag == "BOSS" else (120, 200, 255), anchor="center")


def _draw_points(screen, game, fonts):
    draw_panel(screen, POINTS_RECT, accent=True)
    draw_text(screen, fonts["tiny"], "GOLD", (POINTS_RECT.x + 26, POINTS_RECT.y + 12), GREY)
    draw_text(screen, fonts["mid"], f"$ {game.gold}", (POINTS_RECT.x + 26, POINTS_RECT.y + 40), ACCENT, anchor="midleft")
    draw_text(screen, fonts["tiny"], f"UNITS {len(game.units)}/{MAX_UNITS}", (POINTS_RECT.right - 16, POINTS_RECT.y + 40),
          RED if len(game.units) >= MAX_UNITS else GREY, anchor="midright")
    if game.gain_life > 0:
        draw_text(screen, fonts["small"], f"+{game.gain}", (POINTS_RECT.right - 16, POINTS_RECT.y + 14),
              GREEN, anchor="topright")




def _draw_feed(screen, game, fonts):
    for i, (text, colour, life) in enumerate(game.feed):
        fade = min(1.0, life)
        draw_text(screen, fonts["small"], text, (SCREEN_WIDTH - 16, 84 + i * 20), dim_colour(colour, fade), anchor="topright")


# --- MINIMAP ---

def _draw_radar(screen, game, fonts, selected):
    sx, sy = MINI_W / MAP_COLS, MINI_H / MAP_ROWS
    box = pygame.Rect(MINI_POS[0], MINI_POS[1], MINI_W, MINI_H)
    pygame.draw.rect(screen, (10, 12, 16), box)
    for col, row in game.map.cells:
        pygame.draw.rect(screen, (120, 110, 90), (box.x + col * sx, box.y + row * sy, sx + 1, sy + 1))
    for x, y, _ in game.map.doodads:
        pygame.draw.rect(screen, (50, 110, 60), (box.x + x * sx - 1, box.y + y * sy - 1, 2, 2))
    start, end = game.map.start, game.map.end
    pygame.draw.rect(screen, START_COLOUR, (box.x + start[0] * sx - 3, box.y + start[1] * sy - 3, 6, 6))
    pygame.draw.rect(screen, END_COLOUR, (box.x + end[0] * sx - 3, box.y + end[1] * sy - 3, 6, 6))
    for unit in game.units:
        colour = (110, 170, 255) if unit.faction == "human" else (190, 120, 240)
        pygame.draw.rect(screen, colour, (box.x + unit.x * sx - 2, box.y + unit.y * sy - 2, 4, 4))
    if not game.wave_active and game.status == "playing" and game.next_round_has_flyers():
        # The flyers' straight line from start to end, drawn as a dotted lane
        sx0, sy0 = box.x + start[0] * sx, box.y + start[1] * sy
        sx1, sy1 = box.x + end[0] * sx, box.y + end[1] * sy
        steps = 14
        for i in range(0, steps, 2):
            a, b = i / steps, (i + 1) / steps
            pygame.draw.line(screen, (120, 80, 90), (sx0 + (sx1 - sx0) * a, sy0 + (sy1 - sy0) * a),
                             (sx0 + (sx1 - sx0) * b, sy0 + (sy1 - sy0) * b), 1)
    for enemy in game.enemies:
        pygame.draw.rect(screen, RED, (box.x + enemy.x * sx - 1, box.y + enemy.y * sy - 1, 3, 3))
    if selected is not None:
        pygame.draw.circle(screen, ACCENT, (int(box.x + selected.x * sx), int(box.y + selected.y * sy)), 6, 1)
    pygame.draw.rect(screen, HUD_EDGE, box, 1)
    draw_text(screen, fonts["tiny"], "RADAR", (box.x + 6, box.y + 4), GREY)


def _draw_audio(screen, fonts, audio):
    draw_text(screen, fonts["tiny"], audio, (MINI_POS[0] + 2, MINI_POS[1] + MINI_H + 6), GREY)


# --- BOTTOM LEFT: LIVES ---

def _draw_lives(screen, game, fonts):
    draw_panel(screen, LIVES_RECT, slant=8)
    draw_text(screen, fonts["tiny"], "LIVES", (LIVES_RECT.x + 14, LIVES_RECT.y + 8), GREY)
    draw_text(screen, fonts["mid"], f"{game.lives}", (LIVES_RECT.x + 14, LIVES_RECT.y + 22))
    bar = pygame.Rect(LIVES_RECT.x + 12, LIVES_RECT.bottom - 16, LIVES_RECT.w - 24, 8)
    pygame.draw.rect(screen, DIM, bar)
    fill = bar.w * max(0, game.lives) / START_LIVES
    pygame.draw.rect(screen, RED if game.lives <= START_LIVES // 3 else WHITE,
                     (bar.x, bar.y, int(fill), bar.h))


# --- BOTTOM CENTRE: HOTBAR ---

def _draw_hotbar(screen, game, fonts):
    for i, role in enumerate(ROLES):
        rect = ROLE_RECTS[role]
        spec = UNIT_TYPES[game.faction][role]
        draw_panel(screen, rect, slant=10)
        active = role == game.selected and game.selected_unit is None
        if active:
            pygame.draw.lines(screen, ACCENT, True, [(rect.x + 10, rect.y), (rect.right, rect.y),
                                                     (rect.right - 10, rect.bottom), (rect.x, rect.bottom)], 2)
        icon = pygame.transform.scale(unit_sprite(game.faction, role, 1, None), (24, 36))
        screen.blit(icon, (rect.x + 14, rect.y + 17))
        draw_text(screen, fonts["tiny"], str(i + 1), (rect.x + 8, rect.y + 6), ACCENT)
        if role in AIR_ROLES:  # Can hit flying enemies
            draw_text(screen, fonts["tiny"], "AIR", (rect.right - 8, rect.bottom - 6), (120, 200, 255), anchor="bottomright")
        draw_text(screen, fonts["tiny"], spec["short"], (rect.x + 44, rect.y + 12), WHITE)
        affordable = game.gold >= spec["cost"]
        draw_text(screen, fonts["tiny"], f"$ {spec['cost']}", (rect.x + 44, rect.y + 42),
              GREEN if affordable else RED)


def _draw_hint(screen, game, fonts):
    if game.message:
        text, colour = game.message, ACCENT
    elif game.selected_unit is not None:
        text, colour = "U upgrade    A / B ultimate at level 3    C combine    X sell (twice)    Right-click deselect", GREY
    elif game.wave_active:
        text, colour = "Hold the route. Click a unit to upgrade it", GREY
    else:
        text, colour = "Click a tile to build    1-7 pick unit    SPACE start now    H help    Esc quit", GREY
    draw_text(screen, fonts["small"], text, (SCREEN_WIDTH // 2, HINT_Y), colour, anchor="midtop")


# --- RIGHT: SELECTED UNIT ---

def _stat_bar(screen, fonts, y, label, value_text, ratio):
    x = PANEL.x + 14
    draw_text(screen, fonts["tiny"], label, (x, y), GREY)
    bar = pygame.Rect(x + 86, y + 4, PANEL.w - 186, 8)
    pygame.draw.rect(screen, DIM, bar)
    pygame.draw.rect(screen, WHITE, (bar.x, bar.y, int(bar.w * max(0.0, min(1.0, ratio))), bar.h))
    draw_text(screen, fonts["tiny"], value_text, (PANEL.right - 14, y), WHITE, anchor="topright")


def _draw_unit_panel(screen, game, fonts):
    unit = game.selected_unit
    draw_panel(screen, PANEL, accent=True)
    _draw_unit_header(screen, unit, fonts)
    _draw_unit_stats(screen, unit, fonts)
    _draw_ultimate_switch(screen, game, unit, fonts)
    _draw_sell_button(screen, game, unit, fonts)
    _draw_upgrade_or_ultimate(screen, game, unit, fonts)
    _draw_combine(screen, game, unit, fonts)


def _draw_unit_header(screen, unit, fonts):
    """Name, level pips, and the combo group and squad bonuses."""
    draw_text(screen, fonts["tiny"], "UNIT", (PANEL.x + 14, PANEL.y + 10), GREY)
    draw_text(screen, fonts["mid"], unit.display_name, (PANEL.x + 14, PANEL.y + 26))

    for i in range(4):  # Level pips
        pip = pygame.Rect(PANEL.x + 14 + i * 36, PANEL.y + 62, 30, 8)
        pygame.draw.rect(screen, ACCENT if i < unit.level else DIM, pip)
    if unit.group > 1 or unit.mixed:  # Combo group and the mixed squad bonus, with the damage each adds
        parts = []
        if unit.group > 1:
            parts.append(f"GROUP x{group_multiplier(unit.group):g}")
        if unit.mixed:
            parts.append(f"SQUAD x{squad_multiplier(unit.mixed):.2f}")
        draw_text(screen, fonts["tiny"], "  ".join(parts),
                  (PANEL.right - 14, PANEL.y + 50), ACCENT, anchor="topright")


def _draw_unit_stats(screen, unit, fonts):
    """Damage dealt and kills, the three stat bars, the special effects and the ultimate's description."""
    draw_text(screen, fonts["tiny"], f"DEALT {unit.damage:.0f}   KILLS {unit.kills}",
              (PANEL.right - 14, PANEL.y + 80), GREY, anchor="topright")
    s = unit.stats
    _stat_bar(screen, fonts, PANEL.y + 96, "DAMAGE", f"{s['damage']:.0f}", s["damage"] / 300)
    _stat_bar(screen, fonts, PANEL.y + 120, "RATE", f"{s['rate'] * unit.buff:.2f}/s", s["rate"] * unit.buff / 6)
    _stat_bar(screen, fonts, PANEL.y + 144, "RANGE", f"{s['range']:.1f}", s["range"] / 12)

    specials = []
    if s["splash"] > 0:
        specials.append(f"Blast {s['splash']:.1f}")
    if s["pierce"]:
        specials.append(f"Pierce {s['pierce']}")
    if s["burn"]:
        specials.append(f"Burn {s['burn'][0]:.0f}/s")
    if s["aura"]:
        specials.append(f"Aura {s['aura'][0]:.1f}t x{s['aura'][1]:.2f}")
    if s["slow"]:
        specials.append(f"Slow {int((1 - s['slow'][0]) * 100)}%")
    draw_text(screen, fonts["tiny"], "   ".join(specials) or "Single target", (PANEL.x + 14, PANEL.y + 178), GREY)

    if unit.level == 4:
        draw_text(screen, fonts["tiny"], unit.ultimate["desc"], (PANEL.x + 14, PANEL.y + 200), ACCENT)
    elif unit.recipe_info:
        draw_text(screen, fonts["tiny"], unit.recipe_info["desc"], (PANEL.x + 14, PANEL.y + 200), ACCENT)


def _draw_ultimate_switch(screen, game, unit, fonts):
    """At level 4: the reinforce button, and the button that switches to the other ultimate."""
    if unit.level != 4:
        return
    cost = game.reinforce_cost(unit)
    maxed = unit.reinforce >= REINFORCE_MAX
    affordable = game.gold >= cost and not maxed
    label = (f"FULLY REINFORCED ({REINFORCE_MAX}/{REINFORCE_MAX})" if maxed else
             f"REINFORCE  [G]   $ {cost}   ({unit.reinforce}/{REINFORCE_MAX})")
    draw_panel(screen, UPGRADE_RECT, fill=(36, 84, 46) if affordable else BUTTON, slant=8)
    draw_text(screen, fonts["small"], label, UPGRADE_RECT.center, anchor="center")
    other = 1 - unit.ultimate_index
    switch = ULTIMATES[unit.faction][unit.kind][other]
    cost_text = f"$ {round(unit.cost * RESPEC_COST)}" if not game.wave_active else "between rounds"
    draw_panel(screen, ULT_RECTS[1], fill=(70, 52, 104) if not game.wave_active else BUTTON, slant=8)
    draw_text(screen, fonts["small"], f"SWITCH [{'AB'[other]}]  {switch['name']}",
              (ULT_RECTS[1].x + 12, ULT_RECTS[1].y + 6))
    draw_text(screen, fonts["tiny"], cost_text, (ULT_RECTS[1].x + 12, ULT_RECTS[1].y + 30), GREY)


def _draw_sell_button(screen, game, unit, fonts):
    """The sell button, with a countdown bar while a sale is armed."""
    refund = round(unit.spent * SELL_REFUND)
    armed = game.sell_armed(unit)
    draw_panel(screen, SELL_RECT, fill=(170, 40, 40) if armed else (90, 36, 36), slant=6)
    label = f"CONFIRM SELL +{refund}" if armed else f"SELL [X] +{refund}"
    draw_text(screen, fonts["tiny"], label, SELL_RECT.center, anchor="center")
    if armed:
        left = max(0.0, min(1.0, game.sell_time_left / SELL_CONFIRM_SECONDS))
        pygame.draw.rect(screen, (255, 120, 110), (SELL_RECT.x, SELL_RECT.bottom + 3, SELL_RECT.w * left, 3))


def _draw_combine(screen, game, unit, fonts):
    """The combine button. It names the unit the combination makes, and the price, when a partner is next to it."""
    if unit.level > 3:
        return
    if unit.recipe is not None:
        draw_panel(screen, COMBINE_RECT, fill=BUTTON, slant=8)
        draw_text(screen, fonts["tiny"], "COMBINED: cannot combine again", COMBINE_RECT.center, anchor="center")
        return
    option = game.combine_option(unit)
    if option is None:
        draw_panel(screen, COMBINE_RECT, fill=BUTTON, slant=8)
        draw_text(screen, fonts["tiny"], "COMBINE [C]: needs a unit next to it", COMBINE_RECT.center, anchor="center")
        return
    partner, _, recipe = option
    cost = game.combine_cost(unit, partner)
    affordable = game.gold >= cost
    draw_panel(screen, COMBINE_RECT, fill=(40, 70, 110) if affordable else BUTTON, slant=8)
    draw_text(screen, fonts["small"], f"COMBINE [C]  {recipe['name']}",
              (COMBINE_RECT.x + 12, COMBINE_RECT.centery), anchor="midleft")
    draw_text(screen, fonts["small"], f"$ {cost}", (COMBINE_RECT.right - 12, COMBINE_RECT.centery), anchor="midright")


def _draw_upgrade_or_ultimate(screen, game, unit, fonts):
    """Below level 3: the upgrade button. At level 3: the two ultimate choices."""
    if unit.level < 3:
        cost = game.upgrade_cost(unit)
        affordable = game.gold >= cost
        draw_panel(screen, UPGRADE_RECT, fill=(36, 84, 46) if affordable else BUTTON, slant=8)
        draw_text(screen, fonts["small"], f"UPGRADE  [U]   $ {cost}", UPGRADE_RECT.center, anchor="center")
    elif unit.level == 3:
        draw_text(screen, fonts["tiny"], "CHOOSE AN ULTIMATE", (PANEL.x + 14, PANEL.y + 222), ACCENT)
        for i, (rect, ult) in enumerate(zip(ULT_RECTS, ULTIMATES[unit.faction][unit.kind])):
            draw_panel(screen, rect, fill=(70, 52, 104), slant=8)
            draw_text(screen, fonts["small"], f"[{'AB'[i]}]  {ult['name']}", (rect.x + 12, rect.y + 6))
            draw_text(screen, fonts["tiny"], ult["desc"], (rect.x + 12, rect.y + 30), GREY)


# --- CENTRE: CURSOR, HIT MARKER AND BANNERS ---

def _draw_reticle(screen, pointer):
    x, y = pointer
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pygame.draw.line(screen, WHITE, (x + dx * 4, y + dy * 4), (x + dx * 9, y + dy * 9), 1)


def _draw_hitmarker(screen, pointer):
    x, y = pointer if pointer else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        pygame.draw.line(screen, WHITE, (x + sx * 5, y + sy * 5), (x + sx * 11, y + sy * 11), 2)


def _draw_banner(screen, game, fonts):
    fade = min(1.0, game.banner_life / 0.6)
    draw_text(screen, fonts["big"], game.banner, (SCREEN_WIDTH // 2, 140), dim_colour(WHITE, fade), anchor="midtop")


def _draw_narrative(screen, game, fonts):
    """The story line for the round, in a few centred lines under the banner, fading out at the end."""
    fade = min(1.0, game.narrative_life / 1.0)
    # Kept narrow so it clears the unit panel on the right
    for i, line in enumerate(textwrap.wrap(game.narrative, 50)[:3]):
        draw_text(screen, fonts["small"], line, (SCREEN_WIDTH // 2, 214 + i * 22), dim_colour((220, 210, 170), fade),
                  anchor="midtop")


def _draw_overrun(screen, game, fonts):
    shade(screen, 225)
    cx = SCREEN_WIDTH // 2
    report = game.report()
    draw_text(screen, fonts["big"], "OVERRUN", (cx, 200), RED, anchor="center")
    draw_text(screen, fonts["mid"], f"Reached round {report['round']}     Eliminated {report['kills']}", (cx, 270),
          WHITE, anchor="center")
    draw_text(screen, fonts["small"], "TOP DAMAGE", (cx - 200, 320), ACCENT)
    for i, (name, dmg, kills) in enumerate(report["damage"] or [("none", 0, 0)]):
        draw_text(screen, fonts["small"], f"{i + 1}. {name}  {dmg} dmg, {kills} kills", (cx - 200, 346 + i * 22),
              WHITE)
    draw_text(screen, fonts["small"], "MOST LEAKS", (cx + 40, 320), ACCENT)
    for i, (name, count) in enumerate(report["leaks"] or [("none", 0)]):
        draw_text(screen, fonts["small"], f"{i + 1}. {name}  x{count}", (cx + 40, 346 + i * 22), WHITE)
    draw_text(screen, fonts["small"], "R: back to the title screen", (cx, 470), GREY, anchor="center")
    for i, line in enumerate(textwrap.wrap(story.overrun_line(game.faction, game.wave), 96)[:2]):
        draw_text(screen, fonts["small"], line, (cx, 506 + i * 22), (220, 210, 170), anchor="center")


def draw_hud(screen, game, speed, fonts, pointer=None, audio=""):
    _draw_round(screen, game, fonts, speed)
    _draw_preview(screen, game, fonts)
    _draw_points(screen, game, fonts)
    _draw_feed(screen, game, fonts)
    _draw_radar(screen, game, fonts, game.selected_unit)
    _draw_audio(screen, fonts, audio)
    _draw_lives(screen, game, fonts)
    _draw_hotbar(screen, game, fonts)
    _draw_hint(screen, game, fonts)
    if game.selected_unit is not None and game.status == "playing":
        _draw_unit_panel(screen, game, fonts)
    if pointer and game.status == "playing":
        for role, rect in ROLE_RECTS.items():
            if rect.collidepoint(pointer):
                draw_tooltip(screen, fonts, game, role, pointer)
                break
    if pointer and game.status == "playing":
        _draw_reticle(screen, pointer)
    if game.hitmark > 0:
        _draw_hitmarker(screen, pointer)
    if game.banner_life > 0:
        _draw_banner(screen, game, fonts)
    if game.narrative_life > 0:
        _draw_narrative(screen, game, fonts)
    if game.status == "lost":
        _draw_overrun(screen, game, fonts)


def draw_tooltip(screen, fonts, game, role, pointer):
    """Hover card for a unit in the hotbar: cost and stats, and whether it can hit flyers."""
    spec = UNIT_TYPES[game.faction][role]
    rows = [spec["name"],
            f"Cost $ {spec['cost']}   Damage {spec['damage']:g}   Rate {spec['rate']:g}/s",
            f"Range {spec['range']:g}" + (f"   Blast {spec['splash']:g}" if spec.get("splash") else ""),
            "Flying enemies only" if spec.get("air_only") else
            "Can hit flying enemies" if role in AIR_ROLES else "Ground only"]
    width = 300
    height = 12 + 22 * len(rows)
    x = min(max(8, pointer[0] - width // 2), SCREEN_WIDTH - width - 8)
    y = ROLE_RECTS[role].y - height - 10
    box = pygame.Rect(x, y, width, height)
    draw_panel(screen, box, fill=(20, 22, 28), accent=True)
    for i, row in enumerate(rows):
        draw_text(screen, fonts["small"] if i == 0 else fonts["tiny"], row, (box.x + 12, box.y + 10 + i * 22),
              ACCENT if i == 0 else WHITE)


