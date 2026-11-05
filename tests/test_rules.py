import os
import tempfile
import unittest

from config import (MAX_UNITS, AUTO_START_SECONDS, SELL_CONFIRM_SECONDS, BOSS_EVERY, FLY_HEIGHT,
                    ENEMY_TYPES, ULTIMATES)
from units import group_multiplier
from enemies import Enemy
from game import Game
from projectiles import Projectile
from units import Unit
from waves import build_wave, preview, BOSS
from world import make_map


class FlyingTests(unittest.TestCase):

    def test_only_air_roles_can_target_flyers(self):
        route = make_map(0).route
        crow = Enemy("zombie", "crow", route)
        self.assertTrue(crow.flying)
        self.assertIsNotNone(Unit("human", "rapid", *route[0]).pick_target([crow]))
        self.assertIsNone(Unit("human", "splash", *route[0]).pick_target([crow]))
        self.assertIsNone(Unit("human", "flame", *route[0]).pick_target([crow]))

    def test_flyers_take_the_straight_line_between_the_markers(self):
        game = Game("human")
        game.wave_active = True
        game._spawn("crow")  # Human players face zombies, so the flyer is a crow
        crow = game.enemies[0]
        self.assertEqual(crow.route, [game.map.route[0], game.map.route[-1]])
        self.assertGreater(len(game.map.route), 2)  # The ground route bends; the flyer does not

    def test_splash_does_not_reach_flyers(self):
        route = make_map(0).route
        crow = Enemy("zombie", "crow", route)
        crow.x, crow.y = 5.5, 5.5
        target = Enemy("zombie", "walker", route)
        target.x, target.y = 5.5, 5.5
        stats = dict(Unit("human", "splash", 5.5, 5.5).stats)
        shot = Projectile(5.5, 5.5, "human", "splash", target, stats)
        shot._impact([crow, target], [], [])
        self.assertEqual(crow.hp, crow.max_hp)

    def test_shots_at_flyers_rise_to_flying_height(self):
        route = make_map(0).route
        crow = Enemy("zombie", "crow", route)
        crow.x, crow.y = route[0][0] + 3, route[0][1]
        shot = Projectile(route[0][0], route[0][1], "human", "rapid", crow, Unit("human", "rapid", 0, 0).stats)
        self.assertEqual(shot.aim_z, FLY_HEIGHT)


class WaveFeatureTests(unittest.TestCase):

    def test_boss_arrives_at_the_end_of_every_boss_round_only(self):
        for wave in range(1, 21):
            kinds = [k for _, k in build_wave("human", wave)]
            self.assertEqual(BOSS in kinds, wave % BOSS_EVERY == 0, f"round {wave}")
            if BOSS in kinds:
                self.assertEqual(kinds[-1], BOSS)

    def test_flyers_start_at_round_five(self):
        self.assertNotIn("drone", [k for _, k in build_wave("human", 4)])
        self.assertIn("drone", [k for _, k in build_wave("human", 8)])

    def test_preview_matches_the_round_that_runs(self):
        counts = preview("human", 7)
        self.assertEqual(sum(counts.values()), len(build_wave("human", 7)))

    def test_game_previews_the_next_round(self):
        game = Game("human")
        names = dict(game.next_round_preview())
        self.assertIn(ENEMY_TYPES["zombie"]["walker"]["name"], names)


class RulesFeatureTests(unittest.TestCase):

    def test_unit_cap_blocks_building(self):
        game = Game("human")
        game.gold = 10 ** 6
        spots = [(c, r) for c in range(16) for r in range(12) if game.map.is_buildable(c, r)]
        for col, row in spots[:MAX_UNITS]:
            self.assertIsNotNone(game.place(col, row, "rapid"))
        self.assertIsNone(game.place(*spots[MAX_UNITS], "rapid"))
        self.assertIn("Unit cap", game.message)

    def test_auto_start_counts_down_then_starts_the_round(self):
        game = Game("human")
        self.assertFalse(game.wave_active)
        game.update(AUTO_START_SECONDS - 0.5)
        self.assertFalse(game.wave_active)
        game.update(1.0)
        self.assertTrue(game.wave_active)
        self.assertEqual(game.wave, 1)

    def test_sell_confirmation_expires(self):
        game = Game("human")
        game.gold = 1000
        game.place(5, 0, "rapid")
        game.click_cell(5, 0)
        game.sell()
        self.assertTrue(game.sell_armed(game.selected_unit))
        game.update(SELL_CONFIRM_SECONDS + 0.1)
        self.assertFalse(game.sell())  # Expired: this click arms it again instead of selling
        self.assertEqual(len(game.units), 1)

    def test_grouped_units_of_one_type_get_a_damage_bonus(self):
        game = Game("human")
        game.gold = 10 ** 6
        a = game.place(5, 0, "rapid")
        game.place(6, 0, "rapid")
        far = game.place(10, 0, "rapid")
        game.update(0.01)  # Recomputes the groups
        self.assertEqual(a.group, 2)
        self.assertEqual(far.group, 1)
        base = a.base["damage"]
        self.assertAlmostEqual(a.stats["damage"], base * group_multiplier(2))
        self.assertEqual(far.stats["damage"], base)

    def test_mixed_types_do_not_form_a_group(self):
        game = Game("human")
        game.gold = 10 ** 6
        game.place(5, 0, "rapid")
        game.place(6, 0, "sniper")
        game.update(0.01)
        self.assertTrue(all(u.group == 1 for u in game.units))

    def test_report_ranks_damage_and_leaks(self):
        game = Game("human")
        unit = game.place(5, 0, "rapid")
        unit.damage = 120
        game.leaks["Walker"] = 3
        report = game.report()
        self.assertEqual(report["damage"][0][1], 120)
        self.assertEqual(report["leaks"][0], ("Walker", 3))


class SaveTests(unittest.TestCase):

    def test_save_and_load_round_trip(self):
        game = Game("zombie", map_index=2, difficulty="Hard")
        game.gold = 333
        game.lives = 11
        unit = game.place(5, 0, "splash")
        unit.level = 4
        unit.ultimate_index = 1
        unit.ultimate = ULTIMATES["zombie"]["splash"][1]
        game.wave = 4
        gold = game.gold
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "save.json")
            self.assertTrue(game.save(path))
            loaded = Game.load(path)
        self.assertEqual(loaded.faction, "zombie")
        self.assertEqual(loaded.map.index, 2)
        self.assertEqual(loaded.difficulty, "Hard")
        self.assertEqual((loaded.gold, loaded.lives, loaded.wave), (gold, 11, 4))
        self.assertEqual(len(loaded.units), 1)
        self.assertEqual(loaded.units[0].ultimate_index, 1)

    def test_cannot_save_mid_round(self):
        game = Game("human")
        game.start_wave()
        self.assertFalse(game.save(os.path.join(tempfile.gettempdir(), "never.json")))

    def test_bad_file_loads_as_none(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "bad.json")
            with open(path, "w") as f:
                f.write("not json")
            self.assertIsNone(Game.load(path))


if __name__ == "__main__":
    unittest.main()
