import unittest

from config import COMBINATIONS, COMBINE_COST, DIFFICULTIES, MAX_UNITS, MAP_COLS, MAP_ROWS, UNIT_TYPES
from game import Game
from save import run_from_data, run_to_data
from ui import COMBINE_RECT, ui_action
from units import Unit, recipe_for

COMBINE_CLICK = (COMBINE_RECT.centerx, COMBINE_RECT.centery)


def buildable(game):
    return [(c, r) for c in range(MAP_COLS) for r in range(MAP_ROWS) if game.map.is_buildable(c, r)]


def free_cells(game):
    return [cell for cell in buildable(game) if game.unit_at(*cell) is None]


def free_neighbour(game, unit):
    """An empty buildable cell that shares an edge with `unit`, or None."""
    for dc, dr in Game.NEIGHBOURS:
        cell = (int(unit.x) + dc, int(unit.y) + dr)
        if cell in free_cells(game):
            return cell
    return None


def place_pair(game, first_role, second_role):
    """Place two units on edge-sharing cells. Returns (first, second)."""
    for col, row in buildable(game):
        neighbour = (col + 1, row)
        if game.unit_at(col, row) is None and neighbour in free_cells(game):
            a = game.place(col, row, first_role)
            b = game.place(*neighbour, second_role)
            assert a is not None and b is not None
            return a, b
    raise AssertionError("the map has no two adjacent free cells")


class RecipeLookupTests(unittest.TestCase):
    def test_a_pair_finds_its_recipe_in_either_order(self):
        recipe_id, recipe = recipe_for("human", "rapid", "splash")
        self.assertEqual(recipe["name"], "Breacher")
        self.assertEqual(recipe_for("human", "splash", "rapid")[0], recipe_id)

    def test_pairs_without_a_recipe_return_none(self):
        self.assertIsNone(recipe_for("human", "rapid", "sniper"))
        self.assertIsNone(recipe_for("human", "rapid", "rapid"))

    def test_every_recipe_is_consistent(self):
        for faction, recipes in COMBINATIONS.items():
            for recipe_id, recipe in recipes.items():
                self.assertEqual(len(recipe["roles"]), 2, recipe_id)
                self.assertIn(recipe["base"], recipe["roles"], recipe_id)
                self.assertIn(recipe["base"], UNIT_TYPES[faction], recipe_id)
                self.assertEqual(recipe_for(faction, *recipe["roles"])[0], recipe_id)


class CombineRuleTests(unittest.TestCase):
    def setUp(self):
        self.game = Game("human")
        self.game.gold = 10_000

    def test_units_must_share_an_edge(self):
        cells = set(buildable(self.game))
        col, row = next((c, r) for c, r in sorted(cells) if (c + 1, r + 1) in cells)
        a = self.game.place(col, row, "rapid")
        self.game.place(col + 1, row + 1, "splash")  # Diagonal only
        self.assertIsNone(self.game.combine_option(a))

    def test_adjacent_matching_units_offer_the_recipe(self):
        a, b = place_pair(self.game, "rapid", "splash")
        partner, recipe_id, _ = self.game.combine_option(a)
        self.assertIs(partner, b)
        self.assertEqual(recipe_id, "breacher")

    def test_ultimates_cannot_combine(self):
        a, _ = place_pair(self.game, "rapid", "splash")
        a.level = 4
        a.ultimate_index = 0
        a.ultimate = {"name": "x", "desc": "", "mods": {}}
        self.assertIsNone(self.game.combine_option(a))

    def test_a_combined_unit_cannot_combine_again(self):
        a, _ = place_pair(self.game, "rapid", "splash")
        self.game.selected_unit = a
        self.assertTrue(self.game.combine())
        fused = self.game.selected_unit
        cell = free_neighbour(self.game, fused)
        self.assertIsNotNone(cell, "the fused unit needs a free neighbour for this test")
        self.game.place(*cell, "splash")
        self.assertIsNone(self.game.combine_option(fused))

    def test_combining_without_a_partner_explains_why(self):
        unit = self.game.place(*buildable(self.game)[0], "rapid")
        self.game.selected_unit = unit
        self.assertFalse(self.game.combine())
        self.assertIn("next to it", self.game.message)

    def test_a_level_three_unit_combines_and_keeps_the_higher_level(self):
        a, _ = place_pair(self.game, "rapid", "splash")
        a.level = 3
        self.game.selected_unit = a
        self.assertTrue(self.game.combine())
        self.assertEqual(self.game.selected_unit.level, 3)


