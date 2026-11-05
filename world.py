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


# A route is a serpentine: LANES straight runs across the whole map, joined at alternating ends. An odd number of lanes
# means the route starts at the left edge and ends at the right one, where the start and end markers sit.
LANES = 5


def serpentine(rows):
    """Waypoints of a route that crosses the map along each row in `rows`, joined at alternating ends."""
    waypoints = []
    for k, row in enumerate(rows):
        left, right = 0, MAP_COLS - 1
        if k % 2:
            left, right = right, left
        waypoints += [(left, row), (right, row)]
    return waypoints


def generate_path(seed):
    """A serpentine route for this seed. The lanes are 2 or 3 rows apart at random, so the maps differ, but every
    lane is full width, so the route covers about half the map: the tiles between two lanes are the building ground."""
    rng = random.Random(seed)
    while True:
        rows = [rng.choice((0, 1))]
        for _ in range(LANES - 1):
            rows.append(rows[-1] + rng.choice((2, 3)))
        if rows[-1] <= MAP_ROWS - 1:
            return serpentine(rows)


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
