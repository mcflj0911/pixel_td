"""Undo for the build phase: the last placements and sales, which can be taken back between rounds.

The history only remembers entries. Undoing one changes the game, so `BuildHistory.undo` takes the game as an argument.
"""
from config import UNDO_STEPS


class BuildHistory:
    def __init__(self):
        self._entries = []  # Placements and sales this build phase, newest last

    def record(self, entry):
        """Remember a ("place", unit), ("sell", unit, index), ("combine", fused, [(index, member), ...]) or
        ("move", unit, (x, y)) entry.
        Only the last UNDO_STEPS are kept."""
        self._entries.append(entry)
        del self._entries[:-UNDO_STEPS]

    def clear(self):
        """Rounds lock in the build, so nothing can be undone after one starts."""
        self._entries = []

    def undo(self, game):
        """Take back the most recent placement or sale on `game`. Only between rounds. Sets game.message and
        returns True if something was undone."""
        if game.wave_active:
            game.message = "Can't undo during a round"
            return False
        while self._entries:
            entry = self._entries.pop()
            if entry[0] == "place":
                unit = entry[1]
                if unit not in game.units:
                    continue  # Already sold or removed: look at the one before it
                game.units.remove(unit)
                game.all_units.remove(unit)
                if game.selected_unit is unit:
                    game.selected_unit = None
                refund = unit.spent
                game.gold += refund
                game.message = f"Undid placement, refunded {refund}"
                return True
            if entry[0] == "move":
                _, unit, (x, y) = entry
                if unit not in game.units:
                    continue  # Sold since: look at the one before it
                unit.x, unit.y = x, y
                game.message = "Move undone"
                return True
            if entry[0] == "combine":
                _, fused, originals = entry
                if fused not in game.units:
                    continue  # Already sold: look at the one before it
                # The refund is what was put into the result after its members: the fee, and any upgrades since
                refund = fused.spent - sum(member.spent for _, member in originals)
                game.units.remove(fused)
                game.all_units.remove(fused)
                if game.selected_unit is fused:
                    game.selected_unit = None
                for position, member in sorted(originals, key=lambda item: item[0]):
                    game.units.insert(min(position, len(game.units)), member)
                game.gold += refund
                game.message = f"Combine undone, refunded {refund}"
                return True
            _, unit, index = entry
            refund = game.sell_refund(unit)
            if game.gold < refund:
                self._entries.append(entry)  # Keep the sale, so it can be undone once there is gold
                game.message = f"Need {refund} gold to undo the sale"
                return False
            game.gold -= refund
            game.units.insert(min(index, len(game.units)), unit)
            game.message = "Sale undone"
            return True
        game.message = "Nothing to undo"
        return False
