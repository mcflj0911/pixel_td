import math
import random

from config import (UNIT_TYPES, IMPACT_COLOURS, SHOT_COLOURS, AIR_ROLES, FLY_HEIGHT, WEAK_HIT_COLOUR,
                    RESIST_HIT_COLOUR, CHARGE_COLOUR, COMBO_KIT)

TRAIL_LENGTH = {"rapid": 5, "sniper": 12, "splash": 5, "support": 4, "flame": 4, "artillery": 5, "flak": 5, "rocket": 10}
ARC_KINDS = ("splash", "artillery")  # Shells that rise into the air and come down on the target
ARC_HEIGHT = 1.5  # How high a shell rises, in tiles
CHAIN_RANGE = 4.0  # Pierce looks for its next target this close to where it last hit
# Smoke and embers left behind a shot: (seconds between puffs, colour or None for the shot's own colour, size, life)
TRAIL_PUFFS = {
    "splash": (0.07, (150, 150, 150), 1.5, 0.35),
    "artillery": (0.06, (110, 110, 110), 2.0, 0.45),
    "rocket": (0.05, (215, 215, 210), 1.4, 0.35),
    "flame": (0.03, None, 1.2, 0.2),
}


def can_hit(faction, kind, enemy):
    """Can a unit of this faction and role shoot this enemy? Flyers need an air-capable role, and air-only
    roles (flak) cannot shoot the ground."""
    flying = getattr(enemy, "flying", False)
    if flying and kind not in AIR_ROLES:
        return False
    if not flying and UNIT_TYPES[faction][kind].get("air_only"):
        return False
    return True