class CombineCostTests(unittest.TestCase):
    def setUp(self):
        self.rapid = Unit("human", "rapid", 0.5, 0.5)
        self.splash = Unit("human", "splash", 1.5, 0.5)

    def test_price_is_half_the_base_prices_at_normal(self):
        game = Game("human", difficulty="Normal")
        self.assertEqual(game.combine_cost(self.rapid, self.splash), round((50 + 160) * COMBINE_COST))
        self.assertEqual(game.combine_cost(self.rapid, self.splash), 105)

    def test_price_scales_with_the_difficulty(self):
        costs = {name: Game("human", difficulty=name).combine_cost(self.rapid, self.splash) for name in DIFFICULTIES}
        self.assertLess(costs["Easy"], costs["Normal"])
        self.assertGreater(costs["Hard"], costs["Normal"])
        self.assertEqual(costs["Hard"], round(105 * DIFFICULTIES["Hard"]["combine"]))

    def test_combining_needs_the_gold(self):
        game = Game("human", difficulty="Hard")
        game.gold = 10_000
        a, b = place_pair(game, "rapid", "splash")
        game.selected_unit = a
        game.gold = game.combine_cost(a, b) - 1
        before = (len(game.units), game.gold)
        self.assertFalse(game.combine())
        self.assertEqual((len(game.units), game.gold), before)


class CombineEffectTests(unittest.TestCase):
    def setUp(self):
        self.game = Game("human")
        self.game.gold = 10_000

    def test_two_units_become_one_and_the_price_is_paid(self):
        a, b = place_pair(self.game, "rapid", "splash")
        gold = self.game.gold
        cost = self.game.combine_cost(a, b)
        self.game.selected_unit = a
        self.assertTrue(self.game.combine())
        self.assertEqual(len(self.game.units), 1)
        fused = self.game.units[0]
        self.assertEqual(fused.recipe, "breacher")
        self.assertEqual(fused.kind, "rapid")
        self.assertEqual(fused.spent, a.spent + b.spent + cost)
        self.assertEqual(self.game.gold, gold - cost)
        self.assertIs(self.game.selected_unit, fused)

    def test_the_recipe_changes_the_stats(self):
        a, _ = place_pair(self.game, "rapid", "splash")
        self.game.selected_unit = a
        self.game.combine()
        fused = self.game.selected_unit
        self.assertGreater(fused.stats["splash"], 0)  # Rifle shots burst now
        self.assertAlmostEqual(fused.stats["rate"], UNIT_TYPES["human"]["rapid"]["rate"] * 0.9)

    def test_combining_frees_a_slot_at_the_cap(self):
        game = self.game
        first, _ = place_pair(game, "rapid", "splash")
        for col, row in buildable(game):
            if len(game.units) >= MAX_UNITS:
                break
            if game.unit_at(col, row) is None:
                game.place(col, row, "rapid")
        self.assertEqual(len(game.units), MAX_UNITS)
        self.assertIsNone(game.place(*free_cells(game)[0], "rapid"), "the cap should be reached")

        game.selected_unit = first
        self.assertTrue(game.combine())
        self.assertEqual(len(game.units), MAX_UNITS - 1)
        self.assertIsNotNone(game.place(*free_cells(game)[0], "rapid"), "the freed slot should be usable")

    def test_panel_button_asks_for_a_combine(self):
        a, _ = place_pair(self.game, "rapid", "splash")
        self.game.selected_unit = a
        self.assertEqual(ui_action(COMBINE_CLICK, self.game), ("combine",))

    def test_level_four_units_get_no_combine_button(self):
        a, _ = place_pair(self.game, "rapid", "splash")
        a.level = 4
        a.ultimate_index = 0
        a.ultimate = {"name": "x", "desc": "", "mods": {}}
        self.game.selected_unit = a
        self.assertNotEqual(ui_action(COMBINE_CLICK, self.game), ("combine",))

    def test_undo_splits_the_units_back_and_refunds_the_price(self):
        a, b = place_pair(self.game, "rapid", "splash")
        gold = self.game.gold
        self.game.selected_unit = a
        self.game.combine()
        self.assertTrue(self.game.undo())
        self.assertEqual(self.game.units, [a, b])
        self.assertEqual(self.game.gold, gold)
        self.assertEqual(len(self.game.all_units), 2)  # The fused unit is taken back out of the stats history too

    def test_selling_the_combined_unit_refunds_its_whole_spend(self):
        a, _ = place_pair(self.game, "rapid", "splash")
        self.game.selected_unit = a
        self.game.combine()
        fused = self.game.selected_unit
        self.assertEqual(self.game.sell_refund(fused), round(fused.spent * 0.6))


class CombineSaveTests(unittest.TestCase):
    def test_a_combined_unit_survives_a_save_and_load(self):
        game = Game("human")
        game.gold = 10_000
        a, _ = place_pair(game, "sniper", "support")
        game.selected_unit = a
        game.combine()
        unit = run_from_data(run_to_data(game)).units[0]
        self.assertEqual(unit.recipe, "overwatch")
        self.assertEqual(unit.stats["pierce"], 2)
        self.assertEqual(unit.stats["aura"], COMBINATIONS["human"]["overwatch"]["mods"]["aura"])

    def test_an_unknown_recipe_is_dropped(self):
        unit = Unit("human", "rapid", 0.5, 0.5, recipe="no_such_recipe")
        self.assertIsNone(unit.recipe)
        self.assertIsNone(unit.recipe_info)

    def test_older_saves_without_a_recipe_still_load(self):
        game = Game("human")
        game.place(*buildable(game)[0], "rapid")
        data = run_to_data(game)
        for item in data["units"]:
            item.pop("recipe", None)
        self.assertIsNone(run_from_data(data).units[0].recipe)


if __name__ == "__main__":
    unittest.main()
