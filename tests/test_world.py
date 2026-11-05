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
        # Serpentine maps leave no ground away from the route, so test the placement on ground that has room
        with mock.patch.object(world, "DOODAD_DENSITY", 0.3):
            doodads = world._place_doodads(2, {(0, 0), (1, 0)})
        self.assertTrue(doodads)
        kinds = {kind for _, _, kind in doodads}
        self.assertGreater(len(kinds), 3)
        for x, y, _ in doodads:
            cell = (int(x), int(y))
            self.assertNotIn(cell, {(0, 0), (1, 0)})
            self.assertNotIn(cell, {(c, r) for c in (0, 1, 2) for r in (0, 1)})


if __name__ == "__main__":
    unittest.main()
