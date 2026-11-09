import math

import pygame

from config import (RENDER_W, RENDER_H, UNIT_TYPES, SHOT_COLOURS, DOODAD_HEIGHT, START_COLOUR, END_COLOUR, FLY_HEIGHT,
                    CHARGE_COLOUR, CHARGE_KILLS, ATTACK_ANIM_SECONDS, MOVE_SECONDS)
from projectiles import Projectile, Puff, Floater, Blast, ARC_KINDS
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

def _billboard(scene, camera, image, x, y, height, z=0.0, alpha=255):
    """Draw a sprite standing on the floor at (x, y). Returns (screen x, screen y, pixel height) or None."""
    hit = camera.project(x, y, z)
    if hit is None:
        return None
    sx, sy, depth = hit
    h = int(height * SPRITE_SCALE * camera.focal / depth)
    if h < 2:
        return None
    w = max(2, int(image.get_width() * h / image.get_height()))
    scaled = pygame.transform.scale(image, (w, h))
    if alpha < 255:  # A fading sprite (a fallen enemy)
        scaled.set_alpha(alpha)
    scene.blit(scaled, (int(sx - w / 2), int(sy - h)))
    return sx, sy, h


def _depth(camera, x, y):
    hit = camera.project(x, y)
    return hit[2] if hit else 0.0


MUZZLE_SIZE = {"sniper": 3, "splash": 3, "artillery": 4, "rocket": 3, "flame": 3}  # Bigger guns flash bigger


CHARGE_EMPTY = (40, 34, 20)  # The charge meter's track, and its fill before the unit is charged
CHARGE_FILL = (200, 150, 60)


def _charge_meter(scene, sx, top, unit):
    """A thin bar above a charging unit: it fills with kills, and flashes gold once the charge is full."""
    width, left, y = 12, int(sx - 6), int(top)
    pygame.draw.rect(scene, CHARGE_EMPTY, (left, y, width, 3))
    fill = int(width * unit.kill_meter / CHARGE_KILLS)
    if unit.charged:
        colour = CHARGE_COLOUR if int(pygame.time.get_ticks() / 150) % 2 else (255, 255, 240)
    else:
        colour = CHARGE_FILL
    if fill:
        pygame.draw.rect(scene, colour, (left, y, fill, 3))


def _draw_unit(scene, camera, unit):
    """A unit firing: the sprite is pushed back by its recoil and settles, the muzzle flashes in its shot's colour
    (gold for a charged attack), and a support unit's aura pulses out across the floor. A charging unit has a meter
    above it. A unit that was just moved hops from its old tile and steps as it lands."""
    fade = unit.attack_time / ATTACK_ANIM_SECONDS  # 1 on the shot, falling to 0 as the animation ends
    x, y = unit.x + unit.recoil[0] * fade, unit.y + unit.recoil[1] * fade
    lift, frame = 0.0, 0
    kit = unit.combo_kit
    if kit and kit["anim"] == "bob":  # A combined unit that bobs as it stands
        lift = 0.06 + 0.06 * math.sin(pygame.time.get_ticks() / 250)
    if unit.move_time > 0 and unit.move_from is not None:
        p = 1 - unit.move_time / MOVE_SECONDS  # 0 at the old tile, 1 at the new one
        x = unit.move_from[0] + (x - unit.move_from[0]) * p
        y = unit.move_from[1] + (y - unit.move_from[1]) * p
        lift = 0.35 * math.sin(math.pi * p)
        frame = int(p * 4) % 2
    placed = _billboard(scene, camera, unit_sprite(unit.faction, unit.kind, unit.level, unit.ultimate_index,
                                                   unit.recipe, frame), x, y, unit.height, lift)
    if placed is not None and unit.can_charge and (unit.kill_meter or unit.charged):  # Shown once it has kills
        sx, sy, h = placed
        _charge_meter(scene, sx, sy - h - 6, unit)
    if kit and placed is not None:
        _combo_anim(scene, camera, unit, kit["anim"], placed)
    if unit.flash > 0:  # Muzzle flash at the gun
        hit = camera.project(x, y, unit.height * 0.8)
        if hit:
            colour = CHARGE_COLOUR if unit.attack_charged else (kit["colour"] if kit else SHOT_COLOURS[unit.faction][unit.kind])
            size = MUZZLE_SIZE.get(unit.kind, 2) + (2 if unit.attack_charged else 0)
            pygame.draw.circle(scene, colour, (int(hit[0]), int(hit[1])), size)
            pygame.draw.circle(scene, (255, 250, 230), (int(hit[0]), int(hit[1])), max(1, size - 2))
    if unit.kind == "support" and fade > 0:  # The aura pulses out from the medic and fades
        _ground_circle(scene, camera, unit.x, unit.y, unit.stats["aura"][0] * (1.2 - 0.2 * fade),
                       SHOT_COLOURS[unit.faction]["support"])


