import random

import numpy as np

from config import MAP_COLS, MAP_ROWS, PATH, DOODAD_DENSITY, DOODAD_WEIGHTS


def in_bounds(col, row):
    return 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS


def cell_corners(col, row):
    return [(col, row), (col + 1, row), (col + 1, row + 1), (col, row + 1)]


def cells_on_path(path):
    cells = set()
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        if ax == bx:
            for y in range(min(ay, by), max(ay, by) + 1):
                cells.add((ax, y))
        else:
            for x in range(min(ax, bx), max(ax, bx) + 1):
                cells.add((x, ay))
    return cells


def _neighbours(col, row):
    return [(col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)]


def _run_is_clear(cells, start, run):
    """A new run of route cells is fine if it stays on the map, avoids the route, and does not touch it
    anywhere except at its start. Touching would make the route look like one blob."""
    for cell in run:
        if not in_bounds(*cell) or cell in cells:
            return False
        for n in _neighbours(*cell):
            if n in cells and n != start:
                return False
    return True


def _try_random_path(rng):
    """One attempt at a route: left edge to right edge, alternating straight runs. None if it got stuck."""
    y = rng.randrange(1, MAP_ROWS - 1)
    path = [(0, y)]
    cells = {(0, y)}
    x = 0
    horizontal = True
    for _ in range(40):
        if horizontal:
            nx = min(MAP_COLS - 1, x + rng.randint(3, 7))
            run = [(i, y) for i in range(x + 1, nx + 1)]
        else:
            ny = min(MAP_ROWS - 1, max(0, y + rng.randint(2, 4) * rng.choice((-1, 1))))
            if ny == y:
                return None
            step = 1 if ny > y else -1
            run = [(x, j) for j in range(y + step, ny + step, step)]
        if not run or not _run_is_clear(cells, (x, y), run):
            return None
        cells.update(run)
        x, y = run[-1]
        path.append((x, y))
        if horizontal and x == MAP_COLS - 1:
            return path
        horizontal = not horizontal
    return None


def generate_path(seed, attempts=300):
    rng = random.Random(seed)
    for _ in range(attempts):
        path = _try_random_path(rng)
        if path:
            return path
    return list(PATH)  # Should not happen, but always have a route


def _place_doodads(index, route_cells):
    """Scatter props over the map. Returns a list of (x, y, kind) in tile coordinates."""
    rng = random.Random(2000 + index)
    near_route = set()
    for c, r in route_cells:
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                near_route.add((c + dc, r + dr))
    kinds = [kind for kind, weight in DOODAD_WEIGHTS for _ in range(weight)]
    doodads = []
    for c in range(MAP_COLS):
        for r in range(MAP_ROWS):
            if (c, r) in near_route or rng.random() >= DOODAD_DENSITY:
                continue
            x = c + rng.uniform(0.25, 0.75)
            y = r + rng.uniform(0.25, 0.75)
            doodads.append((x, y, rng.choice(kinds)))
    return doodads


class Map:
    """One battlefield: a route, the cells it covers, the doodads on it, and the floor's brightness variation."""

    def __init__(self, index, path):
        self.index = index
        self.path = path
        self.cells = cells_on_path(path)
        # Enemy route in tile coordinates, through the centre of each corner cell
        self.route = [(c + 0.5, r + 0.5) for c, r in path]
        self.start = self.route[0]  # Where enemies enter
        self.end = self.route[-1]  # Where enemies leave
        self.doodads = _place_doodads(index, self.cells)
        self.doodad_cells = {(int(x), int(y)) for x, y, _ in self.doodads}
        self.mask = np.zeros((MAP_COLS, MAP_ROWS), dtype=bool)  # Indexed [col, row]
        for c, r in self.cells:
            self.mask[c, r] = True
        rng = random.Random(1000 + index)
        self.variation = np.array([[0.95 + 0.09 * rng.random() for _ in range(MAP_ROWS)]
                                   for _ in range(MAP_COLS)])

    def is_buildable(self, col, row):
        return (in_bounds(col, row) and (col, row) not in self.cells
                and (col, row) not in self.doodad_cells)


def make_map(index):
    """Map 0 is the classic route. Every other index gives a fixed random route for that index."""
    path = list(PATH) if index == 0 else generate_path(index * 7919 + 17)
    return Map(index, path)
