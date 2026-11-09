import unittest

from config import DAMAGE_TYPES, DAMAGE_NAMES, ENEMY_TYPES, FLY_HEIGHT, UNIT_TYPES, WEAK_HIT_COLOUR
from enemies import Enemy
from projectiles import BurnZone, Blast, Floater, Projectile, Puff
from units import Unit
from world import make_map


def route():
    return make_map(0).route


def shot(faction, kind, target):
    """A shot fired by a new unit of this role at `target`, with the unit's own stats."""
    unit = Unit(faction, kind, *route()[0])
    return Projectile(unit.x, unit.y, faction, kind, target, unit.stats, owner=unit)


def enemy_at(faction, kind, x, y):
    enemy = Enemy(faction, kind, route())
    enemy.x, enemy.y = x, y
    return enemy


class DamageTypeTableTests(unittest.TestCase):
    def test_every_unit_role_and_enemy_uses_known_damage_types(self):
        for faction, roles in UNIT_TYPES.items():
            for role, spec in roles.items():
                self.assertIn(spec["dtype"], DAMAGE_TYPES, (faction, role))
        for faction, enemies in ENEMY_TYPES.items():
            for kind, spec in enemies.items():
                for dtype in spec.get("vs", {}):
                    self.assertIn(dtype, DAMAGE_TYPES, (faction, kind))

    def test_every_damage_type_has_a_name(self):
        self.assertEqual(set(DAMAGE_NAMES), set(DAMAGE_TYPES))

    def test_roles_deal_the_types_the_design_gives_them(self):
        expected = {"rapid": "bullet", "sniper": "pierce", "splash": "explosion", "support": "bullet",
                    "flame": "burn", "artillery": "explosion", "flak": "flak", "rocket": "explosion"}
        for faction in UNIT_TYPES:
            for role, dtype in expected.items():
                self.assertEqual(UNIT_TYPES[faction][role]["dtype"], dtype, (faction, role))

    def test_a_unit_passes_its_damage_type_in_its_stats(self):
        self.assertEqual(Unit("human", "sniper", 1, 1).stats["dtype"], "pierce")

    def test_a_combined_unit_keeps_the_type_of_its_base_role(self):
        unit = Unit("human", "artillery", 1, 1, recipe="siege_gun")
        self.assertEqual(unit.stats["dtype"], "explosion")


class WeaknessTests(unittest.TestCase):
    def test_a_weakness_multiplies_the_hit(self):
        walker = Enemy("zombie", "walker", route())
        self.assertEqual(walker.take_damage(10, "burn"), 15)
        self.assertEqual(walker.hp, walker.max_hp - 15)

    def test_a_resistance_reduces_the_hit(self):
        runner = Enemy("zombie", "runner", route())
        self.assertAlmostEqual(runner.take_damage(10, "explosion"), 8)

    def test_armour_applies_after_the_type(self):
        brute = Enemy("zombie", "brute", route())  # Armour 25 percent, and weak to armour-piercing rounds
        self.assertAlmostEqual(brute.take_damage(100, "pierce"), 100 * 1.5 * 0.75)

    def test_a_hit_with_no_type_is_not_changed(self):
        walker = Enemy("zombie", "walker", route())
        self.assertEqual(walker.take_damage(10), 10)

    def test_an_enemy_without_a_table_takes_full_damage(self):
        militia = Enemy("human", "militia", route())
        self.assertEqual(militia.damage_factor("burn"), 1.0)

    def test_flyers_are_weak_to_flak(self):
        self.assertEqual(Enemy("zombie", "crow", route()).damage_factor("flak"), 1.6)


