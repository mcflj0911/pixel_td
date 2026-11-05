import unittest

from config import PICKUP_GOLD, PICKUP_LIFE, RAGE_FIRE, RAGE_SECONDS, FREEZE_FACTOR, FREEZE_SECONDS, PICKUP_EVERY
from enemies import Enemy
from game import Game
from pickups import KINDS, Pickup
from world import make_map


class PickupTests(unittest.TestCase):

    def setUp(self):
        self.game = Game("human")
        self.game.gold = 1000
        self.game.start_wave()

    def drop(self, kind):
        """Put a pickup of this kind on the first route cell and return it."""
        col, row = sorted(self.game.map.cells)[0]
        pickup = Pickup(col, row, kind)
        self.game.pickups.append(pickup)
        return pickup

    def test_a_pickup_drops_on_the_route_during_a_round(self):
        self.game._pickup_timer = 0.0
        self.game.update(0.01)
        self.assertEqual(len(self.game.pickups), 1)
        pickup = self.game.pickups[0]
        self.assertIn((pickup.col, pickup.row), self.game.map.cells)
        self.assertIn(pickup.kind, KINDS)

    def test_no_pickups_drop_between_rounds(self):
        self.game.wave_active = False
        self.game._pickup_timer = 0.0
        self.game.countdown = 999
        self.game.update(0.01)
        self.assertEqual(self.game.pickups, [])

    def test_clicking_the_tile_collects_gold(self):
        pickup = self.drop("gold")
        gold = self.game.gold
        self.assertIsNone(self.game.click_cell(pickup.col, pickup.row))
        self.assertEqual(self.game.gold, gold + PICKUP_GOLD)
        self.assertEqual(self.game.pickups, [])

    def test_rage_speeds_up_every_unit_for_a_while(self):
        unit = self.game.place(5, 0, "rapid")
        pickup = self.drop("rage")
        self.game.click_cell(pickup.col, pickup.row)
        self.assertEqual(self.game.rage, RAGE_SECONDS)
        self.game.update(0.01)
        self.assertAlmostEqual(unit.buff, RAGE_FIRE)

    def test_rage_runs_out(self):
        self.game.rage = 0.05
        self.game.update(0.1)
        self.assertEqual(self.game.rage, 0.0)

    def test_freeze_slows_ground_enemies(self):
        walker = Enemy("zombie", "walker", make_map(0).route)
        self.game.enemies.append(walker)
        pickup = self.drop("freeze")
        self.game.click_cell(pickup.col, pickup.row)
        self.game.update(0.01)
        self.assertEqual(walker.slow_factor, FREEZE_FACTOR)
        self.assertGreater(walker.slow_time, 0)

    def test_freeze_leaves_flyers_alone(self):
        crow = Enemy("zombie", "crow", make_map(0).route)
        self.game.enemies.append(crow)
        self.game.freeze = FREEZE_SECONDS
        self.game.update(0.01)
        self.assertEqual(crow.slow_time, 0.0)

    def test_uncollected_pickups_fade(self):
        pickup = self.drop("gold")
        pickup.life = 0.05
        self.game.update(0.1)
        self.assertEqual(self.game.pickups, [])

    def test_pickups_are_cleared_when_the_round_ends(self):
        self.drop("gold")
        self.game._queue = []
        self.game.enemies = []
        self.game.update(0.01)
        self.assertFalse(self.game.wave_active)
        self.assertEqual(self.game.pickups, [])

    def test_a_pickup_lives_for_its_configured_time(self):
        self.assertEqual(Pickup(0, 0, "gold").life, PICKUP_LIFE)
        self.assertGreater(PICKUP_EVERY, 0)


if __name__ == "__main__":
    unittest.main()
