import math

from config import ENEMY_TYPES, DEATH_SECONDS


class Enemy:
    """An enemy walking a route. Positions are in tile coordinates."""

    def __init__(self, faction, kind, route, hp_mult=1.0, speed_mult=1.0):
        self.faction = faction
        self.kind = kind
        self.spec = ENEMY_TYPES[faction][kind]
        self.flying = bool(self.spec.get("flying"))  # Flyers ignore the ground: only air-capable units hit them
        self.max_hp = self.spec["hp"] * hp_mult
        self.hp = self.max_hp
        self.speed = self.spec["speed"] * speed_mult
        self.route = route
        self.x, self.y = route[0]
        self.next_point = 1
        self.leaked = False  # True once it reached the end of the route (no reward for that)
        self.slow_factor = 1.0
        self.slow_time = 0.0  # Seconds of slow left
        self.flash = 0.0  # Seconds of hit flash left
        self.walk = 0.0  # Distance walked, in tiles: drives the walk cycle

    @property
    def alive(self):
        return self.hp > 0

    def damage_factor(self, dtype):
        """How much this enemy takes from a damage type: above 1 is a weakness, below 1 a resistance."""
        return self.spec.get("vs", {}).get(dtype, 1.0)

    def take_damage(self, amount, dtype=None):
        """Hurt the enemy. The damage type's weakness or resistance scales the hit, then armour takes a share off.
        Returns the damage actually dealt."""
        dealt = amount * self.damage_factor(dtype) * (1 - self.spec.get("armour", 0.0))
        self.hp -= dealt
        self.flash = 0.1
        return dealt

    def apply_slow(self, factor, seconds):
        self.slow_factor = factor
        self.slow_time = max(self.slow_time, seconds)

    def advance(self, dt):
        """Walk along the route for dt seconds. Returns True when the enemy reaches the end."""
        self.flash = max(0.0, self.flash - dt)
        mult = self.slow_factor if self.slow_time > 0 else 1.0
        self.slow_time = max(0.0, self.slow_time - dt)
        step = self.speed * mult * dt
        self.walk += step
        while step > 0 and self.next_point < len(self.route):
            tx, ty = self.route[self.next_point]
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            if dist <= step:
                self.x, self.y = tx, ty
                step -= dist
                self.next_point += 1
            else:
                self.x += dx / dist * step
                self.y += dy / dist * step
                step = 0
        return self.next_point >= len(self.route)


class Corpse:
    """A killed enemy, falling over for a moment before it is gone. It only needs to be drawn, not simulated."""

    def __init__(self, enemy):
        self.faction, self.kind = enemy.faction, enemy.kind
        self.x, self.y = enemy.x, enemy.y
        self.height = enemy.spec["height"]
        self.flying = enemy.flying
        self.life = self.max_life = DEATH_SECONDS

    @property
    def progress(self):
        """0 when it falls, 1 when it is gone."""
        return min(1.0, max(0.0, 1 - self.life / self.max_life))

    def update(self, dt):
        self.life -= dt
        return self.life > 0
