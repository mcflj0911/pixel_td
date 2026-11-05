import math

from config import UNIT_TYPES, IMPACT_COLOURS, AIR_ROLES, FLY_HEIGHT

TRAIL_LENGTH = {"rapid": 5, "sniper": 12, "splash": 5, "support": 4, "flame": 4, "artillery": 5, "flak": 5}
ARC_KINDS = ("splash", "artillery")  # Shells that rise into the air and come down on the target
ARC_HEIGHT = 1.5  # How high a shell rises, in tiles
CHAIN_RANGE = 4.0  # Pierce looks for its next target this close to where it last hit


def can_hit(faction, kind, enemy):
    """Can a unit of this faction and role shoot this enemy? Flyers need an air-capable role, and air-only
    roles (flak) cannot shoot the ground."""
    flying = getattr(enemy, "flying", False)
    if flying and kind not in AIR_ROLES:
        return False
    if not flying and UNIT_TYPES[faction][kind].get("air_only"):
        return False
    return True


def _hurt(enemy, amount, owner):
    """Damage an enemy and credit the damage to the unit that caused it. Only the hp it actually lost counts,
    after armour. Returns the damage dealt."""
    before = max(0.0, enemy.hp)
    dealt = enemy.take_damage(amount)
    if owner is not None:
        owner.damage += min(dealt, before)
        if before > 0 and enemy.hp <= 0:
            owner.kills += 1  # Credited with the killing blow
    return dealt


class Puff:
    """A short-lived burst at a point on the ground: impacts and kills."""

    def __init__(self, x, y, colour, size=2.5, life=0.3):
        self.x, self.y = x, y
        self.colour = colour
        self.size = size
        self.life = life
        self.max_life = life

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


class BurnZone:
    """Fire or poison left on the ground. Hurts every ground enemy inside it, every frame, until it runs out."""

    def __init__(self, x, y, radius, dps, life, owner=None):
        self.x, self.y = x, y
        self.radius = radius
        self.dps = dps
        self.life = life
        self.owner = owner

    def update(self, dt, enemies):
        for enemy in enemies:
            if enemy.alive and not getattr(enemy, "flying", False) \
                    and math.hypot(enemy.x - self.x, enemy.y - self.y) <= self.radius:
                _hurt(enemy, self.dps * dt, self.owner)
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

    def _impact(self, enemies, zones, effects):
        s = self.stats
        ix, iy = self.gx, self.gy
        self.x, self.y, self.z = ix, iy, 0.0
        target = self.target

        if target.alive and target not in self.hit:
            dealt = _hurt(target, s["damage"], self.owner)
            self.hit.add(target)
            if dealt >= 1:
                effects.append(Floater(ix, iy, f"{dealt:.0f}", (255, 255, 255)))
            if s["slow"]:
                target.apply_slow(*s["slow"])

        if s["splash"] > 0:
            for enemy in enemies:
                if enemy in self.hit or not enemy.alive or getattr(enemy, "flying", False):
                    continue  # Blasts and fire do not reach the air
                if math.hypot(enemy.x - ix, enemy.y - iy) <= s["splash"]:
                    _hurt(enemy, s["splash_damage"], self.owner)
                    self.hit.add(enemy)

        if s["burn"]:
            dps, life, radius = s["burn"]
            zones.append(BurnZone(ix, iy, radius, dps, life, owner=self.owner))

        effects.append(Puff(ix, iy, IMPACT_COLOURS[self.faction], size=3.5 if s["splash"] else 2.5))

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
