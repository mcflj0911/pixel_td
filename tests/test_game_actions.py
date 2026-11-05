from config import UNDO_STEPS
import os
import tempfile
import unittest

from config import ULTIMATES, REINFORCE_MAX, REINFORCE_BONUS, UNIT_TYPES
from game import Game
from save import save_path
from projectiles import _hurt
from enemies import Enemy
from world import make_map


class UndoTests(unittest.TestCase):

    def test_undo_placement_refunds_and_removes_the_unit(self):
        game = Game("human")
        game.gold = 1000
        game.place(5, 0, "rapid")
        self.assertEqual(game.gold, 1000 - UNIT_TYPES["human"]["rapid"]["cost"])
        self.assertTrue(game.undo())
        self.assertEqual(game.units, [])
        self.assertEqual(game.gold, 1000)

    def test_undo_sale_puts_the_unit_back_in_its_place(self):
        game = Game("human")
        game.gold = 1000
        first = game.place(5, 0, "rapid")
        second = game.place(6, 0, "sniper")
        game.click_cell(6, 0)
        game.sell()
        game.sell()  # Confirmed
        self.assertNotIn(second, game.units)
        self.assertTrue(game.undo())
        self.assertEqual(game.units.index(second), 1)
        self.assertIs(game.units[0], first)

    def test_undo_is_refused_during_a_round(self):
        game = Game("human")
        game.gold = 1000
        game.place(5, 0, "rapid")
        game.start_wave()
        self.assertFalse(game.undo())
        self.assertEqual(len(game.units), 1)

    def test_undo_steps_back_through_the_last_five_actions(self):
        game = Game("human")
        game.gold = 1000
        for col in range(5, 11):  # Six placements: only the last five can be undone
            game.place(col, 0, "rapid")
        for _ in range(UNDO_STEPS):
            self.assertTrue(game.undo())
        self.assertFalse(game.undo())  # Nothing left in the history
        self.assertEqual(len(game.units), 1)  # The first placement is no longer undoable

    def test_undo_is_refused_once_a_round_has_started(self):
        game = Game("human")
        game.gold = 1000
        game.place(5, 0, "rapid")
        game.start_wave()
        self.assertFalse(game.undo())


class ReinforceTests(unittest.TestCase):

    def ultimate_unit(self, game):
        game.gold = 10 ** 6
        unit = game.place(5, 0, "rapid")
        game.click_cell(5, 0)
        unit.level = 4
        unit.ultimate_index = 0
        unit.ultimate = ULTIMATES["human"]["rapid"][0]
        return unit

    def test_reinforce_needs_an_ultimate(self):
        game = Game("human")
        game.gold = 10 ** 6
        game.place(5, 0, "rapid")
        game.click_cell(5, 0)
        self.assertFalse(game.reinforce())

    def test_reinforce_adds_damage_and_costs_gold(self):
        game = Game("human")
        unit = self.ultimate_unit(game)
        before_damage = unit.stats["damage"]
        gold = game.gold
        cost = game.reinforce_cost(unit)
        self.assertTrue(game.reinforce())
        self.assertEqual(game.gold, gold - cost)
        self.assertAlmostEqual(unit.stats["damage"], before_damage * (1 + REINFORCE_BONUS))

    def test_reinforce_stops_at_the_maximum(self):
        game = Game("human")
        unit = self.ultimate_unit(game)
        for _ in range(REINFORCE_MAX):
            self.assertTrue(game.reinforce())
        self.assertFalse(game.reinforce())
        self.assertEqual(unit.reinforce, REINFORCE_MAX)

    def test_reinforce_costs_more_in_later_rounds(self):
        game = Game("human")
        unit = self.ultimate_unit(game)
        early = game.reinforce_cost(unit)
        game.wave = 20
        self.assertGreater(game.reinforce_cost(unit), early)


class CreditTests(unittest.TestCase):

    def test_the_unit_that_lands_the_killing_blow_gets_the_kill(self):
        route = make_map(0).route
        target = Enemy("zombie", "walker", route)
        unit = Game("human").place(5, 0, "rapid")
        _hurt(target, target.hp + 1, unit)
        self.assertEqual(unit.kills, 1)
        self.assertGreater(unit.damage, 0)

    def test_damage_on_an_already_dead_enemy_is_not_a_kill(self):
        route = make_map(0).route
        target = Enemy("zombie", "walker", route)
        unit = Game("human").place(5, 0, "rapid")
        _hurt(target, target.hp + 1, unit)
        _hurt(target, 5, unit)
        self.assertEqual(unit.kills, 1)

    def test_report_rows_carry_the_kill_count(self):
        game = Game("human")
        unit = game.place(5, 0, "rapid")
        unit.damage = 50
        unit.kills = 2
        self.assertEqual(game.report()["damage"][0][2], 2)


class SlotAndSoundTests(unittest.TestCase):

    def test_each_slot_has_its_own_file(self):
        self.assertNotEqual(save_path(1), save_path(2))
        self.assertTrue(save_path(3).endswith(".json"))

    def test_empty_slot_has_no_round(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(Game.save_round(os.path.join(folder, "nothing.json")))

    def test_saved_round_is_readable_from_the_slot(self):
        game = Game("human")
        game.wave = 6
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "slot.json")
            game.save(path)
            self.assertEqual(Game.save_round(path), 6)

    def test_selling_plays_the_cash_sound(self):
        game = Game("human")
        game.gold = 1000
        game.place(5, 0, "rapid")
        game.click_cell(5, 0)
        game.sell()
        game.sell()
        self.assertIn(("cash",), game.sound_events)

    def test_a_new_combo_tier_plays_the_chime(self):
        game = Game("human")
        game.gold = 10 ** 6
        game.place(5, 0, "rapid")
        game.place(6, 0, "rapid")
        game.update(0.01)
        self.assertIn(("combo",), game.sound_events)


if __name__ == "__main__":
    unittest.main()
