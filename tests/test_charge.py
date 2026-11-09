import unittest

from config import CHARGE_DAMAGE, CHARGE_KILLS, COMBINATIONS, MAP_COLS, MAP_ROWS
from enemies import Enemy
from game import Game
from config import ROLES
from projectiles import Blast, Floater, Projectile, _hurt
from save import run_from_data, run_to_data
from units import Unit
from world import make_map


def route():
    return make_map(0).route


def enemy_beside(unit, dx=1.0):
    enemy = Enemy("zombie", "walker", route())
    enemy.x, enemy.y = unit.x + dx, unit.y
    enemy.hp = 10_000  # Tough enough that it survives the test shots
    enemy.max_hp = 10_000
    return enemy


def free_buildable(game, col, row):
    return game.map.is_buildable(col, row) and game.unit_at(col, row) is None


class ChargeTests(unittest.TestCase):
    def test_a_rifle_charges_after_ten_kills(self):
        rifle = Unit("human", "rapid", 1.5, 1.5)
        for _ in range(CHARGE_KILLS - 1):
            rifle.register_kill()
        self.assertFalse(rifle.charged)
        rifle.register_kill()
        self.assertTrue(rifle.charged)

    def test_every_role_charges_for_both_factions(self):
        for faction in ("human", "zombie"):
            for kind in ROLES:
                unit = Unit(faction, kind, 1, 1)
                self.assertTrue(unit.can_charge, (faction, kind))
                for _ in range(CHARGE_KILLS):
                    unit.register_kill()
                self.assertTrue(unit.charged, (faction, kind))

    def test_a_flame_charge_leaves_hotter_fire(self):
        flame = Unit("human", "flame", 1, 1)
        normal = flame.stats["burn"]
        flame.charged, flame.kill_meter = True, CHARGE_KILLS
        target = enemy_beside(flame)
        shot = flame.update(2.0, [target])[0]
        self.assertGreater(shot.stats["burn"][0], normal[0])
        self.assertGreater(shot.stats["burn"][2], normal[2])

    def test_a_charged_mortar_blasts_wider(self):
        mortar = Unit("human", "artillery", 1.5, 1.5)
        normal = mortar.stats["splash"]
        mortar.charged, mortar.kill_meter = True, CHARGE_KILLS
        shot = mortar.update(2.0, [enemy_beside(mortar)])[0]
        self.assertGreater(shot.stats["splash"], normal)

    def test_a_full_charge_is_announced_with_a_floater_and_a_sound(self):
        game = Game("human")
        rifle = game.place(*next((c, r) for c in range(MAP_COLS) for r in range(MAP_ROWS)
                                 if game.map.is_buildable(c, r) and game.unit_at(c, r) is None), "rapid")
        rifle.kill_meter = CHARGE_KILLS - 1
        target = enemy_beside(rifle, dx=0.0)
        target.hp = 1
        game.projectiles.append(Projectile(rifle.x, rifle.y, "human", "rapid", target, rifle.stats, owner=rifle))
        game._fire_and_hit(0.01)
        self.assertTrue(rifle.charged)
        self.assertIn("CHARGED", [e.text for e in game.effects if isinstance(e, Floater)])
        self.assertIn(("charged",), game.sound_events)

    def test_a_kill_by_a_shot_fills_the_charge(self):
        rifle = Unit("human", "rapid", 1.5, 1.5)
        for _ in range(CHARGE_KILLS):
            _hurt(enemy_beside(rifle), 1e9, rifle)  # Each one is a killing blow
        self.assertTrue(rifle.charged)
        self.assertEqual(rifle.kills, CHARGE_KILLS)

    def test_the_next_shot_is_a_charged_attack_and_spends_the_charge(self):
        rifle = Unit("human", "rapid", 1.5, 1.5)
        target = enemy_beside(rifle)
        normal = rifle.update(1.0, [target])[0]
        self.assertFalse(normal.charged)
        rifle.charged, rifle.kill_meter = True, CHARGE_KILLS
        target.hp = 10_000
        charged = rifle.update(2.0, [target])[0]
        self.assertTrue(charged.charged)
        self.assertAlmostEqual(charged.stats["damage"], normal.stats["damage"] * CHARGE_DAMAGE)
        self.assertFalse(rifle.charged)
        self.assertEqual(rifle.kill_meter, 0)

    def test_a_grenadier_charged_blast_is_wider(self):
        grenadier = Unit("human", "splash", 1.5, 1.5)
        target = enemy_beside(grenadier)
        normal_radius = grenadier.stats["splash"]
        grenadier.charged, grenadier.kill_meter = True, CHARGE_KILLS
        shot = grenadier.update(2.0, [target])[0]
        self.assertGreater(shot.stats["splash"], normal_radius)

    def test_a_charged_shot_impact_flashes_gold(self):
        rifle = Unit("human", "rapid", 1.5, 1.5)
        target = enemy_beside(rifle)
        rifle.charged, rifle.kill_meter = True, CHARGE_KILLS
        shot = rifle.update(2.0, [target])[0]
        effects = []
        shot._impact([target], [], effects)
        gold = [e for e in effects if isinstance(e, Blast) and e.colour == (255, 226, 120)]
        self.assertTrue(gold)


