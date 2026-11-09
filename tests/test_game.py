import unittest

from camera import Camera
from config import (PATH, START_GOLD, START_LIVES, WAVE_BONUS, MAP_EVERY, MAP_COLS, MAP_ROWS, MAX_UNITS, OPPONENT, UNIT_TYPES,
                    ENEMY_TYPES, UPGRADE_COST, ULTIMATES, ROLES, SELL_REFUND, MAP_BUILD_SECONDS, AUTO_START_SECONDS,
                    WAVE_BONUS_GROWTH)
from enemies import Enemy
from save import run_from_data, run_to_data
from game import Game
from waves import build_wave, hp_multiplier, preview
from world import make_map, generate_path, in_bounds


def run_until_idle(game, limit=20000, dt=0.05):
    """Advance the game until the round is over (or the game ends). Fails if it takes too long."""
    for _ in range(limit):
        if not game.wave_active or game.status != "playing":
            return
        game.update(dt)
    raise AssertionError("round did not finish")


def total_wave_hp(wave):
    """Hp of a round's regular enemies. Boss rounds add a boss, which is measured separately."""
    return sum(ENEMY_TYPES["zombie"][kind]["hp"] * hp_multiplier(wave) for _, kind in build_wave("zombie", wave)
               if kind != "boss")


ROUND_ONE = sum(preview("zombie", 1).values())  # How many enemies round 1 brings


class WorldTests(unittest.TestCase):

    def test_classic_path_is_axis_aligned_and_in_bounds(self):
        for (ax, ay), (bx, by) in zip(PATH, PATH[1:]):
            self.assertTrue(ax == bx or ay == by, f"diagonal segment {(ax, ay)} to {(bx, by)}")
        for c, r in PATH:
            self.assertTrue(in_bounds(c, r))

    def test_generated_routes_are_valid(self):
        generated = 0
        for index in range(1, 21):
            m = make_map(index)
            path = m.path
            for (ax, ay), (bx, by) in zip(path, path[1:]):
                self.assertTrue(ax == bx or ay == by, f"map {index} has a diagonal")
            self.assertEqual(path[0][0], 0)
            self.assertEqual(path[-1][0], MAP_COLS - 1)
            for c, r in path:
                self.assertTrue(in_bounds(c, r))
            if path != PATH:
                generated += 1
        self.assertGreaterEqual(generated, 15)  # The generator should almost always find a route

    def test_doodads_never_touch_the_route(self):
        for index in range(0, 11):
            m = make_map(index)
            for x, y, _ in m.doodads:
                c, r = int(x), int(y)
                for dc in (-1, 0, 1):
                    for dr in (-1, 0, 1):
                        self.assertNotIn((c + dc, r + dr), m.cells, f"map {index} doodad touches route")

    def test_doodads_block_building(self):
        for index in range(0, 11):
            m = make_map(index)
            for x, y, _ in m.doodads:
                self.assertFalse(m.is_buildable(int(x), int(y)))

    def test_every_map_leaves_room_for_the_full_unit_cap(self):
        for index in range(0, 21):
            m = make_map(index)
            room = sum(m.is_buildable(c, r) for c in range(MAP_COLS) for r in range(MAP_ROWS))
            self.assertGreaterEqual(room, MAX_UNITS, f"map {index} has only {room} buildable tiles")

    def test_markers_sit_at_the_route_ends(self):
        for index in (0, 3):
            m = make_map(index)
            self.assertEqual(m.start, m.route[0])
            self.assertEqual(m.end, m.route[-1])
            self.assertEqual(m.end[0], MAP_COLS - 0.5)

    def test_maps_are_fixed_per_index(self):
        self.assertEqual(generate_path(42), generate_path(42))
        self.assertEqual(make_map(3).path, make_map(3).path)

    def test_cannot_build_on_path_or_off_map(self):
        m = make_map(0)
        self.assertFalse(m.is_buildable(*PATH[0]))  # On the route
        self.assertFalse(m.is_buildable(-1, 0))
        self.assertFalse(m.is_buildable(16, 0))
        self.assertTrue(m.is_buildable(5, 0))

    def test_screen_click_maps_back_to_the_tile(self):
        camera = Camera()
        for col, row in [(0, 0), (5, 7), (15, 11), (8, 1)]:
            px, py, _ = camera.project(col + 0.5, row + 0.5)
            self.assertEqual(camera.screen_to_tile(px * 2, py * 2), (col, row))

    def test_click_above_horizon_is_off_map(self):
        self.assertIsNone(Camera().screen_to_tile(500, 0))


