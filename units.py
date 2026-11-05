import math

from config import (UNIT_TYPES, UPGRADE_DAMAGE, UPGRADE_RATE, UPGRADE_RANGE, COMBO_TIERS, REINFORCE_BONUS,
                    MIXED_SQUAD_BONUS, MIXED_SQUAD_MAX, COMBINATIONS)
from projectiles import Projectile, can_hit


def group_multiplier(size):
    """Damage multiplier for a combo group of this many units (1 means no combo)."""
    mult = 1.0
    for needed, tier_mult in COMBO_TIERS:
        if size >= needed:
            mult = tier_mult
    return mult


def recipe_for(faction, kind_a, kind_b):
    """(recipe_id, recipe) for combining these two roles, or None if they have no recipe together."""
    pair = frozenset((kind_a, kind_b))
    for recipe_id, recipe in COMBINATIONS[faction].items():
        if frozenset(recipe["roles"]) == pair:
            return recipe_id, recipe
    return None


def _apply_mods(stats, mods):
    """Apply ULTIMATES-style mods to a stats dict. range adds; damage, rate, splash and splash_damage multiply;
    the rest (pierce, slow, burn, aura) are set outright."""
    for key, value in mods.items():
        if key == "range":
            stats["range"] += value
        elif key in ("damage", "rate", "splash", "splash_damage"):
            stats[key] *= value
        else:
            stats[key] = value


def squad_multiplier(mixed):
    """Extra damage for standing near units of other types. `mixed` counts the other types nearby."""
    return 1 + MIXED_SQUAD_BONUS * min(mixed, MIXED_SQUAD_MAX)


class Unit:
    """A placed defender. Positions are in tile coordinates (floats).

    Levels: 1 to 4. Each upgrade multiplies damage and fire rate and adds range. At level 4 the unit
    takes an ultimate form, which changes its stats further (see ULTIMATES in config.py).

    The unit only needs enemies to have x, y, hp, alive, take_damage(), and apply_slow().
    """

    def __init__(self, faction, kind, x, y, recipe=None):
        self.faction = faction
        self.kind = kind
        self.base = UNIT_TYPES[faction][kind]
        # The COMBINATIONS recipe this unit was combined from, or None. An unknown id (from a damaged save) is dropped
        self.recipe = recipe if recipe in COMBINATIONS[faction] else None
        self.x = x
        self.y = y
        self.level = 1
        self.ultimate = None  # The chosen ultimate form, once the unit reaches level 4
        self.ultimate_index = None  # 0 or 1: which of the two ultimates was picked
        self.spent = self.base["cost"]  # Gold put into this unit, refunded if the route moves over it
        self.buff = 1.0  # Fire rate multiplier from a support unit's aura or rage, set by the game every frame
        self.dmg_buff = 1.0  # Damage multiplier from a support unit's aura, set by the game every frame
        self.cooldown = 0.0  # Seconds until the unit can fire again
        self.flash = 0.0  # Seconds of muzzle flash left
        self.damage = 0.0  # Total damage this unit has dealt, shown on the post-loss stats screen
        self.group = 1  # How many same-type units stand close to this one, including itself (set by the game)
        self.mixed = 0  # How many other unit types stand close to this one (set by the game)
        self.kills = 0  # Enemies this unit landed the killing blow on
        self.reinforce = 0  # Reinforcements bought after the ultimate (see Game.reinforce)
        self._stats_cache = None  # (key, stats) pair, see the stats property

    @property
    def cost(self):
        return self.base["cost"]

    @property
    def recipe_info(self):
        """The COMBINATIONS entry this unit was combined from, or None."""
        return COMBINATIONS[self.faction][self.recipe] if self.recipe else None

    @property
    def display_name(self):
        if self.ultimate is not None:
            return self.ultimate["name"]
        if self.recipe is not None:
            return self.recipe_info["name"]
        return self.base["name"]

    @property
    def stats(self):
        """The unit's current stats, after upgrades and the ultimate.

        Cached: the dict is rebuilt only when a field that changes the stats is different. It is replaced rather
        than edited, so a projectile that kept an older copy is not changed underneath.
        """
        key = (self.level, self.ultimate, self.recipe, self.group, self.mixed, self.reinforce)
        if self._stats_cache is None or self._stats_cache[0] != key:
            self._stats_cache = (key, self._compute_stats())
        return self._stats_cache[1]

    def _compute_stats(self):
        base = self.base
        steps = self.level - 1
        dmg = UPGRADE_DAMAGE ** steps
        s = {
            "damage": base["damage"] * dmg,
            "splash_damage": base["splash_damage"] * dmg,
            "rate": base["rate"] * UPGRADE_RATE ** steps,
            "range": base["range"] + UPGRADE_RANGE * steps,
            "splash": base["splash"],
            "pierce": base.get("pierce", 0),
            "slow": base.get("slow"),
            "burn": None,
            "aura": base.get("aura"),
            "aura_damage": base.get("aura_damage", 1.0),
        }
        if base.get("burn"):
            dps, life, radius = base["burn"]
            s["burn"] = (dps * dmg, life, radius)
        if self.recipe_info:
            mods = dict(self.recipe_info["mods"])
            if "blast" in mods:  # A blast of its own: set outright, with the same upgrade scaling as the damage
                radius, blast_damage = mods.pop("blast")
                s["splash"] = radius
                s["splash_damage"] = blast_damage * dmg
            _apply_mods(s, mods)
        combo = group_multiplier(self.group) * squad_multiplier(self.mixed) * (1 + REINFORCE_BONUS) ** self.reinforce
        s["damage"] *= combo
        s["splash_damage"] *= combo
        if self.ultimate:
            _apply_mods(s, self.ultimate["mods"])
        return s

    def can_hit(self, enemy):
        return can_hit(self.faction, self.kind, enemy)

    def in_range(self, enemy):
        return math.hypot(enemy.x - self.x, enemy.y - self.y) <= self.stats["range"]

    def pick_target(self, enemies):
        """Nearest living enemy inside range that this unit can hit, or None."""
        reach = self.stats["range"]
        best, best_dist = None, math.inf
        for enemy in enemies:
            if not enemy.alive or not self.can_hit(enemy):
                continue
            dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
            if dist <= reach and dist < best_dist:
                best, best_dist = enemy, dist
        return best

    def update(self, dt, enemies):
        """Advance timers and fire if ready. Returns the list of new projectiles (usually zero or one)."""
        self.cooldown = max(0.0, self.cooldown - dt)
        self.flash = max(0.0, self.flash - dt)
        if self.cooldown > 0:
            return []
        target = self.pick_target(enemies)
        if target is None:
            return []
        stats = self.stats
        if self.dmg_buff != 1.0:  # Support aura: a copy with more damage, so the cached stats stay as they are
            stats = dict(stats, damage=stats["damage"] * self.dmg_buff,
                         splash_damage=stats["splash_damage"] * self.dmg_buff)
        self.cooldown = 1.0 / (self.stats["rate"] * self.buff)
        self.flash = 0.08
        return [Projectile(self.x, self.y, self.faction, self.kind, target, stats, owner=self)]
