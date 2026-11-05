import math

import pygame

from config import RENDER_W, RENDER_H, UNIT_TYPES, SHOT_COLOURS, DOODAD_HEIGHT, START_COLOUR, END_COLOUR, FLY_HEIGHT
from projectiles import Projectile, Puff, Floater, ARC_KINDS
from pickups import LABELS, COLOURS as PICKUP_COLOURS
from sprites import unit_sprite, enemy_sprite, doodad_sprite, marker_sprite
from world import cell_corners

SPRITE_SCALE = 1.3  # Makes the 16x24 sprites read clearly at the render size. Multiplies the heights in config
SELECT = (250, 200, 80)
RANGE_RING = (235, 235, 235)
GOOD = (90, 220, 120)
BAD = (230, 90, 90)
BURN = (255, 120, 40)
BURN_FILL = (120, 40, 16)
BLUE = (110, 170, 255)


# --- DRAWING ON THE FLOOR ---

def _ground_circle(scene, camera, cx, cy, radius, colour):
    points = []
    for i in range(32):
        a = 2 * math.pi * i / 32
        hit = camera.project(cx + radius * math.cos(a), cy + radius * math.sin(a))
        if hit:
            points.append(hit[:2])
    if len(points) > 2:
        pygame.draw.lines(scene, colour, True, points, 1)


def _ground_disc(scene, camera, cx, cy, radius, fill, outline):
    points = []
    for i in range(24):
        a = 2 * math.pi * i / 24
        hit = camera.project(cx + radius * math.cos(a), cy + radius * math.sin(a))
        if hit:
            points.append(hit[:2])
    if len(points) > 2:
        pygame.draw.polygon(scene, fill, points)
        pygame.draw.lines(scene, outline, True, points, 1)


def _ground_tile(scene, camera, col, row, colour):
    points = [camera.project(x, y)[:2] for x, y in cell_corners(col, row)]
    pygame.draw.lines(scene, colour, True, points, 1)


# --- DRAWING UPRIGHT THINGS ---

def _billboard(scene, camera, image, x, y, height, z=0.0):
    """Draw a sprite standing on the floor at (x, y). Returns (screen x, screen y, pixel height) or None."""
    hit = camera.project(x, y, z)
    if hit is None:
        return None
    sx, sy, depth = hit
    h = int(height * SPRITE_SCALE * camera.focal / depth)
    if h < 2:
        return None
    w = max(2, int(image.get_width() * h / image.get_height()))
    scene.blit(pygame.transform.scale(image, (w, h)), (int(sx - w / 2), int(sy - h)))
    return sx, sy, h


def _depth(camera, x, y):
    hit = camera.project(x, y)
    return hit[2] if hit else 0.0


def _draw_unit(scene, camera, unit):
    _billboard(scene, camera, unit_sprite(unit.faction, unit.kind, unit.level, unit.ultimate_index),
               unit.x, unit.y, UNIT_TYPES[unit.faction][unit.kind]["height"])
    if unit.flash > 0:  # Muzzle flash at the gun
        hit = camera.project(unit.x, unit.y, UNIT_TYPES[unit.faction][unit.kind]["height"] * 0.8)
        if hit:
            pygame.draw.circle(scene, (255, 240, 180), (int(hit[0]), int(hit[1])), 2)


