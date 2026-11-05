import unittest
from unittest import mock

import world
from config import DOODAD_HEIGHT, DOODAD_WEIGHTS
from sprites import doodad_sprite


class DoodadTests(unittest.TestCase):

    def test_every_doodad_kind_has_a_height_and_a_sprite(self):
        for kind, _ in DOODAD_WEIGHTS:
            self.assertIn(kind, DOODAD_HEIGHT)
            self.assertIsNotNone(doodad_sprite(kind))

    def test_doodads_block_building_and_are_kept_off_the_route(self):
        with mock.patch.object(world, "DOODAD_DENSITY", 0.3):
            game_map = world.make_map(2)
        self.assertTrue(game_map.doodads)
        kinds = {kind for _, _, kind in game_map.doodads}
        self.assertGreater(len(kinds), 3)
        for x, y, _ in game_map.doodads:
            cell = (int(x), int(y))
            self.assertNotIn(cell, game_map.cells)
            self.assertFalse(game_map.is_buildable(*cell))


if __name__ == "__main__":
    unittest.main()
