import math

from config import (UNIT_TYPES, ULTIMATES, COMBO_KIT, UPGRADE_DAMAGE, UPGRADE_RATE, UPGRADE_RANGE, COMBO_TIERS, REINFORCE_BONUS,
                    MIXED_SQUAD_BONUS, MIXED_SQUAD_MAX, COMBINATIONS, CHARGE_ROLES, CHARGE_KILLS, CHARGE_DAMAGE,
                    CHARGE_PIERCE, CHARGE_BLAST, CHARGE_BURN, ATTACK_RECOIL, ATTACK_ANIM_SECONDS)
from projectiles import Projectile, can_hit


def group_multiplier(size):
    """Damage multiplier for a combo group of this many units (1 means no combo)."""
    mult = 1.0
    for needed, tier_mult in COMBO_TIERS:
        if size >= needed:
            mult = tier_mult
    return mult


def recipe_for(faction, *kinds):
    """(recipe_id, recipe) for combining units of these roles (two or three), or None if there is no recipe."""
    wanted = sorted(kinds)
    for recipe_id, recipe in COMBINATIONS[faction].items():
        if sorted(recipe["roles"]) == wanted:
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


def charged_stats(stats, kind):
    """The stats of a charged attack: much more damage and more pierce, a wider blast for the splash roles, and
    hotter, wider fire or acid for the flame and rocket roles."""
    charged = dict(stats, damage=stats["damage"] * CHARGE_DAMAGE, pierce=stats["pierce"] + CHARGE_PIERCE,
                   charged=True)
    if kind in ("splash", "artillery"):
        charged["splash"] = stats["splash"] * CHARGE_BLAST
    if kind in ("flame", "rocket") and stats.get("burn"):
        dps, life, radius = stats["burn"]
        charged["burn"] = (dps * CHARGE_BURN, life, radius * 1.3)
    return charged


def squad_multiplier(mixed):
    """Extra damage for standing near units of other types. `mixed` counts the other types nearby."""
    return 1 + MIXED_SQUAD_BONUS * min(mixed, MIXED_SQUAD_MAX)


class Unit:
    """A placed defender. Positions are in tile coordinates (floats).

    Levels: 1 to 4. Each upgrade multiplies damage and fire rate and adds range. At level 4 the unit
    takes an ultimate form, which changes its stats further (see ULTIMATES in config.py).

    The unit only needs enemies to have x, y, hp, alive, take_damage(amount, dtype), and apply_slow().
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
        self.kill_meter = 0  # Kills toward the next charged attack. Only the CHARGE_ROLES fill it
        self.charged = False  # The meter is full: the next shot is a charged attack
        self.attack_time = 0.0  # Seconds of attack animation left (the recoil and the flash)
        self.attack_charged = False  # The shot that started the animation was a charged attack
        self.move_from = None  # Where the unit was before it was last moved, for the hop to its new tile
        self.move_time = 0.0  # Seconds of hop left
        self.recoil = (0.0, 0.0)  # Where the sprite is pushed back to at the start of the animation, in tiles

    @property
    def cost(self):
        return self.base["cost"]

    @property
    def recipe_info(self):
        """The COMBINATIONS entry this unit was combined from, or None."""
        return COMBINATIONS[self.faction][self.recipe] if self.recipe else None

    @property
    def combo_kit(self):
        """The kit of a combined unit: its upgrade path, ultimates, sound and look. None for a plain unit."""
        return COMBO_KIT[self.faction][self.recipe] if self.recipe else None

    @property
    def ultimate_options(self):
        """The two ultimate forms this unit can take: its combination's own, or the role's."""
        if self.recipe:
            return self.combo_kit["ultimates"]
        return ULTIMATES[self.faction][self.kind]

    @property
    def can_charge(self):
        return self.kind in CHARGE_ROLES

    def register_kill(self):
        """Count a kill toward the charge. Once it is full, the unit stays charged until its next shot."""
        if not self.can_charge or self.charged:
            return
        self.kill_meter += 1
        if self.kill_meter >= CHARGE_KILLS:
            self.kill_meter = CHARGE_KILLS
            self.charged = True

    @property
    def display_name(self):
        """A combined unit keeps its combined name, and its ultimate form shows under it (see form_name)."""
        if self.recipe is not None:
            return self.recipe_info["name"]
        if self.ultimate is not None:
            return self.ultimate["name"]
        return self.base["name"]

    @property
    def form_name(self):
        """The ultimate form of a combined unit, shown under its name. None for a plain unit or below level 4."""
        return self.ultimate["name"] if self.recipe is not None and self.ultimate else None

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
            "dtype": base["dtype"],  # The damage type of the shot's hit. Blasts and fire are typed by projectiles.py
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
            "shot": self.recipe_info.get("shot") if self.recipe_info else None,  # The look of its shots
            "combo": self.recipe,  # Which combination fired it, for its own sound, trail and impact
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
            for upgrade in self.combo_kit["path"][:self.level - 1]:  # Level 2 and 3 each add the combo's own upgrade
                _apply_mods(s, upgrade["mods"])
        combo = group_multiplier(self.group) * squad_multiplier(self.mixed) * (1 + REINFORCE_BONUS) ** self.reinforce
        s["damage"] *= combo
        s["splash_damage"] *= combo
        if self.ultimate:
            _apply_mods(s, self.ultimate["mods"])
        return s

    @property
    def height(self):
        """How tall the unit stands on the map, in tiles. A combined unit may be bigger than its role."""
        scale = self.recipe_info["scale"] if self.recipe_info else 1.0
        return self.base["height"] * scale

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
        self.attack_time = max(0.0, self.attack_time - dt)
        self.move_time = max(0.0, self.move_time - dt)
        if self.cooldown > 0:
            return []
        target = self.pick_target(enemies)
        if target is None:
            return []
        stats = self.stats
        if self.dmg_buff != 1.0:  # Support aura: a copy with more damage, so the cached stats stay as they are
            stats = dict(stats, damage=stats["damage"] * self.dmg_buff,
                         splash_damage=stats["splash_damage"] * self.dmg_buff)
        self.attack_charged = self.charged
        if self.charged:  # The charge is spent on this shot
            stats = charged_stats(stats, self.kind)
            self.charged = False
            self.kill_meter = 0
        self.cooldown = 1.0 / (self.stats["rate"] * self.buff)
        self.flash = 0.08
        self._start_attack(target)
        return [Projectile(self.x, self.y, self.faction, self.kind, target, stats, owner=self)]

    def _start_attack(self, target):
        """Start the attack animation: the sprite is pushed back away from the target, then settles."""
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy) or 1.0
        push = ATTACK_RECOIL.get(self.kind, 0.0)
        if self.combo_kit and self.combo_kit["anim"] == "pump":  # A pump-action combination kicks back harder
            push *= 1.8
        self.recoil = (-dx / dist * push, -dy / dist * push)
        self.attack_time = ATTACK_ANIM_SECONDS
