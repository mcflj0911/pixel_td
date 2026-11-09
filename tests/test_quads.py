import unittest

from config import COMBINATIONS, MAP_COLS, MAP_ROWS
from game import Game

UNIT_HEIGHT_FLOOR = 1.2  # A plain unit stands about 1.2 tiles tall. A quad must be taller than that


def free_buildable(game, col, row):
    return game.map.is_buildable(col, row) and game.unit_at(col, row) is None


def place_plus(game, centre_role, side_roles):
    """Place a unit in the middle of a plus shape, with units on three of its four sides. Returns (centre, sides)."""
    for col in range(MAP_COLS):
        for row in range(MAP_ROWS):
            for skip in Game.NEIGHBOURS:
                sides = [(col + dc, row + dr) for dc, dr in Game.NEIGHBOURS if (dc, dr) != skip]
                if free_buildable(game, col, row) and all(free_buildable(game, *cell) for cell in sides):
                    centre = game.place(col, row, centre_role)
                    units = [game.place(*cell, role) for cell, role in zip(sides, side_roles)]
                    assert centre is not None and all(units)
                    return centre, units
    raise AssertionError("the map has no room for a plus shape")


class QuadRecipeTests(unittest.TestCase):
    def test_each_faction_has_one_ultimate_combination_of_four_units(self):
        for faction in ("human", "zombie"):
            quads = [r for r in COMBINATIONS[faction].values() if len(r["roles"]) == 4]
            self.assertEqual(len(quads), 1, faction)

    def test_more_pairs_and_trios_now_use_the_rockets(self):
        for faction in ("human", "zombie"):
            rocket_recipes = [r for r in COMBINATIONS[faction].values() if "rocket" in r["roles"]]
            self.assertGreaterEqual(len(rocket_recipes), 5, faction)  # Three pairs and two trios, per side


class QuadCombineTests(unittest.TestCase):
    def setUp(self):
        self.game = Game("human")
        self.game.gold = 10_000

    def test_a_unit_with_three_fitting_neighbours_makes_the_quad(self):
        centre, sides = place_plus(self.game, "splash", ("rapid", "sniper", "support"))
        partners, recipe_id, recipe = self.game.combine_option(centre)
        self.assertEqual(recipe_id, "bastion")
        self.assertEqual(len(partners), 3)
        self.assertCountEqual([p.kind for p in partners], ["rapid", "sniper", "support"])

    def test_combining_the_quad_frees_three_slots(self):
        centre, _ = place_plus(self.game, "splash", ("rapid", "sniper", "support"))
        before = len(self.game.units)
        self.game.selected_unit = centre
        self.assertTrue(self.game.combine())
        self.assertEqual(len(self.game.units), before - 3)
        self.assertEqual(self.game.selected_unit.recipe, "bastion")
        self.assertEqual(self.game.selected_unit.kind, "splash")
        self.assertEqual(self.game.selected_unit.display_name, "Bastion")

    def test_the_quad_is_taller_and_its_stats_include_the_blast(self):
        centre, _ = place_plus(self.game, "splash", ("rapid", "sniper", "support"))
        self.game.selected_unit = centre
        self.game.combine()
        fused = self.game.selected_unit
        self.assertGreater(fused.height, UNIT_HEIGHT_FLOOR)
        self.assertGreater(fused.stats["aura"][0], 2.5)

    def test_a_quad_cannot_combine_again(self):
        centre, _ = place_plus(self.game, "splash", ("rapid", "sniper", "support"))
        self.game.selected_unit = centre
        self.game.combine()
        self.assertIsNone(self.game.combine_option(self.game.selected_unit))

    def test_four_units_in_a_two_by_two_block_make_the_quad(self):
        cells = [(c, r) for c in range(MAP_COLS - 1) for r in range(MAP_ROWS - 1)
                 if all(free_buildable(self.game, cc, rr) for cc, rr in
                        [(c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)])]
        c, r = cells[0]
        centre = self.game.place(c, r, "splash")
        self.game.place(c + 1, r, "rapid")
        self.game.place(c, r + 1, "sniper")
        self.game.place(c + 1, r + 1, "support")
        partners, recipe_id, _ = self.game.combine_option(centre)
        self.assertEqual(recipe_id, "bastion")
        self.assertEqual(len(partners), 3)

    def test_three_neighbours_that_do_not_fit_a_quad_fall_back_to_a_pair(self):
        centre, _ = place_plus(self.game, "splash", ("rapid", "sniper", "flak"))
        partners, recipe_id, _ = self.game.combine_option(centre)
        self.assertEqual(recipe_id, "breacher")
        self.assertEqual([p.kind for p in partners], ["rapid"])

    def test_the_zombie_quad_works_the_same_way(self):
        game = Game("zombie")
        game.gold = 10_000
        centre, _ = place_plus(game, "splash", ("rapid", "sniper", "support"))
        partners, recipe_id, _ = game.combine_option(centre)
        self.assertEqual(recipe_id, "hive_colossus")
        self.assertEqual(len(partners), 3)



if __name__ == "__main__":
    unittest.main()
