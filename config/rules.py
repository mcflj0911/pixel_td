# Economy, round pacing, limits, saves and difficulty.

# --- GAME RULES ---
START_GOLD = 150
START_LIVES = 20
SELL_REFUND = 0.6  # Selling a unit returns this share of everything put into it, upgrades included
WAVE_BONUS = 25  # Gold for clearing a round
MAP_EVERY = 10  # Every this many rounds the route is redrawn at random. The waves never stop
MAP_BUILD_SECONDS = 60.0  # After a map change, this long to rebuild the units the new route removed. Real seconds: game speed and SPACE cannot shorten it
SPEEDS = (1, 2, 3, 4)  # Game speed multipliers, cycled with F
BASIC_PER_ROUND = 1  # Basic enemies added per round (was 2: round 11 was out of reach for the bot)
UNDO_STEPS = 5  # How many builds and sales Ctrl+Z can take back, between rounds
STORY_LOG_LINES = 12  # Story lines kept for the story log (L)

# Rounds get harder without end. Enemy hp and speed grow by these amounts per round after the first
SPAWN_RUSH = 4.0  # Space during a round speeds up the spawn queue by this much (press again to slow it)
WAVE_HP_GROWTH = 0.35  # Set from tools/balance.py. The bot's losses come from the round 11 swarm size, not hp
WAVE_SPEED_GROWTH = 0.03

# --- LIMITS, FLYING AND BOSSES ---
MAX_UNITS = 24  # Hard cap on placed units. Combining two units into one frees a slot
# The cap grows late in a run, so surplus gold has a use: from round CAP_BONUS_FROM, every CAP_BONUS_EVERY rounds
# add CAP_BONUS_STEP units, up to CAP_BONUS_MAX more
CAP_BONUS_FROM = 12
CAP_BONUS_EVERY = 3
CAP_BONUS_STEP = 2
CAP_BONUS_MAX = 8
AIR_ROLES = ("rapid", "sniper", "flak")  # Only these can shoot flying enemies
FLY_HEIGHT = 1.6  # How high flying enemies hover, in tiles
BOSS_EVERY = 5  # A boss joins the end of every this many rounds
SELL_CONFIRM_SECONDS = 3.0  # Time to click SELL a second time to confirm
VOLUME_STEP = 0.1
SAVE_FILE = "savegame_{}.json"  # One file per save slot
SAVE_SLOTS = 3
REINFORCE_BONUS = 0.15  # Each reinforcement adds this much damage to an ultimate unit
REINFORCE_MAX = 5  # Reinforcements per unit
REINFORCE_COST = 0.5  # Fraction of the unit's base cost, before the round scaling below
REINFORCE_GROWTH = 0.08  # Extra cost per round, so reinforcing late in the game is a real choice
DIFFICULTIES = {  # Enemy hp, kill reward and combine price multipliers
    "Easy": {"hp": 0.8, "reward": 1.2, "combine": 0.7},
    "Normal": {"hp": 1.0, "reward": 1.0, "combine": 1.0},
    "Hard": {"hp": 1.25, "reward": 0.9, "combine": 1.5},
}
COMBINE_COST = 0.5  # Combining costs this share of the two units' base prices, before the difficulty multiplier
WAVE_BONUS_GROWTH = 3  # Extra clear bonus per round, so late rounds pay for the bigger armies
AUTO_START_SECONDS = 10.0  # Countdown before the next round starts by itself. SPACE starts it sooner
COMBO_RADIUS = 2.5  # Units of the same type this close together form a combo group
COMBO_TIERS = ((2, 1.15), (3, 1.3), (4, 1.5), (5, 1.7), (6, 1.9))  # (units in the group, damage multiplier) from that size on
MIXED_SQUAD_BONUS = 0.1  # Extra damage per different unit type standing within the combo radius
MIXED_SQUAD_MAX = 3  # At most this many types count for the mixed squad bonus
RESPEC_COST = 0.5  # Switching a level 4 unit to its other ultimate costs this share of the unit cost
# Map pickups: dropped on the route during a round. Click the tile to collect
PICKUP_EVERY = 9.0  # Seconds between pickup drops while a round runs
PICKUP_LIFE = 10.0  # Seconds a pickup stays on the route before it fades
PICKUP_GOLD = 40  # Gold from a gold pickup
RAGE_SECONDS = 8.0  # How long a rage pickup speeds up every unit
RAGE_FIRE = 1.5  # Fire rate multiplier from rage
FREEZE_SECONDS = 4.0  # How long a freeze pickup slows every ground enemy
FREEZE_FACTOR = 0.4  # Speed multiplier for slowed enemies (0.4 is 40 percent speed)
