import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # Draw without a real window

import pygame  # noqa: E402

from app import App  # noqa: E402
from camera import Camera  # noqa: E402
from config import MAP_COLS, MAP_ROWS, SCREEN_WIDTH, SCREEN_HEIGHT, ULTIMATES  # noqa: E402
from demo import Demo  # noqa: E402
from draw_kit import make_fonts  # noqa: E402
from game import Game  # noqa: E402
from enemies import Enemy  # noqa: E402
from hud import draw_enemy_tip, draw_hud, draw_tooltip  # noqa: E402
from render import draw_scene  # noqa: E402
from screens import draw_briefing, draw_help, draw_log, draw_pause, draw_quit_prompt, draw_title  # noqa: E402
from settings import DEFAULTS  # noqa: E402
from ui import ROLE_RECTS, SELL_RECT, UPGRADE_RECT, ULT_RECTS, ui_action  # noqa: E402
from units import Unit  # noqa: E402
from world import make_map  # noqa: E402
from ui import HELP_TAB_RECTS  # noqa: E402


def center(rect):
    return rect.centerx, rect.centery


def buildable_cell(game):
    for col in range(MAP_COLS):
        for row in range(MAP_ROWS):
            if game.map.is_buildable(col, row):
                return col, row
    raise AssertionError("the map has no buildable cell")


class UiActionTests(unittest.TestCase):
    def setUp(self):
        self.game = Game("human")

    def test_clicking_a_role_slot_selects_that_role(self):
        self.assertEqual(ui_action(center(ROLE_RECTS["sniper"]), self.game), ("role", "sniper"))

    def test_clicking_empty_canvas_does_nothing(self):
        self.assertIsNone(ui_action((5, 5), self.game))

    def test_panel_buttons_need_a_selected_unit(self):
        self.assertIsNone(ui_action(center(SELL_RECT), self.game))

    def test_sell_and_upgrade_buttons_on_a_level_one_unit(self):
        self.game.selected_unit = Unit("human", "rapid", 1.5, 1.5)
        self.assertEqual(ui_action(center(SELL_RECT), self.game), ("sell",))
        self.assertEqual(ui_action(center(UPGRADE_RECT), self.game), ("upgrade",))

    def test_ultimate_buttons_at_level_three(self):
        unit = Unit("human", "rapid", 1.5, 1.5)
        unit.level = 3
        self.game.selected_unit = unit
        self.assertEqual(ui_action(center(ULT_RECTS[0]), self.game), ("ultimate", 0))
        self.assertEqual(ui_action(center(ULT_RECTS[1]), self.game), ("ultimate", 1))

    def test_switch_button_at_level_four_offers_the_other_ultimate(self):
        unit = Unit("human", "rapid", 1.5, 1.5)
        unit.level = 4
        unit.ultimate_index = 0
        self.game.selected_unit = unit
        self.assertEqual(ui_action(center(ULT_RECTS[1]), self.game), ("ultimate", 1))


class RenderingTests(unittest.TestCase):
    """Smoke tests: every screen and overlay draws without error, with real game state on it."""

    @classmethod
    def setUpClass(cls):
        pygame.display.init()  # Not the mixer: the sound tests expect no audio device
        pygame.font.init()
        cls.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        cls.fonts = make_fonts(1.0)

    def test_battle_view_with_a_unit_selected(self):
        game = Game("human")
        col, row = buildable_cell(game)
        unit = game.place(col, row, "rapid")
        game.selected_unit = unit
        scene = draw_scene(Camera(), game, (col, row))
        self.assertIsNotNone(scene)
        draw_hud(self.screen, game, 1.0, self.fonts, (10, 10), "")

    def test_unit_panel_at_each_level(self):
        game = Game("human")
        col, row = buildable_cell(game)
        unit = game.place(col, row, "rapid")
        game.selected_unit = unit
        game.gold = 10_000  # Enough to show every button as affordable
        for level in (2, 3, 4):
            unit.level = level
            if level == 4:
                unit.ultimate_index = 0
                unit.ultimate = ULTIMATES["human"]["rapid"][0]
            draw_hud(self.screen, game, 1.0, self.fonts, (10, 10), "")
        game.wave_active = True  # Switching ultimates is shown as "between rounds" during a round
        draw_hud(self.screen, game, 1.0, self.fonts, (10, 10), "")

    def test_menus_and_overlays(self):
        game = Game("zombie")
        draw_title(self.screen, self.fonts, {"saves": {1: None, 2: 4, 3: None}, "autosave": None,
                                             "best": {"human": 0, "zombie": 3}, "notice": "Hello",
                                             "map": 0, "difficulty": "Normal", "slot": 1, "text_scale": "Normal"})
        draw_briefing(self.screen, self.fonts, "human", skip=True)
        draw_pause(self.screen, self.fonts, game)
        draw_help(self.screen, self.fonts)
        draw_log(self.screen, self.fonts, ["first line", "second line"])
        draw_quit_prompt(self.screen, self.fonts)

    def test_every_help_tab_and_the_unit_and_enemy_tips_draw(self):
        for tab in range(len(HELP_TAB_RECTS)):  # Controls, pairs, trios and quads, units, damage
            draw_help(self.screen, self.fonts, tab)
        game = Game("human")
        draw_tooltip(self.screen, self.fonts, game, "sniper", (200, 200))
        draw_enemy_tip(self.screen, self.fonts, Enemy("zombie", "brute", make_map(0).route), (300, 200))

    def test_demo_battle_runs_and_draws(self):
        demo = Demo(seed=1)
        for _ in range(3):
            demo.update(0.5)
        draw_scene(Camera(), demo.game, None)