class PlacementTests(unittest.TestCase):

    def test_placement_spends_gold_and_blocks_same_cell(self):
        game = Game("human")
        cost = UNIT_TYPES["human"]["rapid"]["cost"]
        self.assertIsNotNone(game.place(5, 0))
        self.assertEqual(game.gold, START_GOLD - cost)
        self.assertIsNone(game.place(5, 0))
        self.assertEqual(game.gold, START_GOLD - cost)
        self.assertEqual(game.message, "A unit is already there. Click it to select it")

    def test_cannot_afford_unit(self):
        game = Game("zombie")
        game.gold = 10
        self.assertIsNone(game.place(5, 0))
        self.assertEqual(game.message, f"Need {UNIT_TYPES['zombie']['rapid']['cost']} gold for a Spitter, you have 10")

    def test_every_role_can_be_built(self):
        game = Game("human")
        game.gold = 10000
        for i, role in enumerate(ROLES):
            self.assertIsNotNone(game.place(i, 0, role), role)

    def test_player_units_use_player_faction(self):
        game = Game("zombie")
        self.assertEqual(game.place(5, 0).faction, "zombie")
        self.assertEqual(game.enemy_faction, OPPONENT["zombie"])


class SelectionAndUpgradeTests(unittest.TestCase):

    def test_clicking_a_unit_selects_it_and_clicking_empty_ground_builds(self):
        game = Game("human")
        game.gold = 500
        unit = game.place(5, 0, "rapid")
        game.click_cell(5, 0)
        self.assertIs(game.selected_unit, unit)
        game.click_cell(6, 0)
        self.assertIsNone(game.selected_unit)
        self.assertEqual(len(game.units), 2)

    def test_upgrade_path_to_level_four_then_ultimate(self):
        game = Game("human")
        game.gold = 1000
        unit = game.place(5, 0, "rapid")
        game.click_cell(5, 0)
        cost = UNIT_TYPES["human"]["rapid"]["cost"]

        self.assertTrue(game.upgrade())  # Level 2
        self.assertTrue(game.upgrade())  # Level 3
        self.assertEqual(unit.level, 3)
        spent = round(cost * UPGRADE_COST[0]) + round(cost * UPGRADE_COST[1])
        self.assertEqual(game.gold, 1000 - cost - spent)

        self.assertFalse(game.upgrade())  # Level 3 can't be upgraded with U: it needs an ultimate
        self.assertEqual(unit.level, 3)

        self.assertTrue(game.choose_ultimate(0))  # Level 4
        self.assertEqual(unit.level, 4)
        self.assertEqual(unit.ultimate, ULTIMATES["human"]["rapid"][0])
        self.assertTrue(game.choose_ultimate(1))  # Switching between rounds costs half the unit price
        self.assertEqual(unit.ultimate, ULTIMATES["human"]["rapid"][1])

    def test_spent_gold_is_tracked_for_refunds(self):
        game = Game("human")
        game.gold = 1000
        unit = game.place(5, 0, "rapid")
        game.click_cell(5, 0)
        game.upgrade()
        self.assertEqual(unit.spent, UNIT_TYPES["human"]["rapid"]["cost"] + round(50 * UPGRADE_COST[0]))

    def test_ultimate_needs_level_three(self):
        game = Game("zombie")
        game.gold = 1000
        game.place(5, 0, "sniper")
        game.click_cell(5, 0)
        self.assertFalse(game.choose_ultimate(0))
        self.assertEqual(game.message, "Reach level 3 first")

    def test_upgrade_needs_gold(self):
        game = Game("human")
        game.gold = 100
        game.place(5, 0, "rapid")
        game.click_cell(5, 0)
        game.gold = 5
        self.assertFalse(game.upgrade())
        self.assertEqual(game.message, f"Need {game.upgrade_cost(game.selected_unit)} gold")

    def test_selling_refunds_a_share_of_everything_spent(self):
        game = Game("human")
        game.gold = 1000
        game.place(5, 0, "rapid")
        game.click_cell(5, 0)
        game.upgrade()  # Level 2: adds to the spent total
        before = game.gold
        spent = game.selected_unit.spent
        self.assertFalse(game.sell())  # The first click only arms the sale
        self.assertEqual(len(game.units), 1)
        self.assertTrue(game.sell())  # The second click confirms it
        self.assertEqual(game.units, [])
        self.assertIsNone(game.selected_unit)
        self.assertEqual(game.gold, before + round(spent * SELL_REFUND))

    def test_selling_needs_a_selected_unit(self):
        game = Game("human")
        game.place(5, 0, "rapid")
        self.assertFalse(game.sell())
        self.assertEqual(len(game.units), 1)

    def test_support_aura_speeds_up_neighbours(self):
        game = Game("human")
        game.gold = 1000
        game.place(5, 0, "support")
        neighbour = game.place(6, 0, "rapid")
        game.update(0.0)
        self.assertAlmostEqual(neighbour.buff, UNIT_TYPES["human"]["support"]["aura"][1])

    def test_aura_does_not_reach_far_units(self):
        game = Game("human")
        game.gold = 1000
        game.place(5, 0, "support")
        far = game.place(12, 0, "rapid")  # Well outside the 2.5 tile aura
        game.update(0.0)
        self.assertEqual(far.buff, 1.0)