class AttackAnimationTests(unittest.TestCase):
    def test_firing_pushes_the_unit_back_away_from_its_target(self):
        artillery = Unit("human", "artillery", 5.0, 5.0)
        target = enemy_beside(artillery, dx=3.0)
        artillery.update(2.0, [target])
        self.assertGreater(artillery.attack_time, 0)
        self.assertLess(artillery.recoil[0], 0)  # The target is to the right, so the kick is to the left
        self.assertAlmostEqual(artillery.recoil[1], 0.0)

    def test_the_animation_ends(self):
        rifle = Unit("human", "rapid", 1.5, 1.5)
        rifle.update(2.0, [enemy_beside(rifle)])
        rifle.update(1.0, [])
        self.assertEqual(rifle.attack_time, 0.0)


class CombinedShotTests(unittest.TestCase):
    def test_every_combination_has_a_shot_style_its_shots_carry(self):
        for faction, recipes in COMBINATIONS.items():
            for recipe_id, recipe in recipes.items():
                self.assertIn("shot", recipe, recipe_id)
                unit = Unit(faction, recipe["base"], 1, 1, recipe=recipe_id)
                self.assertEqual(unit.stats["shot"], recipe["shot"], recipe_id)

    def test_a_plain_unit_has_no_special_shot(self):
        self.assertIsNone(Unit("human", "rapid", 1, 1).stats["shot"])

    def test_a_cluster_shot_throws_extra_sparks_on_impact(self):
        unit = Unit("human", "rapid", 1.5, 1.5, recipe="breacher")
        target = enemy_beside(unit)
        shot = Projectile(unit.x, unit.y, "human", "rapid", target, unit.stats, owner=unit)
        plain = Projectile(unit.x, unit.y, "human", "rapid", target, Unit("human", "rapid", 1, 1).stats)
        cluster_effects, plain_effects = [], []
        shot._impact([target], [], cluster_effects)
        plain._impact([target], [], plain_effects)
        self.assertGreater(len(cluster_effects), len(plain_effects))


class MoveTests(unittest.TestCase):
    def setUp(self):
        self.game = Game("human")
        self.game.gold = 10_000

    def free_pair(self):
        for col in range(MAP_COLS - 1):
            for row in range(MAP_ROWS):
                if free_buildable(self.game, col, row) and free_buildable(self.game, col + 1, row):
                    return (col, row), (col + 1, row)
        raise AssertionError("no two free tiles")

    def test_a_unit_moves_to_an_empty_tile_between_rounds(self):
        here, there = self.free_pair()
        unit = self.game.place(*here, "rapid")
        self.assertTrue(self.game.move_unit(unit, *there))
        self.assertEqual((int(unit.x), int(unit.y)), there)

    def test_a_unit_cannot_move_onto_another_unit_or_the_route(self):
        here, there = self.free_pair()
        unit = self.game.place(*here, "rapid")
        self.game.place(*there, "rapid")
        self.assertFalse(self.game.move_unit(unit, *there))
        route_cell = next((c, r) for c in range(MAP_COLS) for r in range(MAP_ROWS) if self.game.map.mask[c, r])
        self.assertFalse(self.game.move_unit(unit, *route_cell))
        self.assertEqual((int(unit.x), int(unit.y)), here)

    def test_no_moving_during_a_round(self):
        here, there = self.free_pair()
        unit = self.game.place(*here, "rapid")
        self.game.wave_active = True
        self.assertFalse(self.game.move_unit(unit, *there))
        self.assertIn("during a round", self.game.message)

    def test_undo_puts_the_unit_back(self):
        here, there = self.free_pair()
        unit = self.game.place(*here, "rapid")
        self.game.move_unit(unit, *there)
        self.assertTrue(self.game.undo())
        self.assertEqual((int(unit.x), int(unit.y)), here)

    def test_moving_costs_nothing(self):
        here, there = self.free_pair()
        unit = self.game.place(*here, "rapid")
        gold = self.game.gold
        self.game.move_unit(unit, *there)
        self.assertEqual(self.game.gold, gold)


class SaveTests(unittest.TestCase):
    def test_the_charge_meter_survives_a_save(self):
        game = Game("human")
        unit = game.place(*next((c, r) for c in range(MAP_COLS) for r in range(MAP_ROWS)
                                if free_buildable(game, c, r)), "rapid")
        unit.kill_meter, unit.charged = 7, False
        loaded = run_from_data(run_to_data(game))
        self.assertEqual(loaded.units[0].kill_meter, 7)
        self.assertFalse(loaded.units[0].charged)


if __name__ == "__main__":
    unittest.main()
