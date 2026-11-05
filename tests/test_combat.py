import unittest

from config import (ENEMY_TYPES, ROLES, AIR_ROLES, COMBO_TIERS, MIXED_SQUAD_BONUS, RESPEC_COST, ULTIMATES,
                    UNIT_TYPES)
from enemies import Enemy
from game import Game
from projectiles import can_hit
from units import Unit, group_multiplier, squad_multiplier
from world import make_map


def route():
    return make_map(0).route


class FlakTests(unittest.TestCase):

    def test_flak_is_the_seventh_role_and_can_shoot_flyers(self):
        self.assertEqual(ROLES[-1], "flak")
        self.assertIn("flak", AIR_ROLES)

    def test_flak_ignores_ground_enemies(self):
        walker = Enemy("zombie", "walker", route())
        self.assertFalse(can_hit("human", "flak", walker))
        self.assertIsNone(Unit("human", "flak", *route()[0]).pick_target([walker]))

    def test_flak_hits_flyers(self):
        crow = Enemy("zombie", "crow", route())
        self.assertTrue(can_hit("human", "flak", crow))
        self.assertIs(Unit("human", "flak", *route()[0]).pick_target([crow]), crow)

    def test_other_roles_still_ignore_flak_targets_on_the_ground(self):
        walker = Enemy("zombie", "walker", route())
        self.assertTrue(can_hit("human", "rapid", walker))
        self.assertTrue(can_hit("human", "splash", walker))

    def test_both_factions_have_flak_units_and_ultimates(self):
        for faction in ("human", "zombie"):
            self.assertTrue(UNIT_TYPES[faction]["flak"]["air_only"])
            self.assertEqual(len(ULTIMATES[faction]["flak"]), 2)


class ArmourTests(unittest.TestCase):

    def test_armour_reduces_each_hit(self):
        brute = Enemy("zombie", "brute", route())
        before = brute.hp
        dealt = brute.take_damage(100)
        self.assertAlmostEqual(dealt, 100 * (1 - ENEMY_TYPES["zombie"]["brute"]["armour"]))
        self.assertAlmostEqual(before - brute.hp, dealt)

    def test_unarmoured_enemies_take_full_damage(self):
        walker = Enemy("zombie", "walker", route())
        self.assertEqual(walker.take_damage(10), 10)

    def test_units_are_only_credited_with_damage_that_landed(self):
        from projectiles import _hurt
        brute = Enemy("zombie", "brute", route())
        unit = Unit("human", "rapid", *route()[0])
        _hurt(brute, 100, unit)
        self.assertAlmostEqual(unit.damage, 100 * (1 - ENEMY_TYPES["zombie"]["brute"]["armour"]))


class SquadAndComboTests(unittest.TestCase):

    def test_squad_multiplier_grows_with_different_types_up_to_the_cap(self):
        self.assertEqual(squad_multiplier(0), 1)
        self.assertAlmostEqual(squad_multiplier(1), 1 + MIXED_SQUAD_BONUS)
        self.assertEqual(squad_multiplier(9), squad_multiplier(3))

    def test_a_mixed_neighbour_adds_the_squad_bonus(self):
        game = Game("human")
        game.gold = 10 ** 6
        rapid = game.place(5, 0, "rapid")
        game.place(6, 0, "splash")
        game.update(0.01)
        self.assertEqual(rapid.mixed, 1)
        self.assertEqual(rapid.group, 1)
        self.assertAlmostEqual(rapid.stats["damage"], rapid.base["damage"] * squad_multiplier(1))

    def test_a_lone_unit_gets_no_squad_bonus(self):
        game = Game("human")
        game.gold = 10 ** 6
        rapid = game.place(5, 0, "rapid")
        game.update(0.01)
        self.assertEqual(rapid.mixed, 0)
        self.assertEqual(rapid.stats["damage"], rapid.base["damage"])

    def test_combo_tiers_go_up_to_six(self):
        self.assertEqual(COMBO_TIERS[-1][0], 6)
        self.assertEqual(group_multiplier(5), 1.7)
        self.assertEqual(group_multiplier(6), 1.9)

    def test_support_aura_adds_damage_as_well_as_fire_rate(self):
        game = Game("human")
        game.gold = 10 ** 6
        game.place(5, 0, "support")
        rapid = game.place(6, 0, "rapid")
        game.update(0.01)
        self.assertAlmostEqual(rapid.dmg_buff, UNIT_TYPES["human"]["support"]["aura_damage"])
        self.assertGreater(rapid.buff, 1.0)


class RespecTests(unittest.TestCase):

    def setUp(self):
        self.game = Game("human")
        self.game.gold = 10 ** 6
        self.unit = self.game.place(5, 0, "rapid")
        self.game.click_cell(5, 0)
        for _ in range(3):
            self.game.upgrade()
        self.game.choose_ultimate(0)

    def test_switching_costs_part_of_the_unit_price(self):
        gold = self.game.gold
        spent = self.unit.spent
        self.assertTrue(self.game.choose_ultimate(1))
        self.assertEqual(self.game.gold, gold - round(self.unit.cost * RESPEC_COST))
        self.assertEqual(self.unit.spent, spent + round(self.unit.cost * RESPEC_COST))
        self.assertEqual(self.unit.ultimate, ULTIMATES["human"]["rapid"][1])

    def test_choosing_the_current_ultimate_again_does_nothing(self):
        gold = self.game.gold
        self.assertFalse(self.game.choose_ultimate(0))
        self.assertEqual(self.game.gold, gold)
        self.assertEqual(self.game.message, "Already using that ultimate")

    def test_switching_is_refused_during_a_round(self):
        self.game.start_wave()
        self.assertFalse(self.game.choose_ultimate(1))
        self.assertEqual(self.unit.ultimate, ULTIMATES["human"]["rapid"][0])

    def test_switching_needs_the_gold(self):
        self.game.gold = 0
        self.assertFalse(self.game.choose_ultimate(1))
        self.assertEqual(self.unit.ultimate_index, 0)


if __name__ == "__main__":
    unittest.main()
