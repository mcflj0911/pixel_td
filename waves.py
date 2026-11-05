import random
from collections import Counter

from config import ENEMY_TYPES, WAVE_HP_GROWTH, WAVE_SPEED_GROWTH, BOSS_EVERY, BASIC_PER_ROUND

BOSS = "boss"


def hp_multiplier(wave):
    """Enemy hp multiplier for a wave number (starting at 1). Each wave is tougher than the one before."""
    return 1 + WAVE_HP_GROWTH * (wave - 1)


def speed_multiplier(wave):
    """Enemy speed multiplier for a wave number (starting at 1)."""
    return 1 + WAVE_SPEED_GROWTH * (wave - 1)


def roster(enemy_faction):
    """(ground kinds, flying kinds) for a faction. The boss is in neither list: it is added by build_wave."""
    kinds = ENEMY_TYPES[enemy_faction]
    ground = [k for k, s in kinds.items() if k != BOSS and not s.get("flying")]
    flyers = [k for k, s in kinds.items() if s.get("flying")]
    return ground, flyers


def build_wave(enemy_faction, wave):
    """Spawn schedule for wave number `wave` (starting at 1), as a list of (time, kind), sorted by time.

    Each wave has more basic enemies than the last, fast ones from wave 2, heavy ones from wave 4 and flyers
    from wave 5. Every BOSS_EVERY waves a boss walks in at the end. Spawns come faster as the waves go on.
    """
    ground, flyers = roster(enemy_faction)
    basic, fast, heavy = ground[:3]
    counts = [(basic, 4 + BASIC_PER_ROUND * wave), (fast, max(0, wave - 1)), (heavy, max(0, (wave - 2) // 2))]
    if flyers:
        counts.append((flyers[0], max(0, (wave - 2) // 3)))
    kinds = [kind for kind, n in counts for _ in range(n)]
    random.Random(wave).shuffle(kinds)  # Same order every time for the same wave number
    interval = max(0.5, 1.2 - 0.05 * wave)
    schedule = [(i * interval, kind) for i, kind in enumerate(kinds)]
    if wave % BOSS_EVERY == 0:
        last = schedule[-1][0] if schedule else 0.0
        schedule.append((last + 2 * interval, BOSS))
    return schedule


def preview(enemy_faction, wave):
    """How many of each kind a wave will bring, as a Counter. Used by the HUD before a round starts."""
    return Counter(kind for _, kind in build_wave(enemy_faction, wave))