class EnemyTests(unittest.TestCase):

    def test_enemy_walks_along_route(self):
        route = make_map(0).route
        enemy = Enemy("zombie", "walker", route)  # Speed 1.2 tiles per second
        start_x = enemy.x
        enemy.advance(1.0)
        self.assertAlmostEqual(enemy.x, start_x + 1.2)
        self.assertAlmostEqual(enemy.y, route[0][1])

    def test_enemy_reports_end_of_route(self):
        enemy = Enemy("human", "scout", make_map(0).route)
        done = False
        for _ in range(10000):
            if enemy.advance(0.05):
                done = True
                break
        self.assertTrue(done)


class WaveTests(unittest.TestCase):

    def test_each_round_is_harder_than_the_last(self):
        hp = [total_wave_hp(w) for w in range(1, 41)]
        for before, after in zip(hp, hp[1:]):
            self.assertGreater(after, before)

    def test_each_round_has_at_least_as_many_spawns(self):
        counts = [len(build_wave("human", w)) for w in range(1, 41)]
        for before, after in zip(counts, counts[1:]):
            self.assertGreaterEqual(after, before)
        self.assertGreater(counts[-1], counts[0])

    def test_spawn_times_are_sorted(self):
        times = [t for t, _ in build_wave("human", 7)]
        self.assertEqual(times, sorted(times))

    def test_start_wave_only_once_at_a_time(self):
        game = Game("human")
        self.assertTrue(game.start_wave())
        self.assertFalse(game.start_wave())
        self.assertEqual(game.wave, 1)


