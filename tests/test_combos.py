import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # Draw without a real window

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from config import COMBINATIONS, COMBO_KIT, FACTIONS, MAP_COLS, MAP_ROWS  # noqa: E402
from game import Game  # noqa: E402
from projectiles import Projectile, _combo_impact  # noqa: E402
from save import run_from_data, run_to_data  # noqa: E402
from sounds import fire_sample  # noqa: E402
from units import Unit  # noqa: E402
from enemies import Enemy  # noqa: E402
from world import make_map  # noqa: E402

TRAILS = {"sparks", "smoke", "ribbon", "beads", "embers", "bolt"}
IMPACTS = {"ring", "starburst", "shards", "bubbles", "flash", "nova"}
ANIMS = {"spin", "pulse", "bob", "vent", "pump"}


def combined(faction, recipe_id, level=1):
    recipe = COMBINATIONS[faction][recipe_id]
    unit = Unit(faction, recipe["base"], 5.5, 5.5, recipe=recipe_id)
    unit.level = level
    return unit


def fused_in_game(faction, recipe_id, level=1):
    """A combined unit placed on a game, selected, ready to be levelled or given an ultimate."""
    game = Game(faction)
    game.gold = 100_000
    unit = combined(faction, recipe_id, level)
    game.units.append(unit)
    game.all_units.append(unit)
    game.selected_unit = unit
    return game, unit


class KitDataTests(unittest.TestCase):
    def test_every_combination_has_a_complete_kit(self):
        for faction in FACTIONS:
            self.assertEqual(set(COMBO_KIT[faction]), set(COMBINATIONS[faction]), faction)
            for recipe_id, kit in COMBO_KIT[faction].items():
                self.assertEqual(len(kit["path"]), 2, recipe_id)
                self.assertEqual(len(kit["ultimates"]), 2, recipe_id)
                for step in kit["path"] + kit["ultimates"]:
                    self.assertTrue(step["name"] and step["desc"], recipe_id)
                    self.assertIsInstance(step["mods"], dict, recipe_id)
                self.assertIn(kit["trail"], TRAILS, recipe_id)
                self.assertIn(kit["impact"], IMPACTS, recipe_id)
                self.assertIn(kit["anim"], ANIMS, recipe_id)
                self.assertEqual(len(kit["colour"]), 3, recipe_id)

    def test_every_combination_has_its_own_sound(self):
        for faction in FACTIONS:
            sounds = [tuple(sorted(kit["sound"].items())) for kit in COMBO_KIT[faction].values()]
            self.assertEqual(len(set(sounds)), len(sounds), faction)

    def test_every_combination_has_its_own_colour(self):
        for faction in FACTIONS:
            colours = [kit["colour"] for kit in COMBO_KIT[faction].values()]
            self.assertEqual(len(set(colours)), len(colours), faction)

    def test_ultimate_names_are_unique_within_a_faction(self):
        for faction in FACTIONS:
            names = [u["name"] for kit in COMBO_KIT[faction].values() for u in kit["ultimates"]]
            self.assertEqual(len(set(names)), len(names), faction)


class RenameTests(unittest.TestCase):
    def test_a_combined_unit_is_named_after_its_combination(self):
        unit = combined("human", "stalker")
        self.assertEqual(unit.display_name, "Stalker")

    def test_the_form_shows_under_the_combined_name_at_level_four(self):
        unit = combined("human", "stalker", level=4)
        unit.ultimate_index, unit.ultimate = 1, COMBO_KIT["human"]["stalker"]["ultimates"][1]
        self.assertEqual(unit.display_name, "Stalker")
        self.assertEqual(unit.form_name, "Kill Shot")

    def test_a_plain_unit_still_has_its_role_name(self):
        self.assertEqual(Unit("human", "rapid", 1, 1).display_name, "Rifleman")
        self.assertIsNone(Unit("human", "rapid", 1, 1).form_name)

    def test_combining_announces_the_combined_name(self):
        game = Game("human")
        game.gold = 10_000
        recipe = COMBINATIONS["human"]["stalker"]
        partner_cell = next((c, r) for c in range(MAP_COLS - 1) for r in range(MAP_ROWS)
                            if all(game.map.is_buildable(x, r) and game.unit_at(x, r) is None for x in (c, c + 1)))
        first = game.place(*partner_cell, "sniper")
        game.place(partner_cell[0] + 1, partner_cell[1], "rocket")
        game.selected_unit = first
        self.assertTrue(game.combine())
        self.assertIn(recipe["name"], game.message)
        self.assertEqual(game.selected_unit.display_name, recipe["name"])


class PathTests(unittest.TestCase):
    def test_level_two_applies_the_first_path_step_on_top_of_the_level(self):
        # Siege Gun: the first path step is 35% damage. Level 2 adds the usual 1.4x damage on top of that
        step = COMBO_KIT["human"]["siege_gun"]["path"][0]
        level1 = combined("human", "siege_gun", level=1).stats["damage"]
        level2 = combined("human", "siege_gun", level=2).stats["damage"]
        self.assertAlmostEqual(level2 / level1, 1.4 * step["mods"]["damage"])

    def test_level_three_applies_the_second_path_step(self):
        # Its second path step is a wider blast. Level 3 is the first level where it shows
        step = COMBO_KIT["human"]["siege_gun"]["path"][1]
        level2 = combined("human", "siege_gun", level=2).stats["splash"]
        level3 = combined("human", "siege_gun", level=3).stats["splash"]
        self.assertAlmostEqual(level3 / level2, step["mods"]["splash"])

    def test_the_path_is_not_applied_to_a_plain_unit(self):
        plain = Unit("human", "sniper", 5, 5)
        plain.level = 2
        self.assertAlmostEqual(plain.stats["damage"], plain.base["damage"] * 1.4)


