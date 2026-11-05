from pygame import Rect

from config import SCREEN_WIDTH, SCREEN_HEIGHT, ROLES

# Screen rectangles of the clickable HUD. hud.py draws into these, and main.py hit-tests them here
SLOT_W, SLOT_H, SLOT_GAP = 110, 70, 6
HOTBAR_X = 150
HOTBAR_Y = SCREEN_HEIGHT - 92
ROLE_RECTS = {role: Rect(HOTBAR_X + i * (SLOT_W + SLOT_GAP), HOTBAR_Y, SLOT_W, SLOT_H)
              for i, role in enumerate(ROLES)}
PANEL = Rect(SCREEN_WIDTH - 300, 196, 284, 410)
UPGRADE_RECT = Rect(PANEL.x + 12, PANEL.y + 238, PANEL.w - 24, 40)
ULT_RECTS = [Rect(PANEL.x + 12, PANEL.y + 238 + i * 58, PANEL.w - 24, 52) for i in range(2)]
COMBINE_RECT = Rect(PANEL.x + 12, PANEL.y + 362, PANEL.w - 24, 36)  # Below the upgrade and ultimate buttons
SELL_RECT = Rect(PANEL.right - 126, PANEL.y + 8, 116, 24)
TITLE_MAP_RECT = Rect(SCREEN_WIDTH // 2 - 170, 470, 340, 40)  # Title screen: map and difficulty pickers
TITLE_DIFF_RECT = Rect(SCREEN_WIDTH // 2 - 170, 518, 340, 40)
TITLE_SLOT_RECT = Rect(SCREEN_WIDTH // 2 - 170, 566, 340, 40)  # Title screen: which save slot to use
HELP_PANEL = Rect(SCREEN_WIDTH // 2 - 370, 40, 740, 600)  # The help page, opened with H
HELP_TAB_NAMES = ("Controls", "Combinations", "Units")
HELP_TAB_RECTS = [Rect(SCREEN_WIDTH // 2 - 355 + i * 242, 100, 230, 32) for i in range(len(HELP_TAB_NAMES))]


def ui_action(pos, game):
    """What a click on the HUD means: ("role", name), ("upgrade",), ("reinforce",), ("ultimate", index),
    ("sell",), ("combine",), ("panel",), or None."""
    for role, rect in ROLE_RECTS.items():
        if rect.collidepoint(pos):
            return ("role", role)
    unit = game.selected_unit
    if unit is not None and PANEL.collidepoint(pos):
        if SELL_RECT.collidepoint(pos):
            return ("sell",)
        if unit.level < 3 and UPGRADE_RECT.collidepoint(pos):
            return ("upgrade",)
        if unit.level == 4 and UPGRADE_RECT.collidepoint(pos):
            return ("reinforce",)
        if unit.level == 3:
            for i, rect in enumerate(ULT_RECTS):
                if rect.collidepoint(pos):
                    return ("ultimate", i)
        if unit.level == 4 and ULT_RECTS[1].collidepoint(pos):
            return ("ultimate", 1 - unit.ultimate_index)  # The switch button shows the other ultimate
        if unit.level <= 3 and COMBINE_RECT.collidepoint(pos):
            return ("combine",)
        return ("panel",)
    return None
