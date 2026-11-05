import pygame

# Sprites are drawn on a 16x24 pixel canvas and scaled to their size on screen

UNIT_BODY = {"human": (66, 104, 186), "zombie": (96, 52, 124)}
UNIT_TRIM = {"human": (196, 210, 240), "zombie": (214, 160, 240)}
ULT_GLOW = {"human": [(255, 226, 110), (120, 220, 255)], "zombie": [(200, 255, 80), (230, 130, 255)]}
ENEMY_BODY = {"zombie": (138, 120, 96), "human": (150, 58, 52)}
ZOMBIE_SKIN = (116, 150, 92)
SKIN = (222, 186, 150)
DARK = (28, 28, 34)

_cache = {}


def _canvas():
    return pygame.Surface((16, 24), pygame.SRCALPHA)


def _shadow(s):
    pygame.draw.ellipse(s, (0, 0, 0, 110), (3, 21, 10, 3))


OUTLINE = (24, 22, 30)


def _outlined(s):
    """The sprite with a one pixel dark outline, so it reads against the grass and the path."""
    edge = pygame.mask.from_surface(s).to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    out = _canvas()
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(edge, (dx, dy))
    out.blit(s, (0, 0))
    return out


def unit_sprite(faction, kind, level, ult_index):
    key = ("unit", faction, kind, level, ult_index)
    if key not in _cache:
        _cache[key] = _outlined(_make_unit(faction, kind, level, ult_index))
    return _cache[key]


def _weapon(s, faction, kind):
    if kind == "rapid":
        pygame.draw.rect(s, DARK, (10, 11, 6, 2))  # Rifle
    elif kind == "sniper":
        pygame.draw.rect(s, DARK, (1, 10, 14, 1))  # Long rifle
        pygame.draw.rect(s, (96, 72, 48), (1, 11, 4, 2))  # Stock
    elif kind == "splash":
        pygame.draw.rect(s, (74, 74, 84), (1, 9, 6, 5))  # Launcher on the shoulder
        pygame.draw.rect(s, DARK, (2, 7, 3, 2))
    elif kind == "support":
        if faction == "human":
            pygame.draw.rect(s, (240, 240, 240), (7, 9, 2, 4))  # Medic cross on the chest
            pygame.draw.rect(s, (210, 40, 40), (6, 10, 4, 2))
        else:
            pygame.draw.rect(s, (130, 255, 150), (7, 9, 2, 3))  # Glowing sac on the chest
            pygame.draw.rect(s, (60, 180, 90), (6, 12, 4, 1))
    elif kind == "flame":
        pygame.draw.rect(s, (110, 110, 120), (1, 8, 3, 7))  # Tank on the back
        pygame.draw.rect(s, (255, 140, 50), (10, 11, 5, 2))  # Nozzle
    elif kind == "artillery":
        pygame.draw.rect(s, DARK, (2, 5, 3, 9))  # Tube
        pygame.draw.rect(s, (96, 72, 48), (1, 13, 5, 2))  # Base plate
    elif kind == "flak":
        pygame.draw.rect(s, (84, 96, 84), (1, 7, 3, 7))  # Stand on the back
        pygame.draw.rect(s, DARK, (9, 9, 6, 1))  # Twin barrels pointing up
        pygame.draw.rect(s, DARK, (9, 11, 6, 1))


def _make_unit(faction, kind, level, ult_index):
    s = _canvas()
    _shadow(s)
    body = UNIT_BODY[faction]
    pygame.draw.rect(s, DARK, (5, 16, 3, 6))  # Legs
    pygame.draw.rect(s, DARK, (9, 16, 3, 6))
    pygame.draw.rect(s, body, (4, 8, 8, 9))  # Torso
    pygame.draw.rect(s, UNIT_TRIM[faction], (4, 8, 8, 1))
    if faction == "human":
        pygame.draw.rect(s, SKIN, (5, 3, 6, 5))  # Face
        pygame.draw.rect(s, (62, 74, 52), (4, 1, 8, 3))  # Helmet
    else:
        pygame.draw.rect(s, ZOMBIE_SKIN, (5, 2, 6, 6))
        s.set_at((6, 4), DARK)  # Eyes
        s.set_at((9, 4), DARK)
    _weapon(s, faction, kind)
    # One pip on the chest per upgrade. The ultimate level gets a glowing outline
    for i in range(min(level, 4) - 1):
        pygame.draw.rect(s, (255, 226, 110), (5 + i * 2, 13, 1, 1))
    if level >= 4:
        pygame.draw.rect(s, ULT_GLOW[faction][ult_index], (3, 7, 10, 11), 1)
    return s


def enemy_sprite(faction, kind):
    key = ("enemy", faction, kind)
    if key not in _cache:
        _cache[key] = _outlined(_make_enemy(faction, kind))
    return _cache[key]