class UltimateTests(unittest.TestCase):
    def test_a_combined_unit_chooses_from_its_own_ultimates(self):
        unit = combined("human", "stalker", level=3)
        self.assertEqual(unit.ultimate_options, COMBO_KIT["human"]["stalker"]["ultimates"])
        self.assertNotEqual(unit.ultimate_options, Unit("human", "sniper", 1, 1).ultimate_options)

    def test_choosing_an_ultimate_gives_the_combo_form(self):
        game, unit = fused_in_game("human", "stalker", level=3)
        self.assertTrue(game.choose_ultimate(1))
        self.assertEqual(unit.level, 4)
        self.assertEqual(unit.ultimate["name"], "Kill Shot")

    def test_switching_to_the_other_combo_form_works(self):
        game, unit = fused_in_game("human", "stalker", level=3)
        game.choose_ultimate(0)
        self.assertTrue(game.choose_ultimate(1))
        self.assertEqual(unit.ultimate["name"], "Kill Shot")

    def test_a_plain_unit_still_uses_the_role_ultimates(self):
        plain = Unit("human", "rapid", 1, 1)
        self.assertEqual(plain.ultimate_options[0]["name"], "Gatling Squad")

    def test_the_ultimate_survives_a_save(self):
        game, unit = fused_in_game("zombie", "death_shroud", level=3)
        game.choose_ultimate(1)
        loaded = run_from_data(run_to_data(game))
        loaded_unit = loaded.units[0]
        self.assertEqual(loaded_unit.recipe, "death_shroud")
        self.assertEqual(loaded_unit.ultimate["name"], COMBO_KIT["zombie"]["death_shroud"]["ultimates"][1]["name"])


class LookTests(unittest.TestCase):
    def test_each_combination_fires_its_own_sound(self):
        plain = fire_sample("human", "sniper")
        for recipe_id in COMBINATIONS["human"]:
            shot = fire_sample("human", "sniper", 0, recipe_id)
            self.assertTrue(np.all(np.isfinite(shot)), recipe_id)
            self.assertGreater(np.max(np.abs(shot)), 0.01, recipe_id)
            n = min(len(shot), len(plain), 400)
            self.assertFalse(np.allclose(shot[:n], plain[:n]), recipe_id)

    def test_zombie_combination_sounds_are_finite(self):
        for recipe_id in COMBINATIONS["zombie"]:
            self.assertTrue(np.all(np.isfinite(fire_sample("zombie", "rapid", 0, recipe_id))), recipe_id)

    def test_a_combined_shot_carries_its_colour_and_kit(self):
        unit = combined("human", "stalker", level=1)
        target = Enemy("zombie", "walker", make_map(0).route)
        shot = Projectile(unit.x, unit.y, "human", "sniper", target, unit.stats, owner=unit)
        self.assertEqual(shot.kit, COMBO_KIT["human"]["stalker"])
        self.assertEqual(shot.colour, COMBO_KIT["human"]["stalker"]["colour"])

    def test_a_plain_shot_keeps_the_role_colour(self):
        from config import SHOT_COLOURS
        unit = Unit("human", "sniper", 5, 5)
        target = Enemy("zombie", "walker", make_map(0).route)
        shot = Projectile(unit.x, unit.y, "human", "sniper", target, unit.stats, owner=unit)
        self.assertIsNone(shot.kit)
        self.assertEqual(shot.colour, SHOT_COLOURS["human"]["sniper"])

    def test_every_impact_style_makes_a_flourish(self):
        for style in IMPACTS:
            self.assertTrue(_combo_impact(style, 3.0, 3.0, (200, 100, 50)), style)

    def test_every_combination_draws_at_every_level(self):
        for faction in FACTIONS:
            for recipe_id in COMBINATIONS[faction]:
                for level in (1, 2, 3):
                    _, unit = fused_in_game(faction, recipe_id, level)
                    self.assertTrue(unit.stats)  # The stats, path included, build without error
                    self.assertEqual(unit.display_name, COMBINATIONS[faction][recipe_id]["name"])


class AppDrawTests(unittest.TestCase):
    """The HUD draws a combined unit's panel at each level and with each ultimate, with no error."""

    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()

    def test_the_unit_panel_draws_for_a_combined_unit_at_each_level(self):
        from app import App
        from settings import DEFAULTS
        patches = [
            mock.patch("app.load_settings", side_effect=lambda *a, **k: dict(DEFAULTS)),
            mock.patch("app.load_records", return_value={}),
            mock.patch("app.save_settings", return_value=True),
            mock.patch("app.save_records", return_value=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        app = App()
        app.settings["skip_briefing"] = True
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h, mod=0, unicode="", scancode=0))
        game = app.game
        game.gold = 100_000
        for level in (1, 2, 3, 4):
            unit = combined("human", "stalker", level=min(level, 3))
            if level == 4:
                unit.level, unit.ultimate_index = 4, 0
                unit.ultimate = COMBO_KIT["human"]["stalker"]["ultimates"][0]
            game.units[:] = [unit]
            game.all_units[:] = [unit]
            game.selected_unit = unit
            app.draw((0, 0))  # Must not raise


if __name__ == "__main__":
    unittest.main()
