"""Map pickups. During a round a pickup drops on the route. Click its tile to collect it, or it fades away."""
from config import PICKUP_LIFE

KINDS = ("gold", "rage", "freeze")
LABELS = {"gold": "G", "rage": "R", "freeze": "F"}  # Letters as well as colour, so the kinds read without colour
COLOURS = {"gold": (255, 210, 60), "rage": (255, 96, 70), "freeze": (120, 200, 255)}


class Pickup:
    def __init__(self, col, row, kind):
        self.col = col
        self.row = row
        self.kind = kind
        self.life = PICKUP_LIFE

    @property
    def x(self):
        return self.col + 0.5

    @property
    def y(self):
        return self.row + 0.5

    def update(self, dt):
        """Count down. Returns False once it has faded."""
        self.life -= dt
        return self.life > 0
