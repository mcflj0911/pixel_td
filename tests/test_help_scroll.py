import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # Draw without a real window

import pygame  # noqa: E402

from settings import DEFAULTS  # noqa: E402
from ui import HELP_PANEL, HELP_SCROLL_STEP, HELP_TAB_NAMES, HELP_TAB_RECTS, HELP_VIEW  # noqa: E402
import screens  # noqa: E402
from screens import HELP_DRAWERS, HELP_LAYER_H, draw_help  # noqa: E402

UPGRADES = 4  # The Upgrades tab: the one long enough to scroll


class HelpLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()

    def setUp(self):
        self.screen = pygame.Surface((1000, 720))
        from draw_kit import make_fonts
        self.fonts = make_fonts()

    def test_six_tabs_fit_across_the_panel(self):
        self.assertEqual(len(HELP_TAB_NAMES), 6)
        self.assertEqual(len(HELP_TAB_RECTS), 6)
        self.assertLessEqual(HELP_TAB_RECTS[-1].right, HELP_PANEL.right - 20)
        for name, rect in zip(HELP_TAB_NAMES, HELP_TAB_RECTS):
            self.assertLessEqual(self.fonts["small"].size(name)[0], rect.w - 6, name)

    def test_the_view_sits_inside_the_panel_below_the_tabs(self):
        self.assertGreater(HELP_VIEW.y, HELP_TAB_RECTS[0].bottom)
        self.assertLess(HELP_VIEW.bottom, HELP_PANEL.bottom)
        self.assertTrue(HELP_PANEL.contains(HELP_VIEW))

    def test_every_tab_draws_at_the_top_and_at_its_end(self):
        for tab in range(len(HELP_DRAWERS)):
            top = draw_help(self.screen, self.fonts, tab, 0)
            end = draw_help(self.screen, self.fonts, tab, 10_000)  # Clamped to the most it can scroll
            self.assertGreaterEqual(top, 0, tab)
            self.assertGreaterEqual(end, 0, tab)

    def test_the_upgrades_tab_is_long_enough_to_scroll(self):
        self.assertGreater(draw_help(self.screen, self.fonts, UPGRADES, 0), 0)

    def test_the_layer_grows_to_hold_a_tall_tab(self):
        from screens import _help_upgrades
        bottom = _help_upgrades(pygame.Surface((1000, HELP_LAYER_H)), self.fonts, 500)
        self.assertGreater(bottom, HELP_LAYER_H)  # Taller than the starting layer, so the page must grow
        draw_help(self.screen, self.fonts, UPGRADES, 0)
        self.assertGreaterEqual(screens._help_layer.get_height(), bottom + 16)

    def test_a_short_tab_does_not_scroll(self):
        self.assertEqual(draw_help(self.screen, self.fonts, 0, 0), 0)  # Controls fits in the view


class HelpScrollInputTests(unittest.TestCase):
    """The help page scrolls with the mouse wheel and the keys, and stops at the top and the end."""

    @classmethod
    def setUpClass(cls):
        pygame.display.init()

    def setUp(self):
        patches = [
            mock.patch("app.load_settings", side_effect=lambda *a, **k: dict(DEFAULTS)),
            mock.patch("app.load_records", return_value={}),
            mock.patch("app.save_settings", return_value=True),
            mock.patch("app.save_records", return_value=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        from app import App
        self.app = App()
        self.app.settings["skip_briefing"] = True
        self.key(pygame.K_h)  # On the title, H starts a run as the humans...
        self.key(pygame.K_h)  # ...and in the battle, H opens the help
        self.assertEqual(self.app.overlay, "help")
        self.app.help_tab = UPGRADES
        self.app.draw((0, 0))  # Drawing the page is what tells the app how far it can scroll
        self.assertGreater(self.app.help_max, 0)

    def key(self, key):
        self.app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))

    def test_the_wheel_scrolls_down_and_up(self):
        self.app.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1))
        self.assertEqual(self.app.help_scroll, HELP_SCROLL_STEP)
        self.app.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1))
        self.assertEqual(self.app.help_scroll, 0)

    def test_the_arrow_keys_scroll(self):
        self.key(pygame.K_DOWN)
        self.assertEqual(self.app.help_scroll, HELP_SCROLL_STEP)
        self.key(pygame.K_UP)
        self.assertEqual(self.app.help_scroll, 0)

    def test_scrolling_stops_at_the_top_and_the_end(self):
        self.key(pygame.K_UP)
        self.assertEqual(self.app.help_scroll, 0)
        for _ in range(500):
            self.key(pygame.K_DOWN)
        self.assertEqual(self.app.help_scroll, self.app.help_max)
        self.app.draw((0, 0))
        self.assertEqual(self.app.help_scroll, self.app.help_max)

    def test_page_down_moves_about_a_page(self):
        self.key(pygame.K_PAGEDOWN)
        self.assertEqual(self.app.help_scroll, min(self.app.help_max, HELP_VIEW.h - HELP_SCROLL_STEP))

    def test_changing_tab_goes_back_to_the_top(self):
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RIGHT)
        self.assertEqual(self.app.help_scroll, 0)

    def test_the_end_is_clamped_again_when_the_page_gets_shorter(self):
        self.key(pygame.K_DOWN)
        self.app.help_tab = 0  # A shorter tab: the page is redrawn, and the old scroll must not stick
        self.app.draw((0, 0))
        self.assertEqual(self.app.help_scroll, 0)


if __name__ == "__main__":
    unittest.main()
