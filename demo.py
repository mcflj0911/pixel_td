import random

from config import ROLES, MAP_COLS, MAP_ROWS
from game import Game

_SPOT_CACHE = {}


def _spots(game_map):
    """Buildable cells within two tiles of the route: where a sensible player would build."""
    if game_map.index not in _SPOT_CACHE:
        spots = []
        for c in range(MAP_COLS):
            for r in range(MAP_ROWS):
                if game_map.is_buildable(c, r) and any(abs(c - pc) + abs(r - pr) <= 2
                                                       for pc, pr in game_map.cells):
                    spots.append((c, r))
        _SPOT_CACHE[game_map.index] = spots
    return _SPOT_CACHE[game_map.index]


class Demo:
    """A self-playing battle shown behind the title screen. It builds, upgrades and runs rounds by itself."""

    GAME_LENGTH = 45.0  # Seconds before the demo starts a fresh battle
    SPEED = 2  # The demo runs at double speed

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.games = 0
        self.game = None
        self._new_game()

    def _new_game(self):
        faction = ("human", "zombie")[self.games % 2]  # Alternate sides so both get shown
        self.games += 1
        self.game = Game(faction, map_index=self.rng.randrange(6))
        self.game.gold = 10 ** 6  # Demo money: it always has something to build
        self.clock = 0.0
        self.next_build = 0.4
        self.next_round = 0.8

    def update(self, dt):
        g = self.game
        self.clock += dt
        if g.status != "playing" or self.clock > self.GAME_LENGTH:
            self._new_game()
            return
        if self.clock >= self.next_round and not g.wave_active:
            g.start_wave()
            self.next_round = self.clock + 3.0
        if self.clock >= self.next_build:
            self.next_build = self.clock + 0.5
            if len(g.units) < 18:
                self._build_one()
            elif g.units and self.rng.random() < 0.4:
                self._upgrade_one()
        g.update(dt * self.SPEED)

    def _build_one(self):
        g = self.game
        free = [c for c in _spots(g.map) if g.unit_at(*c) is None]
        if free:
            col, row = self.rng.choice(free)
            g.place(col, row, self.rng.choice(ROLES))

    def _upgrade_one(self):
        g = self.game
        unit = self.rng.choice(g.units)
        g.selected_unit = unit
        if unit.level < 3:
            g.upgrade()
        elif unit.level == 3:
            g.choose_ultimate(self.rng.randrange(2))
        g.selected_unit = None