class ShotTypeTests(unittest.TestCase):
    def test_a_direct_hit_is_scaled_by_the_shot_type(self):
        runner = enemy_at("zombie", "runner", 5.0, 5.0)  # Weak to armour-piercing rounds
        sniper = shot("human", "sniper", runner)
        before = runner.hp
        sniper._impact([runner], [], [])
        self.assertAlmostEqual(before - runner.hp, UNIT_TYPES["human"]["sniper"]["damage"] * 1.3)

    def test_a_blast_is_explosion_damage_on_everything_it_reaches(self):
        target = enemy_at("zombie", "runner", 5.0, 5.0)  # Resists explosions
        neighbour = enemy_at("zombie", "runner", 5.4, 5.0)
        grenade = shot("human", "splash", target)
        grenade._impact([target, neighbour], [], [])
        expected = UNIT_TYPES["human"]["splash"]["splash_damage"] * 0.8
        self.assertAlmostEqual(target.max_hp - target.hp, UNIT_TYPES["human"]["splash"]["damage"] * 0.8)
        self.assertAlmostEqual(neighbour.max_hp - neighbour.hp, expected)

    def test_fire_on_the_ground_is_burn_damage(self):
        walker = enemy_at("zombie", "walker", 5.0, 5.0)  # Weak to burn
        zone = BurnZone(5.0, 5.0, 1.0, dps=10, life=1.0)
        zone.update(1.0, [walker])
        self.assertAlmostEqual(walker.max_hp - walker.hp, 15)

    def test_a_flame_fire_remembers_which_side_lit_it(self):
        target = enemy_at("zombie", "walker", 5.0, 5.0)
        zones = []
        shot("zombie", "flame", target)._impact([target], zones, [])
        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0].faction, "zombie")


class ImpactEffectTests(unittest.TestCase):
    def impact(self, faction, kind, target):
        effects = []
        shot(faction, kind, target)._impact([target], [], effects)
        return effects

    def test_a_grenade_rings_out_at_its_blast_radius(self):
        target = enemy_at("zombie", "walker", 5.0, 5.0)
        effects = self.impact("human", "splash", target)
        blasts = [e for e in effects if isinstance(e, Blast)]
        self.assertEqual([b.style for b in blasts], ["explosion"])
        self.assertEqual(blasts[0].radius, UNIT_TYPES["human"]["splash"]["splash"])

    def test_a_bullet_gives_a_small_spark(self):
        target = enemy_at("zombie", "walker", 5.0, 5.0)
        blasts = [e for e in self.impact("human", "rapid", target) if isinstance(e, Blast)]
        self.assertEqual([b.style for b in blasts], ["spark"])

    def test_flak_bursts_in_the_air_at_a_flyers_height(self):
        crow = enemy_at("zombie", "crow", 5.0, 5.0)
        blasts = [e for e in self.impact("human", "flak", crow) if isinstance(e, Blast)]
        self.assertEqual([b.style for b in blasts], ["flak"])
        self.assertEqual(blasts[0].z, FLY_HEIGHT)

    def test_fire_leaves_embers_not_a_blast(self):
        target = enemy_at("zombie", "walker", 5.0, 5.0)
        effects = self.impact("human", "flame", target)
        self.assertFalse([e for e in effects if isinstance(e, Blast)])
        self.assertTrue([e for e in effects if isinstance(e, Puff)])

    def test_a_weak_hit_shows_its_number_in_the_weakness_colour(self):
        runner = enemy_at("zombie", "runner", 5.0, 5.0)
        floaters = [e for e in self.impact("human", "sniper", runner) if isinstance(e, Floater)]
        self.assertEqual(floaters[0].colour, WEAK_HIT_COLOUR)

    def test_a_shell_leaves_smoke_as_it_flies(self):
        target = enemy_at("zombie", "walker", 9.0, 5.0)
        shell = shot("human", "artillery", target)
        effects = []
        shell.update(0.2, [target], [], effects)
        self.assertTrue([e for e in effects if isinstance(e, Puff)])

    def test_a_blast_fades_out_over_its_life(self):
        blast = Blast(0.0, 0.0, 1.0, (255, 255, 255), "explosion")
        self.assertEqual(blast.progress, 0.0)
        while blast.update(0.1):
            pass
        self.assertFalse(blast.life > 0)
        self.assertAlmostEqual(blast.progress, 1.0)


if __name__ == "__main__":
    unittest.main()
