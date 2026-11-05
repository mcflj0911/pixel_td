import unittest

from config import UNIT_TYPES, ULTIMATES, UPGRADE_DAMAGE, UPGRADE_RATE, UPGRADE_RANGE, ROLES, FACTIONS
from enemies import Enemy
from units import Unit
from world import make_map

ROUTE = make_map(0).route


def make_enemy(x, y, kind="walker", hp=None):
    enemy = Enemy("zombie", kind, ROUTE)
    enemy.x, enemy.y = x, y
    if hp is not None:
        enemy.hp = enemy.max_hp = hp
    return enemy


def fly(projectile, enemies, zones=None, effects=None, limit=5000):
    """Run one projectile until it resolves. Returns the zones and effects it created."""
    zones = [] if zones is None else zones
    effects = [] if effects is None else effects
    for _ in range(limit):
        if projectile.done:
            return zones, effects
        projectile.update(0.02, enemies, zones, effects)
    raise AssertionError("projectile never resolved")


def ultimate_unit(faction, kind, index, x=0.5, y=0.5):
    unit = Unit(faction, kind, x, y)
    unit.level = 4
    unit.ultimate_index = index
    unit.ultimate = ULTIMATES[faction][kind][index]
    return unit


class RosterTests(unittest.TestCase):

    def test_every_faction_has_six_roles_with_two_ultimates_each(self):
        for faction in FACTIONS:
            self.assertEqual(set(UNIT_TYPES[faction]), set(ROLES))
            for role in ROLES:
                self.assertEqual(len(ULTIMATES[faction][role]), 2, f"{faction} {role}")

    def test_cost_order_matches_design(self):
        for faction in FACTIONS:
            u = UNIT_TYPES[faction]
            self.assertLess(u["rapid"]["cost"], u["support"]["cost"])
            self.assertLess(u["support"]["cost"], u["sniper"]["cost"])
            self.assertLess(u["sniper"]["cost"], u["flame"]["cost"])
            self.assertLess(u["flame"]["cost"], u["artillery"]["cost"])

    def test_support_aura_and_flame_burn_are_configured(self):
        for faction in FACTIONS:
            self.assertIsNotNone(UNIT_TYPES[faction]["support"]["aura"])
            self.assertIsNotNone(UNIT_TYPES[faction]["flame"]["burn"])


class TargetingAndFiringTests(unittest.TestCase):

    def test_fires_at_nearest_enemy_in_range(self):
        unit = Unit("human", "rapid", 0.5, 0.5)
        near = make_enemy(2.5, 0.5)
        far = make_enemy(4.5, 0.5)
        shots = unit.update(0.0, [far, near])
        self.assertEqual(len(shots), 1)
        self.assertIs(shots[0].target, near)

    def test_ignores_enemies_out_of_range(self):
        unit = Unit("human", "splash", 0.5, 0.5)
        self.assertEqual(unit.update(1.0, [make_enemy(unit.stats["range"] + 1, 0.5)]), [])

    def test_ignores_dead_enemies(self):
        unit = Unit("human", "rapid", 0.5, 0.5)
        self.assertEqual(unit.update(0.0, [make_enemy(2, 0.5, hp=0)]), [])

    def test_cooldown_limits_fire_rate(self):
        unit = Unit("human", "rapid", 0.5, 0.5)  # 1 shot per second
        target = make_enemy(2.5, 0.5, hp=1000)
        self.assertEqual(len(unit.update(0.0, [target])), 1)
        self.assertEqual(len(unit.update(0.5, [target])), 0)
        self.assertEqual(len(unit.update(0.5, [target])), 1)

    def test_flame_fires_much_faster_than_mortar(self):
        flame = Unit("human", "flame", 0.5, 0.5)
        mortar = Unit("human", "artillery", 0.5, 0.5)
        target = make_enemy(1.5, 0.5, hp=10000)
        flame_shots = sum(len(flame.update(0.1, [target])) for _ in range(20))
        mortar_shots = sum(len(mortar.update(0.1, [target])) for _ in range(20))
        self.assertGreater(flame_shots, mortar_shots * 5)

    def test_aura_buff_speeds_up_firing(self):
        unit = Unit("human", "rapid", 0.5, 0.5)
        unit.buff = 2.0
        target = make_enemy(2.5, 0.5, hp=1000)
        unit.update(0.0, [target])
        self.assertEqual(len(unit.update(0.5, [target])), 1)  # Twice as fast, so ready after half a second