def _draw_enemy(scene, camera, enemy):
    if enemy.flying:  # A dark patch on the ground underneath, so the height reads
        ground = camera.project(enemy.x, enemy.y)
        if ground:
            pygame.draw.circle(scene, (20, 20, 24), (int(ground[0]), int(ground[1])),
                               max(1, int(0.25 * camera.focal / ground[2])))
    z = FLY_HEIGHT if enemy.flying else 0.0
    frame = 0 if enemy.flying else int(enemy.walk * 4) % 2  # Walkers step every quarter tile; flyers keep still
    result = _billboard(scene, camera, enemy_sprite(enemy.faction, enemy.kind, frame), enemy.x, enemy.y,
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


def _draw_corpse(scene, camera, corpse):
    """A killed enemy collapses: it squashes down to the ground and fades. A flyer drops from the air as it goes."""
    p = corpse.progress
    z = FLY_HEIGHT * (1 - p) if corpse.flying else 0.0
    _billboard(scene, camera, enemy_sprite(corpse.faction, corpse.kind), corpse.x, corpse.y,
               corpse.height * (1 - 0.6 * p), z, alpha=int(255 * (1 - p)))


def _combo_trail(scene, samples, colour, style):
    """The trail of a combined unit's shot, in its kit's style. `samples` are the screen points, oldest first."""
    pts = [(int(sx), int(sy)) for sx, sy, _ in samples]
    if style == "sparks":  # Bright flecks, dropping off the path
        for i, (x, y) in enumerate(pts):
            if i % 2 == 0:
                pygame.draw.circle(scene, (255, 250, 220) if i % 4 == 0 else colour, (x + (i % 4) - 1, y + 1), 1)
    elif style == "smoke":  # Faint, wide puffs in the colour greyed out
        grey = tuple((c + 90) // 2 for c in colour)
        for x, y in pts:
            pygame.draw.circle(scene, grey, (x, y), 2)
    elif style == "ribbon" and len(pts) > 1:  # A wavering ribbon
        wave = [(x, y + (1 if i % 2 else -1)) for i, (x, y) in enumerate(pts)]
        pygame.draw.lines(scene, colour, False, wave, 2)
    elif style == "beads":  # Beads strung along the path
        for i, (x, y) in enumerate(pts):
            if i % 2 == 0:
                pygame.draw.circle(scene, colour, (x, y), 1)
    elif style == "embers":  # Embers flickering between the colour and a hot yellow
        for i, (x, y) in enumerate(pts):
            pygame.draw.circle(scene, (255, 230, 120) if i % 2 else colour, (x, y), 1)
    elif style == "bolt" and len(pts) > 1:  # A jagged, crackling line
        zig = [(x + (2 if i % 2 else -2), y) for i, (x, y) in enumerate(pts)]
        pygame.draw.lines(scene, colour, False, zig, 1)


def _combo_anim(scene, camera, unit, anim, placed):
    """A combined unit's own animation, drawn over its sprite: a spinning dot, a beating ring, or rising steam.
    A bob is part of where the unit is drawn, so it is not drawn here."""
    sx, sy, h = placed
    colour = unit.combo_kit["colour"]
    ticks = pygame.time.get_ticks()
    if anim == "spin":  # A dot orbits the head
        a = ticks / 180
        pygame.draw.circle(scene, colour, (int(sx + math.cos(a) * 4), int(sy - h * 0.9 + math.sin(a) * 2)), 1)
    elif anim == "pulse":  # A ring beats on the ground under the unit
        beat = 0.5 + 0.5 * math.sin(ticks / 200)
        _ground_circle(scene, camera, unit.x, unit.y, 0.35 + 0.15 * beat, colour)
    elif anim == "vent":  # Steam rises from the top, and fades as it goes
        steam = tuple((c + 210) // 2 for c in colour)
        for i in range(3):
            rise = (ticks / 40 + i * 10) % 24
            pygame.draw.circle(scene, steam, (int(sx + (i - 1) * 2), int(sy - h - rise)), 2)


def _draw_projectile(scene, camera, p):
    colour = p.colour
    samples = [camera.project(x, y, z) for x, y, z in p.trail + [(p.x, p.y, p.z)]]
    samples = [s for s in samples if s is not None]
    if not samples:
        return
    head_x, head_y, head_depth = samples[-1]
    if p.charged and len(samples) > 1:  # A charged attack has a wide gold trail under the shot
        pygame.draw.lines(scene, CHARGE_COLOUR, False, [(sx, sy) for sx, sy, _ in samples], 3)
    if p.kind in ARC_KINDS:
        ground = camera.project(p.x, p.y, 0.0)  # Shadow of the shell on the floor
        if ground:
            pygame.draw.circle(scene, (30, 30, 30), (int(ground[0]), int(ground[1])), 1)
        for sx, sy, _ in samples[:-1]:  # A faint trail under the smoke puffs
            pygame.draw.circle(scene, colour, (int(sx), int(sy)), 1)
        radius = max(1, int(0.12 * camera.focal / head_depth))
        if p.shot == "heavy":  # A heavy combined shell is a bigger, dark-cased round
            radius += 2
        pygame.draw.circle(scene, (40, 36, 32), (int(head_x), int(head_y)), radius + 1)
        pygame.draw.circle(scene, colour, (int(head_x), int(head_y)), radius)
        pygame.draw.circle(scene, (255, 250, 230), (int(head_x), int(head_y)), max(1, radius - 1))
    elif p.kind == "rocket":
        _draw_missile(scene, samples, colour)
    elif p.kind == "flame":
        _draw_flame_jet(scene, samples, colour, p.faction)
    else:
        _draw_direct_shot(scene, samples, colour, p.shot, wide=p.kind == "sniper")
    if p.kit:  # A combined unit's own trail
        _combo_trail(scene, samples, colour, p.kit["trail"])
    if p.charged:  # A ring round the head marks it as a charged attack
        pygame.draw.circle(scene, CHARGE_COLOUR, (int(head_x), int(head_y)), 4, 1)
    if p.shot == "cluster":  # Three sub-shots orbit the head
        spin = pygame.time.get_ticks() / 60
        for i in range(3):
            a = spin + i * 2.09
            pygame.draw.circle(scene, colour, (int(head_x + math.cos(a) * 3), int(head_y + math.sin(a) * 3)), 1)


def _draw_direct_shot(scene, samples, colour, style, wide):
    """A bullet or armour-piercing round, in the look of the combined unit that fired it (its shot style)."""
    pts = [(sx, sy) for sx, sy, _ in samples]
    head = pts[-1]
    if style == "beam" and len(pts) > 1:  # A glowing beam with a white core
        pygame.draw.lines(scene, tuple(c // 2 for c in colour), False, pts, 3)
        pygame.draw.lines(scene, colour, False, pts, 1)
        pygame.draw.lines(scene, (255, 255, 255), False, pts, 1)
    elif style == "twin" and len(pts) > 1:  # Two tracers side by side
        dx, dy = head[0] - pts[0][0], head[1] - pts[0][1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        for side in (-1.0, 1.0):
            pygame.draw.lines(scene, colour, False, [(x + nx * side, y + ny * side) for x, y in pts], 1)
    elif style == "barrage" and len(pts) > 1:  # Three streaks spread across the path
        for offset in (-2, 0, 2):
            pygame.draw.lines(scene, colour, False, [(x, y + offset) for x, y in pts], 1)
    else:
        width = 2 if wide or style == "heavy" else 1
        if len(pts) > 1:
            pygame.draw.lines(scene, colour, False, pts, width)
        if style == "heavy":  # A heavy round is a big glowing ball
            pygame.draw.circle(scene, colour, (int(head[0]), int(head[1])), 3)
    pygame.draw.circle(scene, (255, 255, 255), (int(head[0]), int(head[1])), 2 if wide or style == "heavy" else 1)


def _draw_missile(scene, samples, colour):
    """A missile with a hot exhaust: the trail runs from orange at the back to its own colour at the nose."""
    exhaust = (255, 170, 70)
    count = len(samples)
    for i in range(1, count):
        t = i / count
        mixed = tuple(int(e + (c - e) * t) for e, c in zip(exhaust, colour))
        pygame.draw.line(scene, mixed, samples[i - 1][:2], samples[i][:2], 2 if t > 0.5 else 1)
    hx, hy, _ = samples[-1]
    pygame.draw.circle(scene, (255, 250, 230), (int(hx), int(hy)), 1)


def _draw_flame_jet(scene, samples, colour, faction):
    """A jet of fire: dots along the path that flicker, biggest and brightest at the nozzle end."""
    tick = pygame.time.get_ticks() // 70
    hot = (255, 230, 120) if faction == "human" else (235, 255, 170)
    count = len(samples)
    for i, (sx, sy, _) in enumerate(samples):
        t = (i + 1) / count  # 1 at the head of the jet
        size = 1 + round(2.5 * t) + ((tick + i) % 2)
        pygame.draw.circle(scene, hot if t > 0.7 else colour, (int(sx), int(sy)), size)


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


ACID_OUTLINE = (200, 255, 120)
ACID_FILLS = ((96, 168, 46), (130, 210, 70))  # The acid pool flickers between these two greens
BUBBLE = (222, 255, 150)


def _draw_zone(scene, camera, zone):
    """Fire where a human shot landed, acid where a zombie shot did. Both fade out as the zone runs down, and the
    flames or bubbles rise from fixed places in it."""
    fraction = max(0.0, zone.life / zone.max_life)
    shown = zone.spots[:max(1, round(len(zone.spots) * fraction))]
    t = pygame.time.get_ticks() / 1000
    if zone.faction == "zombie":
        _draw_acid(scene, camera, zone, shown, t)
    else:
        _draw_fire(scene, camera, zone, shown, t)


def _draw_fire(scene, camera, zone, shown, t):
    # Flicker the fill between two shades so it looks like it is burning
    flicker = BURN_FILL if int(zone.life * 10) % 2 else (150, 60, 20)
    _ground_disc(scene, camera, zone.x, zone.y, zone.radius, flicker, BURN)
    for dx, dy, phase in shown:
        height = 0.5 + 0.25 * math.sin(t * 9 + phase * 6.3) + 0.12 * math.sin(t * 17 + phase * 11)
        _flame_tongue(scene, camera, zone.x + dx, zone.y + dy, max(0.12, height))


def _flame_tongue(scene, camera, x, y, height):
    """One tongue of fire standing on the floor at (x, y): an orange tip with a yellow core."""
    left, right = camera.project(x - 0.18, y, 0.0), camera.project(x + 0.18, y, 0.0)
    tip = camera.project(x, y, height)
    if left is None or right is None or tip is None:
        return
    pygame.draw.polygon(scene, (255, 120, 40), [left[:2], tip[:2], right[:2]])
    core_left, core_right = camera.project(x - 0.05, y, 0.0), camera.project(x + 0.05, y, 0.0)
    core_tip = camera.project(x, y, height * 0.5)
    if core_left is not None and core_right is not None and core_tip is not None:
        pygame.draw.polygon(scene, (255, 230, 120), [core_left[:2], core_tip[:2], core_right[:2]])


def _draw_acid(scene, camera, zone, shown, t):
    """An acid pool: a green fill that flickers, with bubbles that rise out of it and pop."""
    fill = ACID_FILLS[1] if int(zone.life * 10) % 2 else ACID_FILLS[0]
    _ground_disc(scene, camera, zone.x, zone.y, zone.radius, fill, ACID_OUTLINE)
    for dx, dy, phase in shown:
        cycle = (t * 0.7 + phase) % 1.0  # 0 when a bubble starts to rise, 1 as it bursts
        hit = camera.project(zone.x + dx, zone.y + dy, 0.05 + 0.5 * cycle)
        if hit is None:
            continue
        pop = max(0.0, cycle - 0.8) * 5  # It shrinks away in the last part of its rise
        radius = max(1, int(0.13 * camera.focal / hit[2] * (1 - min(1.0, pop))))
        pygame.draw.circle(scene, BUBBLE, (int(hit[0]), int(hit[1])), radius)


COMBO_RING = (255, 196, 40)  # Same-type combo: a solid gold ring
SQUAD_RING = (120, 230, 210)  # Mixed squad: a wider teal ring, so the two read apart without colour


def _draw_combo_rings(scene, camera, units):
    for unit in units:
        if unit.mixed:
            _ground_circle(scene, camera, unit.x, unit.y, 0.58, SQUAD_RING)
        if unit.group > 1:
            _ground_circle(scene, camera, unit.x, unit.y, 0.42, COMBO_RING)
        if unit.charged:  # A full charge: a gold ring that pulses until the charged shot is fired
            pulse = 0.72 + 0.06 * math.sin(pygame.time.get_ticks() / 120)
            _ground_circle(scene, camera, unit.x, unit.y, pulse, CHARGE_COLOUR)


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
    hit = camera.project(puff.x, puff.y, puff.z)
    if hit is None:
        return
    radius = max(1, round(puff.size * puff.life / puff.max_life))
    pygame.draw.circle(scene, puff.colour, (int(hit[0]), int(hit[1])), radius)


def _draw_blast(scene, camera, b):
    """A burst where a shot landed. Explosions ring out over the floor with sparks flying off; a bullet's spark is a
    small flash; flak bursts in the air at its height."""
    p = b.progress
    if b.style == "explosion":
        if p < 0.5:  # A bright flash in the middle at first, then just the ring
            _ground_disc(scene, camera, b.x, b.y, b.radius * (1 - p), (255, 246, 214), b.colour)
        _ground_circle(scene, camera, b.x, b.y, b.radius * (0.2 + 0.8 * p), b.colour)
        _burst_sparks(scene, camera, b, reach=b.radius * 1.3 * p, lift=1.2 * 4 * p * (1 - p), size=2)
    elif b.style == "spark":
        hit = camera.project(b.x, b.y, b.z)
        if hit is not None:
            pygame.draw.circle(scene, (255, 250, 230), (int(hit[0]), int(hit[1])), max(1, round(3 * (1 - p)) + 1))
        _burst_sparks(scene, camera, b, reach=0.4 * p, lift=0.25 * 4 * p * (1 - p), size=1)
    else:  # flak
        hit = camera.project(b.x, b.y, b.z)
        if hit is not None:
            radius = max(1, int(b.radius * camera.focal / hit[2] * (0.4 + 0.9 * p)))
            pygame.draw.circle(scene, b.colour, (int(hit[0]), int(hit[1])), radius, 1)
        _burst_sparks(scene, camera, b, reach=0.9 * p, lift=0.4, size=1)


def _burst_sparks(scene, camera, b, reach, lift, size):
    """Sparks leaving the burst at its angles: `reach` tiles out and `lift` tiles up at the top of their arc."""
    for angle in b.spark_angles:
        hit = camera.project(b.x + math.cos(angle) * reach, b.y + math.sin(angle) * reach, b.z + lift)
        if hit is not None:
            pygame.draw.circle(scene, b.colour, (int(hit[0]), int(hit[1])), size)


def draw_scene(camera, game, hover, drag=None):
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
    for c in game.corpses:
        drawables.append((_depth(camera, c.x, c.y), lambda c=c: _draw_corpse(scene, camera, c)))
    drawables.sort(key=lambda d: -d[0])
    for _, draw in drawables:
        draw()

    if drag is not None:  # A unit being dragged: a ghost on the tile under the pointer, green if it can go there
        unit, cell = drag
        if cell is not None:
            col, row = cell
            _ground_tile(scene, camera, col, row, GOOD if game.move_error(col, row) is None else BAD)
            _billboard(scene, camera, unit_sprite(unit.faction, unit.kind, unit.level, unit.ultimate_index,
                                                  unit.recipe), col + 0.5, row + 0.5, unit.height)

    for projectile in game.projectiles:
        if isinstance(projectile, Projectile):
            _draw_projectile(scene, camera, projectile)
    for effect in game.effects:
        if isinstance(effect, Puff):
            _draw_puff(scene, camera, effect)
        elif isinstance(effect, Blast):
            _draw_blast(scene, camera, effect)
        elif isinstance(effect, Floater):
            _draw_floater(scene, camera, effect)
    return scene
