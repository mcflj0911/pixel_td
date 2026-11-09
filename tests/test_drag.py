import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # Draw without a real window

import pygame  # noqa: E402

from app import App  # noqa: E402
from config import MAP_COLS, MAP_ROWS  # noqa: E402
from settings import DEFAULTS  # noqa: E402

CELL = 10  # In these tests one tile is 10 pixels, so tile (c, r) is clicked at (c * 10 + 5, r * 10 + 5)


def at(col, row):
    return (col * CELL + CELL // 2, row * CELL + CELL // 2)


class DragTests(unittest.TestCase):
    """Press a unit, drag it to another tile, let go: the app moves it. The window and screen mapping are faked."""

    @classmethod
    def setUpClass(cls):
        pygame.display.init()

    def setUp(self):
        patches = [
            mock.patch("app.load_settings", side_effect=lambda *a, **k: dict(DEFAULTS)),
            mock.patch("app.load_records", return_value={}),
            mock.patch("app.save_settings", return_value=True),
            mock.patch("app.save_records", return_value=True),
            # The pointer position is already in tile-sized units, so the canvas mapping is the identity
            mock.patch("app.to_canvas", side_effect=lambda pos, *a, **k: pos),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.app = App()
        self.app.settings["skip_briefing"] = True
        self.app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h, mod=0, unicode="", scancode=0))
        self.game = self.app.game
        self.game.gold = 10_000
        # Tiles are CELL pixels wide, with no HUD to get in the way
        self.app.camera.screen_to_tile = lambda x, y: (int(x // CELL), int(y // CELL)) \
            if 0 <= x // CELL < MAP_COLS and 0 <= y // CELL < MAP_ROWS else None

    def event(self, kind, pos):
        self.app.handle_event(pygame.event.Event(kind, pos=pos, button=1))

    def free_pair(self):
        for col in range(MAP_COLS - 1):
            for row in range(MAP_ROWS):
                if self.game.map.is_buildable(col, row) and self.game.map.is_buildable(col + 1, row) \
                        and self.game.unit_at(col, row) is None and self.game.unit_at(col + 1, row) is None:
                    return (col, row), (col + 1, row)
        raise AssertionError("no two free tiles")

    def test_a_press_and_drag_moves_the_unit(self):
        here, there = self.free_pair()
        unit = self.game.place(*here, "rapid")
        self.event(pygame.MOUSEBUTTONDOWN, at(*here))
        self.app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=at(*there), rel=(0, 0), buttons=(1, 0, 0)))
        self.assertTrue(self.app._dragging)
        self.assertEqual(self.app._drag_cell, there)
        self.event(pygame.MOUSEBUTTONUP, at(*there))
        self.assertEqual((int(unit.x), int(unit.y)), there)
        self.assertIsNone(self.app._press)

    def test_a_click_without_moving_only_selects(self):
        here, _ = self.free_pair()
        unit = self.game.place(*here, "rapid")
        self.event(pygame.MOUSEBUTTONDOWN, at(*here))
        self.event(pygame.MOUSEBUTTONUP, at(*here))
        self.assertIs(self.game.selected_unit, unit)
        self.assertEqual((int(unit.x), int(unit.y)), here)

    def test_dropping_on_the_route_is_refused_with_a_reason(self):
        here, _ = self.free_pair()
        unit = self.game.place(*here, "rapid")
        route_cell = next((c, r) for c in range(MAP_COLS) for r in range(MAP_ROWS) if self.game.map.mask[c, r])
        self.event(pygame.MOUSEBUTTONDOWN, at(*here))
        self.app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=at(*route_cell), rel=(0, 0), buttons=(1, 0, 0)))
        self.event(pygame.MOUSEBUTTONUP, at(*route_cell))
        self.assertEqual((int(unit.x), int(unit.y)), here)
        self.assertIn("route", self.game.message)

    def test_no_drag_during_a_round(self):
        here, _ = self.free_pair()
        self.game.place(*here, "rapid")
        self.game.wave_active = True
        self.event(pygame.MOUSEBUTTONDOWN, at(*here))
        self.assertIsNone(self.app._press)

    def test_the_drag_ghost_draws_without_error(self):
        here, there = self.free_pair()
        self.game.place(*here, "rapid")
        self.event(pygame.MOUSEBUTTONDOWN, at(*here))
        self.app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=at(*there), rel=(0, 0), buttons=(1, 0, 0)))
        self.app.draw((0, 0))


if __name__ == "__main__":
    unittest.main()
