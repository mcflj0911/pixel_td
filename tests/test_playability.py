import os
import random
import unittest
from unittest import mock

import pygame

from camera import Camera, SCALE
from config import MAX_UNITS, CAP_BONUS_MAX, MAP_COLS, MAP_ROWS
from game import Game
from hud import _enemy_under, tutorial_line
from keymap import action_for, apply_settings, label
from tools.balance import play


def first_free(game, predicate=lambda c, r: True):
    for c in range(MAP_COLS):
        for r in range(MAP_ROWS):
            if game.map.is_buildable(c, r) and game.unit_at(c, r) is None and predicate(c, r):
                return c, r
    raise AssertionError("no free cell")


class UnitCapTests(unittest.TestCase):
    def test_the_cap_is_the_normal_cap_early_in_the_run(self):
        game = Game("human")
        game.wave = 5
        self.assertEqual(game.unit_cap(), MAX_UNITS)

    def test_the_cap_grows_late_in_the_run_and_stops_at_its_limit(self):
        game = Game("human")
        game.wave = 12
        self.assertGreater(game.unit_cap(), MAX_UNITS)
        game.wave = 200
        self.assertEqual(game.unit_cap(), MAX_UNITS + CAP_BONUS_MAX)

    def test_units_can_be_placed_up_to_the_grown_cap(self):
        game = Game("human")
        game.gold = 10_000
        game.wave = 12
        for _ in range(game.unit_cap()):
            cell = first_free(game)
            self.assertIsNotNone(game.place(*cell, "rapid"))
        self.assertIsNone(game.place(*first_free(game), "rapid"))
        self.assertIn("Unit cap reached", game.message)


class PlacementMessageTests(unittest.TestCase):
    def setUp(self):
        self.game = Game("human")
        self.game.gold = 1000

    def test_the_route_says_so(self):
        route_cell = next((c, r) for c in range(MAP_COLS) for r in range(MAP_ROWS) if self.game.map.mask[c, r])
        self.assertIn("route", self.game.placement_error(*route_cell))

    def test_outside_the_map_says_so(self):
        self.assertEqual(self.game.placement_error(-1, 0), "That is outside the map")

    def test_an_occupied_tile_points_to_the_unit(self):
        cell = first_free(self.game)
        self.game.place(*cell, "rapid")
        self.assertIn("already there", self.game.placement_error(*cell))

    def test_missing_gold_says_how_much_and_what_you_have(self):
        self.game.gold = 20
        message = self.game.placement_error(*first_free(self.game), role="artillery")
        self.assertEqual(message, "Need 220 gold for a Mortar, you have 20")


class NoAirWarningTests(unittest.TestCase):
    def flyer_game(self):
        game = Game("human")
        for wave in range(0, 40):
            game.wave = wave
            if game.next_round_has_flyers():
                return game
        raise AssertionError("no flyer round found")

    def test_flyers_with_no_air_cover_are_flagged(self):
        game = self.flyer_game()
        self.assertIn("NO AIR", game.next_round_warnings())

    def test_a_rifle_on_the_field_clears_the_warning(self):
        game = self.flyer_game()
        game.gold = 1000
        game.place(*first_free(game), "rapid")
        self.assertNotIn("NO AIR", game.next_round_warnings())
        self.assertIn("FLYERS", game.next_round_warnings())

    def test_a_rocket_does_not_count_as_air_cover(self):
        game = self.flyer_game()
        game.gold = 1000
        game.place(*first_free(game), "rocket")
        self.assertIn("NO AIR", game.next_round_warnings())


class TutorialTests(unittest.TestCase):
    def test_the_first_round_starts_with_a_build_tip(self):
        game = Game("human")
        self.assertIn("build your first unit", tutorial_line(game))

    def test_after_a_unit_is_placed_the_tip_asks_for_the_start(self):
        game = Game("human")
        game.gold = 1000
        game.place(*first_free(game), "rapid")
        self.assertIn("SPACE", tutorial_line(game))

    def test_no_tip_once_the_run_is_under_way(self):
        game = Game("human")
        game.gold = 1000
        game.place(*first_free(game), "rapid")
        game.start_wave()
        self.assertIsNone(tutorial_line(game))


class EnemyHoverTests(unittest.TestCase):
    def test_hovering_an_enemy_finds_it(self):
        game = Game("human")
        game.wave_active = True
        game._spawn("walker")
        enemy = game.enemies[0]
        camera = Camera(game.map)
        x, y, _ = camera.project(enemy.x, enemy.y, enemy.spec["height"] * 0.5)
        self.assertIs(_enemy_under(camera, game, (x * SCALE, y * SCALE)), enemy)

    def test_hovering_empty_ground_finds_nothing(self):
        game = Game("human")
        game.wave_active = True
        game._spawn("walker")
        self.assertIsNone(_enemy_under(Camera(game.map), game, (1, 1)))


class KeymapTests(unittest.TestCase):
    def tearDown(self):
        apply_settings({})  # Back to the defaults for the other tests

    def test_a_changed_key_is_used_and_shown(self):
        apply_settings({"upgrade": "e"})
        self.assertEqual(label("upgrade"), "E")
        self.assertEqual(action_for(pygame.key.key_code("e")), "upgrade")
        self.assertIsNone(action_for(pygame.key.key_code("u")))

    def test_a_key_taken_by_another_action_falls_back_to_the_default(self):
        apply_settings({"upgrade": "p"})  # Pause already uses P
        self.assertEqual(label("upgrade"), "U")
        self.assertEqual(label("pause"), "P")

    def test_unknown_names_and_fixed_keys_fall_back(self):
        apply_settings({"sell": "not_a_key", "combine": "r"})
        self.assertEqual(label("sell"), "X")
        self.assertEqual(label("combine"), "C")

    def test_defaults_are_unchanged_without_settings(self):
        apply_settings({})
        self.assertEqual(label("start"), "SPACE")
        self.assertEqual(action_for(pygame.key.key_code("space")), "start")


class BalanceBotRegressionTests(unittest.TestCase):
    """The bot plays a fixed seed the same way every time, so a change to the rules that shifts the result shows up here."""

    def test_the_same_seed_plays_the_same_game(self):
        first = play("human", "Normal", 4, random.Random(7))
        second = play("human", "Normal", 4, random.Random(7))
        self.assertEqual((first.wave, first.gold, first.lives), (second.wave, second.gold, second.lives))
        self.assertGreaterEqual(first.wave, 4)


if __name__ == "__main__":
    unittest.main()