class RulesTests(unittest.TestCase):

    def test_leaking_enemies_cost_lives_and_pay_nothing(self):
        game = Game("human")  # Round 1 is only basic enemies, and no towers are built
        game.start_wave()
        run_until_idle(game)
        self.assertEqual(game.kills, 0)
        self.assertEqual(game.lives, START_LIVES - ROUND_ONE)
        self.assertEqual(game.gold, START_GOLD + WAVE_BONUS)
        self.assertEqual(game.status, "playing")

    def test_towers_kill_and_are_paid(self):
        game = Game("human")
        game.gold = 1000
        for col in (5, 6, 7):  # Row 0 runs beside the first lane of the classic map
            self.assertIsNotNone(game.place(col, 0, "rapid"))
        game.start_wave()
        rewards, seen = [], 0
        for _ in range(20000):  # Record what each kill paid, since combos change the reward
            game.update(0.05)
            if game.kills > seen:
                rewards.append(game.gain)
                seen = game.kills
            if not game.wave_active and not game.enemies:
                break
        leaked = START_LIVES - game.lives
        self.assertGreater(game.kills, 0)
        self.assertEqual(game.kills + leaked, ROUND_ONE)  # Every enemy either died or leaked
        spent = 3 * UNIT_TYPES["human"]["rapid"]["cost"]
        self.assertEqual(game.gold, 1000 - spent + sum(rewards) + WAVE_BONUS)

    def test_losing_all_lives_ends_game(self):
        game = Game("zombie")
        game.lives = 1
        game.start_wave()
        run_until_idle(game)
        self.assertEqual(game.status, "lost")
        self.assertEqual(game.lives, 0)
        self.assertIsNone(game.place(5, 0))

    def test_sandbox_never_ends_on_a_round_count(self):
        game = Game("human")
        game.wave = 60
        game.lives = 10 ** 6  # Leaks would cost lives; this only checks that the round count never ends the game
        game.enemies = []
        game._queue = []
        game.start_wave()
        run_until_idle(game)
        self.assertEqual(game.status, "playing")
        self.assertTrue(game.start_wave())

    def clear_round(self, game):
        """End the running round at once, as if its last enemy had been dealt with."""
        game._queue = []
        game.enemies = []
        game.update(0.05)

    def test_route_changes_when_round_ten_clears(self):
        game = Game("human")
        game.wave = MAP_EVERY - 1
        game.start_wave()  # Round 10 still uses the first map
        self.assertEqual(game.map.index, 0)
        self.clear_round(game)
        self.assertEqual(game.map.index, 1)  # The new route appears at once, before round 11
        self.assertTrue(game.countdown_locked)

    def test_the_map_build_time_is_a_real_minute_even_at_fast_speed(self):
        game = Game("human")
        game.wave = MAP_EVERY - 1
        game.start_wave()
        self.clear_round(game)
        self.assertFalse(game.start_wave(), "SPACE cannot skip the build time")
        for _ in range(30):  # Four times game speed, one real second per step
            game.update(4.0, real_dt=1.0)
        self.assertTrue(game.countdown_locked)
        self.assertFalse(game.wave_active)
        self.assertAlmostEqual(game.countdown, MAP_BUILD_SECONDS - 30)
        for _ in range(30):
            game.update(4.0, real_dt=1.0)
        self.assertTrue(game.wave_active)  # The round starts itself when the minute is up
        self.assertEqual(game.wave, MAP_EVERY + 1)
        self.assertFalse(game.countdown_locked)

    def test_the_build_time_does_not_apply_between_ordinary_rounds(self):
        game = Game("human")
        game.wave = 3
        game.start_wave()
        self.clear_round(game)
        self.assertFalse(game.countdown_locked)
        self.assertEqual(game.countdown, AUTO_START_SECONDS)

    def test_units_on_the_new_route_are_refunded_when_round_ten_clears(self):
        game = Game("human")
        game.gold = 500
        new_cells = sorted(make_map(1).cells)
        target = next(c for c in new_cells if game.map.is_buildable(*c))
        game.place(*target, "rapid")
        self.assertEqual(game.gold, 450)
        game.wave = MAP_EVERY - 1
        game.start_wave()  # Round 10 runs, and clearing it is what changes the map
        self.clear_round(game)
        self.assertEqual(len(game.units), 0)
        bonus = WAVE_BONUS + WAVE_BONUS_GROWTH * (MAP_EVERY - 1)
        self.assertEqual(game.gold, 450 + 50 + bonus)  # The unit is refunded in full

    def test_the_build_time_survives_a_save(self):
        game = Game("human")
        game.wave = MAP_EVERY - 1
        game.start_wave()
        self.clear_round(game)
        game.countdown = 42.0
        loaded = run_from_data(run_to_data(game))
        self.assertTrue(loaded.countdown_locked)
        self.assertEqual(loaded.countdown, 42.0)

    def test_hud_feed_records_kills(self):
        game = Game("human")
        game.gold = 1000
        game.place(5, 1, "rapid")
        game.start_wave()
        run_until_idle(game)
        self.assertTrue(any("eliminated" in text or "breached" in text for text, _, _ in game.feed))


if __name__ == "__main__":
    unittest.main()
