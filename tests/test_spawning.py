import unittest

from config import SPAWN_RUSH
from game import Game


class RushTests(unittest.TestCase):

    def test_space_during_a_round_toggles_the_rush(self):
        game = Game("human")
        game.start_wave()
        self.assertTrue(game.toggle_rush())
        self.assertTrue(game.rushing)
        game.toggle_rush()
        self.assertFalse(game.rushing)

    def test_rush_is_refused_between_rounds(self):
        game = Game("human")
        self.assertFalse(game.toggle_rush())
        self.assertFalse(game.rushing)

    def test_rush_spawns_the_queue_faster(self):
        normal = Game("human")
        normal.start_wave()
        fast = Game("human")
        fast.start_wave()
        fast.toggle_rush()
        for game in (normal, fast):
            game._queue = [(1.0, "walker")] * 3
            for _ in range(3):  # 0.3 seconds: the normal queue has not reached its first spawn time yet
                game.update(0.1)
        self.assertEqual(len(normal.enemies), 0)
        self.assertGreater(len(fast.enemies), 0)
        self.assertGreater(SPAWN_RUSH, 1)

    def test_rush_ends_with_the_round(self):
        game = Game("zombie")
        game.start_wave()
        game.toggle_rush()
        game._queue = []
        game.enemies = []
        game.update(0.01)
        self.assertFalse(game.wave_active)
        self.assertFalse(game.rushing)


if __name__ == "__main__":
    unittest.main()