def _draw_enemy(scene, camera, enemy):
    if enemy.flying:  # A dark patch on the ground underneath, so the height reads
        ground = camera.project(enemy.x, enemy.y)
        if ground:
            pygame.draw.circle(scene, (20, 20, 24), (int(ground[0]), int(ground[1])),
                               max(1, int(0.25 * camera.focal / ground[2])))
    z = FLY_HEIGHT if enemy.flying else 0.0
    result = _billboard(scene, camera, enemy_sprite(enemy.faction, enemy.kind), enemy.x, enemy.y,
                        enemy.spec["height"], z)
    if result is None:
        return
    sx, sy, h = result
    bar_w = max(6, h // 2)
    bar_y = int(sy - h - 3)
    pygame.draw.rect(scene, (60, 20, 20), (int(sx - bar_w / 2), bar_y, bar_w, 2))
    fill = bar_w * max(0.0, enemy.hp) / enemy.max_hp
    pygame.draw.rect(scene, (90, 220, 90), (int(sx - bar_w / 2), bar_y, int(fill), 2))
    if enemy.slow_time > 0:
        pygame.draw.circle(scene, BLUE, (int(sx), bar_y - 3), 1)
    if enemy.flash > 0:
        pygame.draw.circle(scene, (255, 255, 255), (int(sx), int(sy - h * 0.6)), max(1, h // 5))


def _draw_projectile(scene, camera, p):
    colour = SHOT_COLOURS[p.faction][p.kind]
    samples = [camera.project(x, y, z) for x, y, z in p.trail + [(p.x, p.y, p.z)]]
    samples = [s for s in samples if s is not None]
    if not samples:
        return
    head_x, head_y, head_depth = samples[-1]
    if p.kind in ARC_KINDS:
        ground = camera.project(p.x, p.y, 0.0)  # Shadow of the shell on the floor
        if ground:
            pygame.draw.circle(scene, (30, 30, 30), (int(ground[0]), int(ground[1])), 1)
        for sx, sy, _ in samples[:-1]:  # Trail of dots
            pygame.draw.circle(scene, colour, (int(sx), int(sy)), 1)
        radius = max(1, int(0.12 * camera.focal / head_depth))
        pygame.draw.circle(scene, colour, (int(head_x), int(head_y)), radius)
        pygame.draw.circle(scene, (255, 250, 230), (int(head_x), int(head_y)), max(1, radius - 1))
    else:
        if len(samples) > 1:
            pygame.draw.lines(scene, colour, False, [(sx, sy) for sx, sy, _ in samples], 1)
        pygame.draw.circle(scene, (255, 255, 255), (int(head_x), int(head_y)), 1)


def _draw_doodad(scene, camera, x, y, kind):
    _billboard(scene, camera, doodad_sprite(kind), x, y, DOODAD_HEIGHT[kind])


_label_font = None


def _label(scene, text, sx, top, colour):
    global _label_font
    if _label_font is None:
        _label_font = pygame.font.SysFont(None, 14)
    surf = _label_font.render(text, True, colour)
    scene.blit(surf, (int(sx - surf.get_width() / 2), int(top - surf.get_height())))


def _draw_markers(scene, camera, game_map):
    """Start and end of the route: a pulsing ring on the floor, and a flag with a label."""
    pulse = 0.45 + 0.06 * math.sin(pygame.time.get_ticks() / 180)
    for (x, y), colour, text in ((game_map.start, START_COLOUR, "START"), (game_map.end, END_COLOUR, "END")):
        _ground_circle(scene, camera, x, y, pulse, colour)
        result = _billboard(scene, camera, marker_sprite(colour), x, y, 1.6)
        if result:
            sx, sy, h = result
            _label(scene, text, sx, sy - h - 2, colour)


def _draw_zone(scene, camera, zone):
    # Flicker the fill between two shades so it looks like it is burning
    flicker = BURN_FILL if int(zone.life * 10) % 2 else (150, 60, 20)
    _ground_disc(scene, camera, zone.x, zone.y, zone.radius, flicker, BURN)


COMBO_RING = (255, 196, 40)  # Same-type combo: a solid gold ring
SQUAD_RING = (120, 230, 210)  # Mixed squad: a wider teal ring, so the two read apart without colour


def _draw_combo_rings(scene, camera, units):
    for unit in units:
        if unit.mixed:
            _ground_circle(scene, camera, unit.x, unit.y, 0.58, SQUAD_RING)
        if unit.group > 1:
            _ground_circle(scene, camera, unit.x, unit.y, 0.42, COMBO_RING)


def _draw_pickup(scene, camera, pickup):
    colour = PICKUP_COLOURS[pickup.kind]
    # Blink in the last two seconds so a pickup about to fade is noticed
    if pickup.life < 2.0 and int(pickup.life * 6) % 2:
        return
    _ground_disc(scene, camera, pickup.x, pickup.y, 0.34, colour, (255, 255, 255))
    hit = camera.project(pickup.x, pickup.y, 0.4)
    if hit is not None:
        _label(scene, LABELS[pickup.kind], hit[0], hit[1] - 4, (20, 20, 20))


def _draw_floater(scene, camera, floater):
    hit = camera.project(floater.x, floater.y, 0.9)
    if hit is None:
        return
    rise = (1 - floater.life / floater.max_life) * 14  # Numbers drift up over their life
    _label(scene, floater.text, hit[0], hit[1] - rise, floater.colour)


def _draw_puff(scene, camera, puff):
    hit = camera.project(puff.x, puff.y, 0.2)
    if hit is None:
        return
    radius = max(1, round(puff.size * puff.life / puff.max_life))
    pygame.draw.circle(scene, puff.colour, (int(hit[0]), int(hit[1])), radius)


def draw_scene(camera, game, hover):
    """Draw the 3D view of a game at render size. Returns the surface, which the caller scales up."""
    scene = pygame.Surface((RENDER_W, RENDER_H))
    camera.use_map(game.map)
    camera.render_floor(scene)

    _draw_markers(scene, camera, game.map)

    for zone in game.zones:
        _draw_zone(scene, camera, zone)
    for pickup in game.pickups:
        _draw_pickup(scene, camera, pickup)
    _draw_combo_rings(scene, camera, game.units)

    # Range and placement hints on the floor
    if game.selected_unit is not None:
        unit = game.selected_unit
        _ground_circle(scene, camera, unit.x, unit.y, unit.stats["range"], SELECT)
        _ground_circle(scene, camera, unit.x, unit.y, 0.45, SELECT)
    elif hover is not None:
        col, row = hover
        ok = game.placement_error(col, row) is None
        _ground_tile(scene, camera, col, row, GOOD if ok else BAD)
        _ground_circle(scene, camera, col + 0.5, row + 0.5,
                       UNIT_TYPES[game.faction][game.selected]["range"], RANGE_RING)

    # Doodads, units and enemies, far first so nearer ones cover them
    drawables = [(_depth(camera, x, y), (lambda x=x, y=y, k=kind: _draw_doodad(scene, camera, x, y, k)))
                 for x, y, kind in game.map.doodads]
    for u in game.units:
        drawables.append((_depth(camera, u.x, u.y), lambda u=u: _draw_unit(scene, camera, u)))
    for e in game.enemies:
        drawables.append((_depth(camera, e.x, e.y), lambda e=e: _draw_enemy(scene, camera, e)))
    drawables.sort(key=lambda d: -d[0])
    for _, draw in drawables:
        draw()

    for projectile in game.projectiles:
        if isinstance(projectile, Projectile):
            _draw_projectile(scene, camera, projectile)
    for effect in game.effects:
        if isinstance(effect, Puff):
            _draw_puff(scene, camera, effect)
        elif isinstance(effect, Floater):
            _draw_floater(scene, camera, effect)
    return scene