class AppTests(unittest.TestCase):
    """Drive the App's event handling directly, without its loop, and without touching the real settings files."""

    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()

    def setUp(self):
        self.write_ok = True
        patches = [
            mock.patch("app.load_settings", side_effect=lambda *a, **k: dict(DEFAULTS)),
            mock.patch("app.load_records", return_value={}),
            mock.patch("app.save_settings", side_effect=lambda *a, **k: self.write_ok),
            mock.patch("app.save_records", side_effect=lambda *a, **k: self.write_ok),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.app = App()

    def press(self, key):
        self.app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))

    def click(self, pos=(400, 300)):
        self.app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))

    def start_run(self, faction_key=pygame.K_h):
        self.app.settings["skip_briefing"] = True
        self.press(faction_key)
        self.assertIsNotNone(self.app.game)

    def test_escape_on_the_title_asks_first_and_n_cancels(self):
        self.press(pygame.K_ESCAPE)
        self.assertEqual(self.app.overlay, "quit")
        self.press(pygame.K_n)
        self.assertIsNone(self.app.overlay)
        self.assertTrue(self.app.running)

    def test_y_at_the_quit_prompt_stops_the_app(self):
        self.press(pygame.K_ESCAPE)
        self.press(pygame.K_y)
        self.assertFalse(self.app.running)

    def test_briefing_then_enter_starts_the_run(self):
        self.press(pygame.K_h)
        self.assertEqual(self.app.briefing, "human")
        self.press(pygame.K_RETURN)
        self.assertIsNone(self.app.briefing)
        self.assertEqual(self.app.game.faction, "human")

    def test_skip_briefing_starts_the_run_at_once(self):
        self.app.settings["skip_briefing"] = True
        self.press(pygame.K_z)
        self.assertEqual(self.app.game.faction, "zombie")

    def test_help_overlay_blocks_clicks_on_the_battle(self):
        self.start_run()
        self.press(pygame.K_F1)
        self.assertEqual(self.app.overlay, "help")
        with mock.patch.object(self.app.game, "click_cell") as click_cell:
            self.click()
        click_cell.assert_not_called()

    def test_pause_stops_the_round_clock(self):
        self.start_run()
        before = self.app.game.countdown
        self.app.paused = True
        self.app.update(1.0)
        self.assertEqual(self.app.game.countdown, before)
        self.app.paused = False
        self.app.update(1.0)
        self.assertLess(self.app.game.countdown, before)

    def test_quit_prompt_keeps_p_from_pausing(self):
        self.start_run()
        self.press(pygame.K_ESCAPE)
        self.press(pygame.K_p)
        self.assertFalse(self.app.paused)

    def test_m_mutes_on_every_screen(self):
        muted = self.app.sounds.muted
        self.press(pygame.K_m)
        self.assertNotEqual(self.app.sounds.muted, muted)

    def test_failed_settings_write_is_shown_on_the_title(self):
        self.write_ok = False
        self.press(pygame.K_d)  # Changes the difficulty and saves the choice
        self.assertEqual(self.app.setup["notice"], "Could not save your settings")

    def test_failed_records_write_is_shown_on_the_title(self):
        self.start_run()
        self.app.game.status = "lost"
        self.app.game.wave = 4
        self.write_ok = False
        self.app._step_battle(0.0)
        self.assertEqual(self.app.setup["notice"], "Could not save the best rounds")

    def test_r_after_a_lost_run_returns_to_the_title(self):
        self.start_run()
        self.app.game.status = "lost"
        self.press(pygame.K_r)
        self.assertIsNone(self.app.game)

    def test_h_opens_the_help_and_pauses_the_battle(self):
        self.start_run()
        before = self.app.game.countdown
        self.press(pygame.K_h)
        self.assertEqual(self.app.overlay, "help")
        self.app.update(5.0)  # Five seconds pass while the help is open...
        self.assertEqual(self.app.game.countdown, before)  # ...and the battle does not move
        self.press(pygame.K_h)
        self.assertIsNone(self.app.overlay)

    def test_help_tabs_change_with_the_arrows_and_clicks(self):
        self.start_run()
        self.press(pygame.K_h)
        self.press(pygame.K_RIGHT)
        self.assertEqual(self.app.help_tab, 1)
        for _ in range(len(HELP_TAB_RECTS) - 1):  # Right through the rest of the tabs...
            self.press(pygame.K_RIGHT)
        self.assertEqual(self.app.help_tab, 0)  # ...and it wraps round
        self.press(pygame.K_LEFT)
        self.assertEqual(self.app.help_tab, len(HELP_TAB_RECTS) - 1)
        self.app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=HELP_TAB_RECTS[1].center, button=1))
        self.assertEqual(self.app.help_tab, 1)

    def test_every_app_screen_draws(self):
        self.app.draw((10, 10))  # Title
        self.app.briefing = "zombie"
        self.app.draw((10, 10))  # Briefing
        self.app.briefing = None
        self.start_run()
        for overlay, paused in ((None, False), ("help", False), ("log", False), (None, True), ("quit", False)):
            self.app.overlay = overlay
            self.app.paused = paused
            self.app.draw((10, 10))


if __name__ == "__main__":
    unittest.main()