def _combo_impact(style, ix, iy, colour):
    """The flourish where a combined unit's shot lands, in its kit's style (see config/combos.py)."""
    if style == "ring":
        return [Blast(ix, iy, 0.7, colour, "explosion")]
    if style == "starburst":  # Four sparks fly out in a cross
        return [Blast(ix + math.cos(a) * 0.4, iy + math.sin(a) * 0.4, 0.25, colour, "spark")
                for a in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    if style == "shards":  # Three shards spray outward, uneven
        return [Blast(ix + math.cos(a) * 0.6, iy + math.sin(a) * 0.6, 0.2, colour, "spark")
                for a in (0.8, 2.4, 4.3)]
    if style == "bubbles":  # Bubbles pop up from the hit
        return [Puff(ix + dx, iy + dy, colour, size=2.5, life=0.45)
                for dx, dy in ((0.3, 0.1), (-0.25, 0.3), (0.1, -0.3), (-0.2, -0.15))]
    if style == "flash":  # A white flash with a bloom of colour
        return [Blast(ix, iy, 0.6, (255, 255, 255), "spark"), Puff(ix, iy, colour, size=4.0, life=0.3)]
    if style == "nova":  # A short ring and a wider spark ring, one after the other
        return [Blast(ix, iy, 0.45, colour, "explosion"), Blast(ix, iy, 0.9, colour, "spark")]
    return []


def _hurt(enemy, amount, owner, dtype=None):
    """Damage an enemy of a damage type and credit the damage to the unit that caused it. Only the hp it actually
    lost counts, after the type's weakness or resistance and armour. Returns the damage dealt."""
    before = max(0.0, enemy.hp)
    dealt = enemy.take_damage(amount, dtype)
    if owner is not None:
        owner.damage += min(dealt, before)
        if before > 0 and enemy.hp <= 0:
            owner.kills += 1  # Credited with the killing blow
            owner.register_kill()  # Also fills the owner's charge, if it charges
    return dealt


class Puff:
    """A short-lived dot at a point: smoke, embers, sparks and kills. It shrinks as it fades. `z` is its height."""

    def __init__(self, x, y, colour, size=2.5, life=0.3, z=0.2):
        self.x, self.y, self.z = x, y, z
        self.colour = colour
        self.size = size
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.life -= dt
        return self.life > 0


class Blast:
    """The burst where a shot lands. Its look follows the damage type:
      "explosion": a ring spreads over the ground to `radius` tiles, with sparks flying off it
      "spark":     a small flash, for a bullet or an armour-piercing round
      "flak":      an airburst at height `z`, for flak that bursts on a flyer
    It fades out over its life."""

    LIFE = {"explosion": 0.5, "spark": 0.25, "flak": 0.4}
    SPARKS = {"explosion": 8, "spark": 4, "flak": 6}

    def __init__(self, x, y, radius, colour, style, z=0.0):
        self.x, self.y, self.z = x, y, z
        self.radius = radius
        self.colour = colour
        self.style = style
        self.life = self.LIFE[style]
        self.max_life = self.life
        count = self.SPARKS[style]
        # Each spark leaves at its own angle; alternate ones are turned a little so the burst is not a neat star
        self.spark_angles = [2 * math.pi * i / count + (0.4 if i % 2 else 0.0) for i in range(count)]

    @property
    def progress(self):
        """0 when the burst starts, 1 when it is gone."""
        return min(1.0, max(0.0, 1 - self.life / self.max_life))

    def update(self, dt):
        self.life -= dt
        return self.life > 0


class Floater:
    """A damage number that rises above the hit and fades out."""

    def __init__(self, x, y, text, colour, life=0.7):
        self.x, self.y = x, y
        self.text = text
        self.colour = colour
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.life -= dt
        return self.life > 0


def _spots(x, y, radius):
    """Fixed places inside a burn zone where its flames or bubbles rise. Seeded by the position, so a zone looks the
    same from one frame to the next and every time it is drawn."""
    rng = random.Random(f"{x:.2f},{y:.2f}")
    count = max(4, int(radius * 4))
    return [(rng.uniform(-0.7, 0.7) * radius, rng.uniform(-0.7, 0.7) * radius, rng.random()) for _ in range(count)]


class BurnZone:
    """Fire (humans) or acid (zombies) left on the ground. Hurts every ground enemy inside it, every frame, until it
    runs out. The damage is burn damage, whatever shot left it."""

    def __init__(self, x, y, radius, dps, life, owner=None, faction="human"):
        self.x, self.y = x, y
        self.radius = radius
        self.dps = dps
        self.life = life
        self.max_life = life
        self.owner = owner
        self.faction = faction  # Which side's shot made it: decides whether it looks like fire or acid
        self.spots = _spots(x, y, radius)

    def update(self, dt, enemies):
        for enemy in enemies:
            if enemy.alive and not getattr(enemy, "flying", False) \
                    and math.hypot(enemy.x - self.x, enemy.y - self.y) <= self.radius:
                _hurt(enemy, self.dps * dt, self.owner, "burn")
        self.life -= dt
        return self.life > 0


class Projectile:
    """A shot in flight. It homes in on its target and resolves its damage when it arrives.

    If the target dies first, the shot keeps flying to where the target was last seen and still hits there,
    so splash and burn damage are not wasted.
    """

    def __init__(self, x, y, faction, kind, target, stats, owner=None):
        self.faction = faction
        self.kind = kind
        self.stats = stats  # Snapshot of the unit's stats when it fired
        self.shot = stats.get("shot")  # The look of a combined unit's shots, or None
        self.combo = stats.get("combo")  # The combination that fired it, or None
        self.kit = COMBO_KIT[faction][self.combo] if self.combo else None  # Its own colour, trail and impact
        self.colour = self.kit["colour"] if self.kit else SHOT_COLOURS[faction][kind]
        self.charged = bool(stats.get("charged"))  # A charged attack: drawn bigger and gold
        self.owner = owner  # The unit that fired, credited with the damage
        self.x, self.y, self.z = x, y, 0.0
        self.target = target
        self.gx, self.gy = target.x, target.y  # Where it is heading
        self.speed = UNIT_TYPES[faction][kind]["shot_speed"]
        self.pierce_left = stats["pierce"]
        self.hit = set()  # Enemies this shot has already damaged
        self.trail = []
        self.done = False
        self.aim_z = 0.0
        self._puff_timer = 0.0  # Seconds until the next smoke or ember puff
        self._start_leg()

    def _start_leg(self):
        self.leg_length = max(0.01, math.hypot(self.gx - self.x, self.gy - self.y))
        # Shots at a flyer travel up to its height, so they do not pass under it
        self.aim_z = FLY_HEIGHT if getattr(self.target, "flying", False) else 0.0

    def update(self, dt, enemies, zones, effects):
        if self.done:
            return
        if self.target.alive:
            self.gx, self.gy = self.target.x, self.target.y
        self.trail.append((self.x, self.y, self.z))
        del self.trail[:-TRAIL_LENGTH[self.kind]]

        dx, dy = self.gx - self.x, self.gy - self.y
        dist = math.hypot(dx, dy)
        step = self.speed * dt
        if dist <= step:
            self._impact(enemies, zones, effects)
            return
        self.x += dx / dist * step
        self.y += dy / dist * step
        progress = 1 - (dist - step) / self.leg_length
        if self.kind in ARC_KINDS:
            self.z = 4 * ARC_HEIGHT * progress * (1 - progress)
        else:
            self.z = self.aim_z * progress
        self._emit_trail(dt, effects)

    def _emit_trail(self, dt, effects):
        """Smoke behind a shell or missile, and embers behind a flame."""
        spec = TRAIL_PUFFS.get(self.kind)
        if spec is None:
            return
        self._puff_timer -= dt
        if self._puff_timer > 0:
            return
        every, colour, size, life = spec
        self._puff_timer = every
        effects.append(Puff(self.x, self.y, colour or self.colour, size=size, life=life, z=self.z))

    def _impact_effects(self, ix, iy, s):
        """The burst where the shot lands. It follows the damage type: a blast rings out, flak bursts in the air,
        fire leaves embers, and a bullet or armour-piercing round gives a quick spark. A charged shot adds a gold
        flash, and a combined unit's shot style adds its own flourish."""
        colour = IMPACT_COLOURS[self.faction]
        effects = self._base_impact(ix, iy, s, colour)
        if self.kit:
            effects.extend(_combo_impact(self.kit["impact"], ix, iy, self.kit["colour"]))
        if self.charged:
            effects.append(Blast(ix, iy, 1.3, CHARGE_COLOUR, "explosion"))
        if self.shot == "cluster":  # Splits into a ring of small bursts
            for i in range(4):
                angle = math.pi / 2 * i + math.pi / 4
                effects.append(Blast(ix + math.cos(angle) * 0.5, iy + math.sin(angle) * 0.5, 0.3, colour, "spark"))
        elif self.shot == "barrage":  # Each shell of a barrage lands with an extra thud
            effects.append(Blast(ix, iy, 0.6, colour, "explosion"))
        return effects

    def _base_impact(self, ix, iy, s, colour):
        if s["splash"] > 0:
            return [Blast(ix, iy, s["splash"], colour, "explosion")]
        if s["dtype"] == "flak":
            return [Blast(ix, iy, 0.9, SHOT_COLOURS[self.faction]["flak"], "flak", z=self.aim_z)]
        if s["dtype"] == "burn":
            return [Puff(ix, iy, colour, size=3.0, life=0.35)]
        return [Blast(ix, iy, 0.35, colour, "spark")]

    def _impact(self, enemies, zones, effects):
        s = self.stats
        ix, iy = self.gx, self.gy
        self.x, self.y, self.z = ix, iy, 0.0
        target = self.target

        if target.alive and target not in self.hit:
            factor = target.damage_factor(s["dtype"])
            dealt = _hurt(target, s["damage"], self.owner, s["dtype"])
            self.hit.add(target)
            if dealt >= 1:
                # A weakness shows orange and a resistance grey, so the player can see the type at work
                colour = WEAK_HIT_COLOUR if factor > 1 else RESIST_HIT_COLOUR if factor < 1 else (255, 255, 255)
                effects.append(Floater(ix, iy, f"{dealt:.0f}", colour))
            if s["slow"]:
                target.apply_slow(*s["slow"])

        if s["splash"] > 0:
            for enemy in enemies:
                if enemy in self.hit or not enemy.alive or getattr(enemy, "flying", False):
                    continue  # Blasts and fire do not reach the air
                if math.hypot(enemy.x - ix, enemy.y - iy) <= s["splash"]:
                    _hurt(enemy, s["splash_damage"], self.owner, "explosion")
                    self.hit.add(enemy)

        if s["burn"]:
            dps, life, radius = s["burn"]
            zones.append(BurnZone(ix, iy, radius, dps, life, owner=self.owner, faction=self.faction))

        effects.extend(self._impact_effects(ix, iy, s))

        nxt = self._next_target(enemies, ix, iy) if self.pierce_left > 0 else None
        if nxt is not None:
            self.pierce_left -= 1
            self.target = nxt
            self.gx, self.gy = nxt.x, nxt.y
            self._start_leg()  # The shot carries on from where it hit
        else:
            self.done = True

    def _next_target(self, enemies, ix, iy):
        best, best_dist = None, CHAIN_RANGE
        for enemy in enemies:
            if not enemy.alive or enemy in self.hit:
                continue
            if not can_hit(self.faction, self.kind, enemy):
                continue
            dist = math.hypot(enemy.x - ix, enemy.y - iy)
            if dist <= best_dist:
                best, best_dist = enemy, dist
        return best
