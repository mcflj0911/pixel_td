import math

from config import ENEMY_TYPES


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

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        """Hurt the enemy. Armour takes a share off the hit. Returns the damage actually dealt."""
        dealt = amount * (1 - self.spec.get("armour", 0.0))
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