class ProjectileTests(unittest.TestCase):

    def test_damage_lands_when_the_shot_arrives(self):
        unit = Unit("human", "rapid", 0.5, 0.5)
        target = make_enemy(3.5, 0.5, hp=100)
        (shot,) = unit.update(0.0, [target])
        self.assertEqual(target.hp, 100)  # Still in the air
        fly(shot, [target])
        self.assertEqual(target.hp, 100 - UNIT_TYPES["human"]["rapid"]["damage"])

    def test_shot_resolves_at_last_seen_spot_if_target_dies(self):
        unit = Unit("human", "splash", 0.5, 0.5)
        target = make_enemy(2.0, 0.5, hp=100)
        neighbour = make_enemy(2.0, 1.0, hp=100)  # Inside the splash radius of the target
        (shot,) = unit.update(0.0, [target, neighbour])
        target.hp = 0  # Dies while the shell is in the air
        fly(shot, [target, neighbour])
        self.assertEqual(neighbour.hp, 100 - UNIT_TYPES["human"]["splash"]["splash_damage"])

    def test_splash_hits_neighbours_but_not_far_enemies(self):
        unit = Unit("human", "splash", 0.5, 0.5)
        main = make_enemy(2.0, 0.5, hp=100)
        close = make_enemy(2.0, 1.2, hp=100)  # 0.7 tiles from main: inside the 1.5 tile splash
        far = make_enemy(2.0, 3.0, hp=100)  # 2.5 tiles from main: outside
        enemies = [main, close, far]
        (shot,) = unit.update(0.0, enemies)
        fly(shot, enemies)
        spec = UNIT_TYPES["human"]["splash"]
        self.assertEqual(main.hp, 100 - spec["damage"])
        self.assertEqual(close.hp, 100 - spec["splash_damage"])
        self.assertEqual(far.hp, 100)

    def test_artillery_shell_arcs_and_splashes(self):
        unit = Unit("human", "artillery", 0.5, 0.5)
        target = make_enemy(6.0, 0.5, hp=500)
        neighbour = make_enemy(6.0, 1.5, hp=500)  # 1.0 tile away: inside the 2.2 tile blast
        enemies = [target, neighbour]
        (shot,) = unit.update(0.0, enemies)
        heights = []
        for _ in range(400):
            shot.update(0.02, enemies, [], [])
            heights.append(shot.z)
            if shot.done:
                break
        self.assertGreater(max(heights), 0.5)
        self.assertLess(neighbour.hp, 500)

    def test_pierce_carries_through_enemies_in_a_line(self):
        unit = ultimate_unit("human", "rapid", 1)  # Piercing Volley: 3 extra enemies
        first = make_enemy(2.0, 0.5, hp=500)
        second = make_enemy(2.8, 0.5, hp=500)
        third = make_enemy(3.5, 0.5, hp=500)
        enemies = [first, second, third]
        (shot,) = unit.update(0.0, enemies)
        fly(shot, enemies)
        for enemy in enemies:
            self.assertLess(enemy.hp, 500)

    def test_burn_leaves_a_zone_behind(self):
        unit = ultimate_unit("zombie", "splash", 1)  # Toxic Pool
        target = make_enemy(2.0, 0.5, hp=500)
        (shot,) = unit.update(0.0, [target])
        zones, _ = fly(shot, [target])
        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0].dps, ULTIMATES["zombie"]["splash"][1]["mods"]["burn"][0])

    def test_flame_sets_the_ground_on_fire(self):
        unit = Unit("human", "flame", 0.5, 0.5)
        target = make_enemy(1.8, 0.5, hp=500)
        (shot,) = unit.update(0.0, [target])
        zones, _ = fly(shot, [target])
        self.assertEqual(len(zones), 1)
        self.assertGreater(zones[0].dps, 0)

    def test_hunters_mark_slows_what_it_hits(self):
        unit = ultimate_unit("human", "sniper", 1)  # Hunter's Mark
        target = make_enemy(4.5, 0.5, hp=500)
        (shot,) = unit.update(0.0, [target])
        fly(shot, [target])
        self.assertEqual(target.slow_factor, 0.5)
        self.assertGreater(target.slow_time, 0)


class UpgradeTests(unittest.TestCase):

    def test_each_level_raises_damage_rate_and_range(self):
        base = Unit("human", "sniper", 0, 0)
        upgraded = Unit("human", "sniper", 0, 0)
        upgraded.level = 2
        self.assertAlmostEqual(upgraded.stats["damage"], base.stats["damage"] * UPGRADE_DAMAGE)
        self.assertAlmostEqual(upgraded.stats["rate"], base.stats["rate"] * UPGRADE_RATE)
        self.assertAlmostEqual(upgraded.stats["range"], base.stats["range"] + UPGRADE_RANGE)

    def test_level_four_stacks_three_upgrades(self):
        unit = ultimate_unit("human", "rapid", 0)  # Gatling Squad: rate x2, damage x0.8
        base = UNIT_TYPES["human"]["rapid"]
        self.assertAlmostEqual(unit.stats["rate"], base["rate"] * UPGRADE_RATE ** 3 * 2.0)
        self.assertAlmostEqual(unit.stats["damage"], base["damage"] * UPGRADE_DAMAGE ** 3 * 0.8)

    def test_ultimate_sets_pierce(self):
        unit = ultimate_unit("zombie", "sniper", 0)  # Spore Cannon: pierce 5
        self.assertEqual(unit.stats["pierce"], 5)

    def test_ultimate_sets_aura(self):
        unit = ultimate_unit("human", "support", 0)  # Battle Drums: reach 4 tiles
        self.assertEqual(unit.stats["aura"], (4.0, 1.25))


class EnemyMovementTests(unittest.TestCase):

    def test_slow_halves_speed(self):
        normal = Enemy("zombie", "walker", ROUTE)
        slowed = Enemy("zombie", "walker", ROUTE)
        slowed.apply_slow(0.5, 5.0)
        normal.advance(1.0)
        slowed.advance(1.0)
        self.assertAlmostEqual((slowed.x - ROUTE[0][0]) * 2, normal.x - ROUTE[0][0], places=6)


if __name__ == "__main__":
    unittest.main()
