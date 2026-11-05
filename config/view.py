# Window, camera, map and scenery settings. Positions are in tiles, colours are RGB.

# --- WINDOW AND VIEW ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 720
RENDER_W, RENDER_H = 500, 360  # The 3D view is drawn at half size and scaled up: faster, and it gives the pixel look
FPS = 60
CAM_POS = (8.0, 19.0, 12.0)  # Camera x, y and height above the floor, in tiles: south of the map, looking north
CAM_TARGET = (8.0, 5.0, 0.0)  # The point the camera looks at
CAM_FOV = 66  # Horizontal field of view, in degrees. Smaller means more zoomed in
SKY = (150, 190, 225)
FOG_COLOUR = (170, 200, 220)
FOG_START, FOG_END = 14, 30  # Distance from the camera where the fog starts and is fully thick, in tiles

# --- MAP ---
MAP_COLS, MAP_ROWS = 16, 12
# The first map is fixed. Every later map is generated from its index (see world.py)
PATH = [(0, 2), (12, 2), (12, 6), (3, 6), (3, 9), (15, 9)]
# Floor colours: grass, grass alternate, path, path alternate, outside the map
TILE_COLOURS = [(78, 128, 66), (70, 118, 60), (160, 134, 90), (148, 122, 80), (52, 60, 48)]

# --- DOODADS AND ROUTE MARKERS ---
# Decorative props scattered over the map. They block building but enemies walk past them.
# They are never placed next to the route, so there is always room to build beside it.
DOODAD_DENSITY = 0.20  # Chance that an eligible cell gets a doodad
DOODAD_WEIGHTS = (("tree", 5), ("rock", 3), ("bush", 2), ("flower", 3), ("stump", 2), ("dead_tree", 2), ("ruin", 1))
DOODAD_HEIGHT = {"tree": 1.8, "rock": 0.6, "bush": 0.7, "flower": 0.4, "stump": 0.4, "dead_tree": 1.6, "ruin": 0.9}  # How tall each one looks, in tiles
START_COLOUR = (110, 230, 120)  # Where enemies enter the map
END_COLOUR = (240, 90, 70)  # Where enemies leave the map (and cost you lives)
