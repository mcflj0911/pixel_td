import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # Draw without a real window

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from camera import Camera  # noqa: E402
from config import DEATH_SECONDS, MAP_COLS, MAP_ROWS, MOVE_SECONDS, ROLES  # noqa: E402
from enemies import Corpse, Enemy  # noqa: E402
from game import Game  # noqa: E402
from render import _draw_corpse, _draw_enemy, draw_scene  # noqa: E402
from sounds import Sounds, death_sample, fire_sample  # noqa: E402


def free_pair(game):
    """Two free buildable tiles side by side."""
    for col in range(MAP_COLS - 1):
        for row in range(MAP_ROWS):
            if all(game.map.is_buildable(c, row) and game.unit_at(c, row) is None for c in (col, col + 1)):
                return (col, row), (col + 1, row)
    raise AssertionError("no two free tiles")


class ZombieSoundTests(unittest.TestCase):
    def test_every_zombie_role_has_its_own_clean_shot(self):
        for role in ROLES:
            x = fire_sample("zombie", role)
            self.assertTrue(np.all(np.isfinite(x)), role)
            self.assertGreater(np.max(np.abs(x)), 0.01, role)

    def test_zombie_shots_differ_from_each_other(self):
        samples = {role: fire_sample("zombie", role) for role in ROLES}
        for a in ROLES:
            for b in ROLES:
                if a < b:
                    n = min(len(samples[a]), len(samples[b]))
                    self.assertGreater(np.abs(samples[a][:n] - samples[b][:n]).mean(), 0.01, f"{a} vs {b}")

    def test_zombie_shots_are_not_the_human_shots(self):
        for role in ROLES:
            n = 400
            self.assertFalse(np.allclose(fire_sample("human", role)[:n], fire_sample("zombie", role)[:n]), role)

    def test_zombie_and_human_deaths_sound_different(self):
        zombie, human = death_sample("zombie"), death_sample("human")
        for x in (zombie, human):
            self.assertTrue(np.all(np.isfinite(x)))
            self.assertGreater(np.max(np.abs(x)), 0.05)
        n = min(len(zombie), len(human))
        self.assertGreater(np.abs(zombie[:n] - human[:n]).mean(), 0.01)

    def test_a_death_event_plays_a_sound_once_then_is_rate_limited(self):
        sounds = Sounds()
        sounds.enabled, sounds.muted = True, False  # No mixer in tests, so turn playing on by hand
        with mock.patch("sounds._array_sound", side_effect=lambda x: mock.Mock()) as make:
            sounds.play_event(("death", "zombie"))
            sounds.play_event(("death", "zombie"))
        self.assertEqual(make.call_count, 1)


class WalkTests(unittest.TestCase):
    def test_a_walking_enemy_counts_the_ground_it_covers(self):
        game = Game("human")
        enemy = Enemy("zombie", "walker", game.map.route)
        self.assertEqual(enemy.walk, 0.0)
        enemy.advance(1.0)
        self.assertGreater(enemy.walk, 0.0)

    def test_a_walking_enemy_draws_on_either_frame(self):
        game = Game("human")
        enemy = Enemy("zombie", "walker", game.map.route)
        scene, camera = pygame.Surface((500, 360)), Camera()
        for walked in (0.0, 0.3):  # The two frames of the walk cycle
            enemy.walk = walked
            _draw_enemy(scene, camera, enemy)


class CorpseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()  # Drawing labels needs a font

    def setUp(self):
        self.game = Game("human")

    def test_a_killed_enemy_leaves_a_corpse_that_is_gone_after_a_moment(self):
        enemy = Enemy("zombie", "walker", self.game.map.route)
        self.game.enemies.append(enemy)
        enemy.hp = 0
        self.game._resolve_deaths()
        self.assertEqual(len(self.game.corpses), 1)
        self.assertIn(("death", "zombie"), self.game.sound_events)
        self.game.update(DEATH_SECONDS / 2)
        self.assertEqual(len(self.game.corpses), 1)
        self.game.update(DEATH_SECONDS)
        self.assertEqual(self.game.corpses, [])

    def test_a_leaked_enemy_leaves_no_corpse(self):
        enemy = Enemy("zombie", "walker", self.game.map.route)
        self.game.enemies.append(enemy)
        enemy.hp = 0
        enemy.leaked = True
        self.game._resolve_deaths()
        self.assertEqual(self.game.corpses, [])

    def test_progress_runs_from_standing_to_gone(self):
        corpse = Corpse(Enemy("zombie", "walker", self.game.map.route))
        self.assertEqual(corpse.progress, 0.0)
        self.assertTrue(corpse.update(DEATH_SECONDS / 2))
        self.assertFalse(corpse.update(DEATH_SECONDS))
        self.assertEqual(corpse.progress, 1.0)

    def test_a_flying_corpse_remembers_it_flew(self):
        corpse = Corpse(Enemy("zombie", "crow", self.game.map.route))
        self.assertTrue(corpse.flying)

    def test_fallen_enemies_draw_without_error(self):
        enemy = Enemy("zombie", "walker", self.game.map.route)
        self.game.enemies.append(enemy)
        enemy.hp = 0
        self.game._resolve_deaths()
        draw_scene(Camera(), self.game, None)
        _draw_corpse(pygame.Surface((500, 360)), Camera(), self.game.corpses[0])


class MoveHopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def setUp(self):
        self.game = Game("human")
        self.game.gold = 10_000

    def test_a_moved_unit_hops_for_a_moment_then_settles(self):
        here, there = free_pair(self.game)
        unit = self.game.place(*here, "rapid")
        self.assertTrue(self.game.move_unit(unit, *there))
        self.assertEqual(unit.move_time, MOVE_SECONDS)
        self.assertEqual(unit.move_from, (here[0] + 0.5, here[1] + 0.5))
        unit.update(MOVE_SECONDS, [])
        self.assertEqual(unit.move_time, 0.0)

    def test_a_hopping_unit_draws_without_error(self):
        here, there = free_pair(self.game)
        unit = self.game.place(*here, "rapid")
        self.game.move_unit(unit, *there)
        draw_scene(Camera(), self.game, None)


if __name__ == "__main__":
    unittest.main()
