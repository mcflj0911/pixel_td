"""Colours and drawing helpers shared by the HUD and the full-screen menus."""
import pygame

from config import SCREEN_WIDTH, SCREEN_HEIGHT

HUD_BG = (14, 16, 20)
HUD_EDGE = (70, 74, 84)
ACCENT = (255, 196, 40)
WHITE = (240, 240, 240)
GREY = (150, 155, 165)
RED = (222, 60, 60)
GREEN = (110, 214, 110)
DIM = (60, 62, 70)
BUTTON = (40, 44, 52)
SLANT = 12

_shades = {}  # Alpha -> full-screen surface, so menus do not allocate a new one every frame


def make_fonts(scale=1.0):
    """The UI fonts. `scale` comes from the text size setting."""
    return {
        "big": pygame.font.SysFont(None, round(60 * scale)),
        "mid": pygame.font.SysFont(None, round(30 * scale)),
        "small": pygame.font.SysFont(None, round(22 * scale)),
        "tiny": pygame.font.SysFont(None, round(20 * scale)),
    }


def draw_text(screen, font, text, pos, colour=WHITE, anchor="topleft"):
    surf = font.render(str(text), True, colour)
    rect = surf.get_rect(**{anchor: pos})
    screen.blit(surf, rect)
    return rect


def draw_panel(screen, rect, fill=HUD_BG, accent=False, slant=SLANT):
    x, y, w, h = rect
    pts = [(x + slant, y), (x + w, y), (x + w - slant, y + h), (x, y + h)]
    pygame.draw.polygon(screen, fill, pts)
    pygame.draw.lines(screen, HUD_EDGE, True, pts, 1)
    if accent:
        pygame.draw.rect(screen, ACCENT, (x + slant, y, w - 2 * slant, 3))


def dim_colour(colour, amount):
    return tuple(int(c * amount) for c in colour)


def shade(screen, alpha=170):
    """Darken the whole screen. `alpha` runs from 0 (nothing) to 255 (black)."""
    if alpha not in _shades:
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        surf.fill((0, 0, 0, alpha))
        _shades[alpha] = surf
    screen.blit(_shades[alpha], (0, 0))