def _make_enemy(faction, kind):
    if kind == "crow":
        return _make_crow()
    if kind == "drone":
        return _make_drone()
    s = _canvas()
    _shadow(s)
    body = ENEMY_BODY[faction]
    big = kind in ("brute", "heavy", "boss")
    pygame.draw.rect(s, DARK, (5, 16, 3, 6))
    pygame.draw.rect(s, DARK, (9, 16, 3, 6))
    if big:
        pygame.draw.rect(s, body, (2, 6, 12, 11))
    else:
        pygame.draw.rect(s, body, (4, 8, 8, 9))
    if faction == "zombie":
        pygame.draw.rect(s, ZOMBIE_SKIN, (5, 2, 6, 6))
        s.set_at((6, 4), (200, 40, 40))  # Red eyes
        s.set_at((9, 4), (200, 40, 40))
        if kind == "runner":
            pygame.draw.rect(s, body, (2, 9, 3, 2))  # Arms reaching forward
            pygame.draw.rect(s, body, (11, 8, 3, 2))
        else:
            pygame.draw.rect(s, body, (11, 10, 4, 2))
        if big:
            pygame.draw.rect(s, (70, 60, 50), (3, 13, 3, 2))  # Torn clothes
    else:
        pygame.draw.rect(s, SKIN, (5, 4, 6, 4))
        pygame.draw.rect(s, (60, 64, 52), (4, 1, 8, 3))  # Helmet
        pygame.draw.rect(s, DARK, (10, 11, 6, 2))  # Rifle
    if kind == "boss":
        pygame.draw.rect(s, (230, 180, 50), (4, 0, 8, 2))  # Gold crown or cap badge: marks the boss
        pygame.draw.rect(s, (230, 180, 50), (5, 14, 6, 1))  # Belt
    return s


def _make_crow():
    """A black bird with its wings out, seen from the side."""
    s = _canvas()
    black = (30, 28, 36)
    pygame.draw.polygon(s, black, [(0, 8), (7, 6), (6, 11)])  # Left wing
    pygame.draw.polygon(s, black, [(16, 8), (9, 6), (10, 11)])  # Right wing
    pygame.draw.ellipse(s, black, (5, 7, 6, 5))  # Body
    pygame.draw.rect(s, (230, 190, 60), (4, 9, 2, 1))  # Beak
    s.set_at((7, 8), (240, 240, 240))  # Eye
    return s


def _make_drone():
    """A quadcopter: a grey body with rotor arms and a red light."""
    s = _canvas()
    pygame.draw.line(s, (90, 96, 104), (1, 7), (14, 7))  # Rotor arm
    pygame.draw.circle(s, (170, 176, 184), (2, 7), 2)  # Rotors
    pygame.draw.circle(s, (170, 176, 184), (13, 7), 2)
    pygame.draw.rect(s, (66, 70, 78), (5, 8, 6, 4))  # Body
    pygame.draw.rect(s, (220, 60, 60), (7, 10, 2, 1))  # Light
    pygame.draw.line(s, DARK, (8, 12), (8, 14))  # Sensor stalk
    return s


# --- DOODADS AND MARKERS ---

_doodad_cache = {}


def doodad_sprite(kind):
    if kind not in _doodad_cache:
        s = _canvas()
        _shadow(s)
        if kind == "tree":
            pygame.draw.rect(s, (96, 66, 40), (7, 14, 2, 8))  # Trunk
            pygame.draw.circle(s, (34, 90, 42), (8, 9), 6)  # Canopy
            pygame.draw.circle(s, (52, 120, 58), (6, 7), 3)  # Highlight
        elif kind == "rock":
            pygame.draw.polygon(s, (120, 120, 126), [(2, 21), (4, 15), (9, 13), (14, 17), (14, 21)])
            pygame.draw.polygon(s, (150, 150, 156), [(4, 15), (9, 13), (8, 16)])
        elif kind == "bush":
            pygame.draw.ellipse(s, (44, 110, 50), (2, 13, 12, 8))
            pygame.draw.ellipse(s, (70, 146, 72), (4, 14, 5, 3))
            pygame.draw.ellipse(s, (30, 84, 40), (8, 17, 6, 3))  # Shaded underside
        elif kind == "flower":
            pygame.draw.line(s, (60, 130, 60), (8, 22), (8, 15))  # Stem
            pygame.draw.rect(s, (70, 150, 70), (5, 18, 3, 1))  # Leaf
            pygame.draw.circle(s, (255, 120, 160), (8, 13), 3)  # Petals
            pygame.draw.circle(s, (255, 230, 90), (8, 13), 1)  # Centre
            pygame.draw.circle(s, (255, 240, 240), (4, 17), 2)
        elif kind == "stump":
            pygame.draw.rect(s, (110, 76, 46), (4, 16, 9, 6))  # Cut wood
            pygame.draw.ellipse(s, (160, 118, 72), (4, 14, 9, 4))  # Cut top
            pygame.draw.ellipse(s, (120, 84, 50), (6, 15, 5, 2))  # Rings
        elif kind == "dead_tree":
            pygame.draw.rect(s, (92, 84, 74), (7, 8, 2, 14))  # Bare trunk
            pygame.draw.line(s, (92, 84, 74), (8, 11), (3, 5))  # Branches
            pygame.draw.line(s, (92, 84, 74), (8, 9), (12, 4))
            pygame.draw.line(s, (92, 84, 74), (8, 14), (12, 12))
        elif kind == "ruin":
            pygame.draw.rect(s, (128, 124, 118), (2, 15, 12, 6))  # Blocks
            pygame.draw.rect(s, (150, 146, 138), (2, 15, 12, 1))
            pygame.draw.rect(s, (104, 100, 96), (5, 11, 4, 4))  # Broken course above
            pygame.draw.line(s, (84, 80, 76), (8, 15), (7, 21))  # Crack
        _doodad_cache[kind] = _outlined(s)
    return _doodad_cache[kind]


_marker_cache = {}


def marker_sprite(colour):
    """A flag on a pole, in the marker's colour."""
    if colour not in _marker_cache:
        s = _canvas()
        pygame.draw.rect(s, (60, 60, 66), (3, 2, 1, 21))  # Pole
        pygame.draw.polygon(s, colour, [(4, 2), (13, 4), (4, 7)])  # Flag
        pygame.draw.polygon(s, tuple(c // 2 for c in colour), [(4, 7), (13, 4), (13, 5), (4, 8)])
        _marker_cache[colour] = s
    return _marker_cache[colour]
