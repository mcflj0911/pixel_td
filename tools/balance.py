"""Headless balance check. A simple bot plays real games (no window, no sound) and reports how far it gets.

Usage (from the project folder):
    python tools/balance.py                       # 12 games per faction on Normal
    python tools/balance.py --games 30 --difficulty Hard
    python tools/balance.py --faction human --max-round 40

The bot builds with a fixed mix of roles, places them near the route, upgrades them and spends spare gold on
reinforcements. It is a rough player, so treat its numbers as a guide: a good human should beat it by a few rounds.
"""
import argparse
import os
import random
import statistics
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import UNIT_TYPES, REINFORCE_MAX, MAX_UNITS, DIFFICULTIES  # noqa: E402
from game import Game  # noqa: E402

DT = 0.05  # Simulated seconds per step
BUILD_PLAN = ["rapid", "splash", "rapid", "support", "sniper", "flame", "rapid", "artillery"]
AIR_PLAN = ["flak"]  # Added once flyers arrive (round 5 on)
RESERVE = 40  # Gold the bot keeps back for the next placement


def route_cells(game):
    return sorted(game.map.cells)


def best_cell(game, role):
    """The buildable cell within 2 tiles of the route that covers the most route cells for this role's range."""
    route = route_cells(game)
    reach = UNIT_TYPES[game.faction][role]["range"]
    best, best_score = None, -1
    seen = set()
    for rc, rr in route:
        for dc in range(-2, 3):
            for dr in range(-2, 3):
                cell = (rc + dc, rr + dr)
                if cell in seen:
                    continue
                seen.add(cell)
                col, row = cell
                if not game.map.is_buildable(col, row) or game.unit_at(col, row) is not None:
                    continue
                cx, cy = col + 0.5, row + 0.5
                score = sum(1 for c, r in route if (c + 0.5 - cx) ** 2 + (r + 0.5 - cy) ** 2 <= reach ** 2)
                if score > best_score:
                    best, best_score = cell, score
    return best


def combine_round(game):
    """At the unit cap, fuse adjacent pairs that have a recipe, so the freed slots can be built on."""
    if len(game.units) < MAX_UNITS:
        return
    for unit in list(game.units):
        if unit not in game.units:
            continue
        option = game.combine_option(unit)
        if option is None or game.gold < game.combine_cost(unit, option[0]) + RESERVE:
            continue
        game.selected_unit = unit
        game.combine()
    game.selected_unit = None


def build_round(game, rng, combine=True):
    """Spend gold on new units, upgrades and reinforcements. Called between rounds."""
    if combine:
        combine_round(game)
    plan_index = len(game.units)
    flyers = game.wave >= 5
    while len(game.units) < MAX_UNITS:
        options = BUILD_PLAN + (AIR_PLAN if flyers and plan_index % 3 == 2 else [])
        role = options[plan_index % len(options)]
        cost = UNIT_TYPES[game.faction][role]["cost"]
        if game.gold < cost + RESERVE:
            break
        cell = best_cell(game, role)
        if cell is None or game.place(cell[0], cell[1], role) is None:
            break
        plan_index += 1

    # Upgrades: cheapest-to-upgrade units first, keeping a reserve
    for unit in sorted(game.units, key=lambda u: u.spent):
        game.selected_unit = unit
        if unit.level < 3:
            if game.gold >= game.upgrade_cost(unit) + RESERVE:
                game.upgrade()
        elif unit.level == 3:
            if game.gold >= game.upgrade_cost(unit) + RESERVE:
                game.choose_ultimate(rng.choice((0, 1)))
        elif unit.level == 4 and unit.reinforce < REINFORCE_MAX:
            if game.gold >= game.reinforce_cost(unit) + 2 * RESERVE:
                game.reinforce()
    game.selected_unit = None


def play(faction, difficulty, max_round, rng, combine=True):
    game = Game(faction, map_index=0, difficulty=difficulty)
    while game.status == "playing" and game.wave < max_round:
        build_round(game, rng, combine)
        game.start_wave()
        steps = 0
        while game.wave_active and game.status == "playing" and steps < 200000:
            game.update(DT)
            game.drain_sounds()
            steps += 1
        game.drain_sounds()
    return game


def report(label, games):
    rounds = [g.wave for g in games]
    lost = sum(1 for g in games if g.status == "lost")
    print(f"\n{label}: {len(games)} games")
    print(f"  rounds reached   median {statistics.median(rounds):g}   mean {statistics.mean(rounds):.1f}"
          f"   min {min(rounds)}   max {max(rounds)}   lost {lost}/{len(games)}")
    damage = Counter()
    kills = Counter()
    leaks = Counter()
    for g in games:
        for unit in g.all_units:
            damage[unit.kind] += unit.damage
            kills[unit.kind] += unit.kills
        leaks.update(g.leaks)
    total = sum(damage.values()) or 1
    print("  damage share by role: " + ", ".join(f"{k} {v / total:.0%}" for k, v in damage.most_common()))
    print("  kills by role:        " + ", ".join(f"{k} {v}" for k, v in kills.most_common()))
    if leaks:
        print("  enemies that got through: " + ", ".join(f"{k} {v}" for k, v in leaks.most_common(6)))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--games", type=int, default=12, help="games per faction")
    parser.add_argument("--faction", choices=("human", "zombie", "both"), default="both")
    parser.add_argument("--difficulty", choices=tuple(DIFFICULTIES), default="Normal")
    parser.add_argument("--max-round", type=int, default=40, help="stop a game after this many rounds")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--no-combine", action="store_true", help="the bot never combines units")
    args = parser.parse_args()

    factions = ("human", "zombie") if args.faction == "both" else (args.faction,)
    for faction in factions:
        rng = random.Random(args.seed)
        games = [play(faction, args.difficulty, args.max_round, rng, not args.no_combine) for _ in range(args.games)]
        label = f"{faction} vs {'zombie' if faction == 'human' else 'human'} on {args.difficulty}"
        report(label + ("" if args.no_combine else ", combining"), games)


if __name__ == "__main__":
    main()
