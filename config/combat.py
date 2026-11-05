# Units, upgrades, ultimates, enemies and the colours of shots. All combat numbers live here.

# --- UNIT ROLES ---
# Each faction has six roles. The first three are the basics, and the last three were added later:
#   rapid    : mid fire rate, mid range, cheap
#   sniper   : long range, slow fire rate, pierces at level 4
#   splash   : short range, area damage, expensive
#   support  : short range weak shots, and an aura that makes units nearby fire faster
#   flame    : very short range, very fast, sets the ground on fire
#   artillery: very long range, slow, huge blasts that arc over the map
#   flak     : anti-air only. Shoots flyers and ignores ground enemies
ROLES = ("rapid", "sniper", "splash", "support", "flame", "artillery", "flak")
#
# rate          = shots per second
# range         = targeting radius in tiles
# damage        = damage to the main target
# splash        = radius in tiles around the main target that also takes splash_damage (0 = single target)
# splash_damage = damage each other enemy in the splash radius takes
# burn          = (damage per second, seconds, radius) of fire left on the ground where a shot lands
# aura          = (radius, fire rate multiplier): units inside the radius fire this much faster
# shot_speed    = how fast the projectile flies, in tiles per second
# height        = how tall the unit looks, in tiles
# short         = the label on the hotbar
# air_only     = True: this unit only shoots flying enemies
# aura_damage   = (support units) damage multiplier the aura gives to units inside it, on top of the fire rate

FACTIONS = ("human", "zombie")
# The faction that the player's wave enemies come from
OPPONENT = {"human": "zombie", "zombie": "human"}

UNIT_TYPES = {
    "human": {
        "rapid": {
            "name": "Rifleman", "short": "RIFLE", "cost": 50,
            "rate": 1.0, "range": 4.5, "damage": 10,
            "splash": 0.0, "splash_damage": 0,
            "shot_speed": 10, "height": 1.2,
        },
        "sniper": {
            "name": "Marksman", "short": "SNIPER", "cost": 90,
            "rate": 0.4, "range": 9.0, "damage": 40,
            "splash": 0.0, "splash_damage": 0,
            "shot_speed": 16, "height": 1.3,
        },
        "splash": {
            "name": "Grenadier", "short": "GRENADE", "cost": 160,
            "rate": 0.6, "range": 3.0, "damage": 14,
            "splash": 1.5, "splash_damage": 14,
            "shot_speed": 6, "height": 1.0,
        },
        "support": {
            "name": "Medic", "short": "MEDIC", "cost": 70,
            "rate": 0.8, "range": 2.0, "damage": 3,
            "splash": 0.0, "splash_damage": 0,
            "aura": (2.5, 1.3), "aura_damage": 1.15,
            "shot_speed": 10, "height": 1.2,
        },
        "flame": {
            "name": "Flamethrower", "short": "FLAME", "cost": 110,
            "rate": 4.0, "range": 2.2, "damage": 3,
            "splash": 0.0, "splash_damage": 0,
            "burn": (6.0, 1.5, 0.8),
            "shot_speed": 14, "height": 1.1,
        },
        "artillery": {
            "name": "Mortar", "short": "MORTAR", "cost": 220,
            "rate": 0.3, "range": 7.5, "damage": 30,
            "splash": 2.2, "splash_damage": 20,
            "shot_speed": 7, "height": 1.4,
        },
        "flak": {
            "name": "Flak Gunner", "short": "FLAK", "cost": 120,
            "rate": 1.2, "range": 5.0, "damage": 22,
            "splash": 0.0, "splash_damage": 0,
            "air_only": True,
            "shot_speed": 14, "height": 1.3,
        },
    },
    "zombie": {
        "rapid": {
            "name": "Spitter", "short": "SPIT", "cost": 50,
            "rate": 1.0, "range": 4.5, "damage": 10,
            "splash": 0.0, "splash_damage": 0,
            "shot_speed": 10, "height": 1.2,
        },
        "sniper": {
            "name": "Lobber", "short": "LOBBER", "cost": 90,
            "rate": 0.4, "range": 9.0, "damage": 40,
            "splash": 0.0, "splash_damage": 0,
            "shot_speed": 16, "height": 1.3,
        },
        "splash": {
            "name": "Bloater", "short": "BLOAT", "cost": 160,
            "rate": 0.6, "range": 3.0, "damage": 14,
            "splash": 1.5, "splash_damage": 14,
            "shot_speed": 6, "height": 1.0,
        },
        "support": {
            "name": "Shaman", "short": "SHAMAN", "cost": 70,
            "rate": 0.8, "range": 2.0, "damage": 3,
            "splash": 0.0, "splash_damage": 0,
            "aura": (2.5, 1.3), "aura_damage": 1.15,
            "shot_speed": 10, "height": 1.2,
        },
        "flame": {
            "name": "Bile Spewer", "short": "BILE", "cost": 110,
            "rate": 4.0, "range": 2.2, "damage": 3,
            "splash": 0.0, "splash_damage": 0,
            "burn": (6.0, 1.5, 0.8),
            "shot_speed": 14, "height": 1.1,
        },
        "artillery": {
            "name": "Spore Mortar", "short": "SPORE", "cost": 220,
            "rate": 0.3, "range": 7.5, "damage": 30,
            "splash": 2.2, "splash_damage": 20,
            "shot_speed": 7, "height": 1.4,
        },
        "flak": {
            "name": "Spore Caster", "short": "CASTER", "cost": 120,
            "rate": 1.2, "range": 5.0, "damage": 22,
            "splash": 0.0, "splash_damage": 0,
            "air_only": True,
            "shot_speed": 14, "height": 1.3,
        },
    },
}

# --- UPGRADES ---
# Each unit goes from level 1 to level 4 in three upgrades. Levels 2 and 3 use these multipliers per level gained.
UPGRADE_DAMAGE = 1.4
UPGRADE_RATE = 1.1
UPGRADE_RANGE = 0.5  # Tiles of range added per level gained
# Cost of each upgrade as a multiple of the unit's cost: to level 2, to level 3, and to level 4 (the ultimate)
UPGRADE_COST = (0.6, 0.9, 1.4)

# At level 4 the player picks one of two ultimate forms. The mods are applied on top of the level stats:
#   rate, damage, splash, splash_damage: multiply the stat
#   range: add to the stat
#   pierce: extra enemies a shot can carry on through after its first hit
#   slow:   (speed factor, seconds) applied to what the shot hits
#   burn:   (damage per second, seconds, radius) of fire left where the shot lands
#   aura:   (radius, fire rate multiplier) for support units
ULTIMATES = {
    "human": {
        "rapid": [
            {"name": "Gatling Squad", "desc": "Fires twice as fast, hits softer", "mods": {"rate": 2.0, "damage": 0.8}},
            {"name": "Piercing Volley", "desc": "Shots carry on through 3 enemies", "mods": {"pierce": 3, "damage": 1.2, "range": 1.0}},
        ],
        "sniper": [
            {"name": "Railgun", "desc": "Huge shots that pierce 5 enemies", "mods": {"damage": 2.5, "pierce": 5, "rate": 0.8}},
            {"name": "Hunter's Mark", "desc": "Slows what it hits by half for 3 s", "mods": {"damage": 1.3, "slow": (0.5, 3.0)}},
        ],
        "splash": [
            {"name": "Cluster Bomb", "desc": "Bigger blast, much harder hits", "mods": {"splash": 1.5, "splash_damage": 1.6}},
            {"name": "Napalm", "desc": "Leaves fire that burns for 4 s", "mods": {"splash": 1.1, "burn": (10, 4.0, 1.4)}},
        ],
        "support": [
            {"name": "Battle Drums", "desc": "Aura reaches 4 tiles, +25% fire rate", "mods": {"aura": (4.0, 1.25)}},
            {"name": "Field Surgeon", "desc": "+60% fire rate and double damage", "mods": {"aura": (2.5, 1.6), "damage": 2.0}},
        ],
        "flame": [
            {"name": "Inferno", "desc": "Hotter fire, burns 3 s, fires faster", "mods": {"burn": (14, 3.0, 1.3), "rate": 1.2}},
            {"name": "Pyre Lance", "desc": "Flames pierce 3 enemies, reach +1.5", "mods": {"pierce": 3, "range": 1.5, "damage": 2.0}},
        ],
        "artillery": [
            {"name": "Barrage", "desc": "Fires 1.8x as fast, bigger blasts", "mods": {"rate": 1.8, "splash_damage": 1.2}},
            {"name": "Siege Shell", "desc": "Much wider blast, much harder hits", "mods": {"splash": 1.4, "splash_damage": 2.0, "damage": 1.5}},
        ],
        "flak": [
            {"name": "Flak Storm", "desc": "Fires twice as fast, hits softer", "mods": {"rate": 2.0, "damage": 0.8}},
            {"name": "Tracker", "desc": "Long reach and faster aim, hits harder", "mods": {"range": 2.0, "rate": 1.3, "damage": 1.2}},
        ],
    },
    "zombie": {
        "rapid": [
            {"name": "Spit Storm", "desc": "Fires twice as fast, hits softer", "mods": {"rate": 2.0, "damage": 0.8}},
            {"name": "Bone Shards", "desc": "Shots carry on through 3 enemies", "mods": {"pierce": 3, "damage": 1.2, "range": 1.0}},
        ],
        "sniper": [
            {"name": "Spore Cannon", "desc": "Huge shots that pierce 5 enemies", "mods": {"damage": 2.5, "pierce": 5, "rate": 0.8}},
            {"name": "Rot Mark", "desc": "Slows what it hits by half for 3 s", "mods": {"damage": 1.3, "slow": (0.5, 3.0)}},
        ],
        "splash": [
            {"name": "Bloat Burst", "desc": "Bigger blast, much harder hits", "mods": {"splash": 1.5, "splash_damage": 1.6}},
            {"name": "Toxic Pool", "desc": "Leaves poison that burns for 4 s", "mods": {"splash": 1.1, "burn": (10, 4.0, 1.4)}},
        ],
        "support": [
            {"name": "Frenzy Chant", "desc": "Aura reaches 4 tiles, +25% fire rate", "mods": {"aura": (4.0, 1.25)}},
            {"name": "Rot Bond", "desc": "+60% fire rate and double damage", "mods": {"aura": (2.5, 1.6), "damage": 2.0}},
        ],
        "flame": [
            {"name": "Acid Torrent", "desc": "Hotter acid, burns 3 s, fires faster", "mods": {"burn": (14, 3.0, 1.3), "rate": 1.2}},
            {"name": "Venom Lash", "desc": "Lashes pierce 3 enemies, reach +1.5", "mods": {"pierce": 3, "range": 1.5, "damage": 2.0}},
        ],
        "artillery": [
            {"name": "Spore Barrage", "desc": "Fires 1.8x as fast, bigger blasts", "mods": {"rate": 1.8, "splash_damage": 1.2}},
            {"name": "Pod Bomb", "desc": "Much wider blast, much harder hits", "mods": {"splash": 1.4, "splash_damage": 2.0, "damage": 1.5}},
        ],
        "flak": [
            {"name": "Spore Storm", "desc": "Fires twice as fast, hits softer", "mods": {"rate": 2.0, "damage": 0.8}},
            {"name": "Seeker Spores", "desc": "Long reach and faster aim, hits harder", "mods": {"range": 2.0, "rate": 1.3, "damage": 1.2}},
        ],
    },
}

# What each role does, for the help page. Shared by both factions: the names and costs come from UNIT_TYPES
ROLE_DESCRIPTIONS = {
    "rapid": "Steady fire at short to medium range. A good all-rounder, and it can shoot flyers.",
    "sniper": "Long range, slow, heavy single shots. Its ultimates pierce through enemies.",
    "splash": "Short range. Area blasts that hit a group of enemies at once.",
    "support": "Weak shots, but an aura that makes the units around it fire faster.",
    "flame": "Very short range and very fast. Sets the ground on fire.",
    "artillery": "Very long range and slow. Huge blasts that arc over the map.",
    "flak": "Anti-air only. Shoots flyers and ignores ground enemies.",
}

# --- COMBINATIONS ---
# Combine two adjacent units (press C with one selected) and they become one unit of the recipe's type. Two units become
# one, so combining frees a slot under the unit cap. Each recipe names the two roles it joins, the role the new unit
# fights as (`base`), and its mods. The mods use the same keys as ULTIMATES, plus:
#   blast: (radius, damage) of a splash blast set outright, for a unit that has no splash of its own
# Only units at level 3 or below can combine, and a combined unit cannot combine again.
COMBINATIONS = {
    "human": {
        "breacher": {"name": "Breacher", "roles": ("rapid", "splash"), "base": "rapid",
                     "desc": "Rifle shots burst in a small blast", "mods": {"blast": (1.2, 12), "rate": 0.9}},
        "sentinel": {"name": "Sentinel", "roles": ("rapid", "flak"), "base": "rapid",
                     "desc": "Longer reach and harder hits", "mods": {"range": 1.5, "damage": 1.3}},
        "overwatch": {"name": "Overwatch", "roles": ("sniper", "support"), "base": "sniper",
                      "desc": "Aura reaches 3 tiles, shots pierce 2", "mods": {"aura": (3.0, 1.25), "pierce": 2}},
        "siege_gun": {"name": "Siege Gun", "roles": ("sniper", "artillery"), "base": "artillery",
                      "desc": "Reaches 2.5 tiles further, wider and harder blast",
                      "mods": {"range": 2.5, "damage": 1.3, "blast": (2.4, 26)}},
        "flame_medic": {"name": "Flame Medic", "roles": ("support", "flame"), "base": "flame",
                        "desc": "Aura reaches 2 tiles, +30% fire rate, +20% damage",
                        "mods": {"aura": (2.0, 1.3), "damage": 1.2}},
        "napalm_crew": {"name": "Napalm Crew", "roles": ("splash", "flame"), "base": "splash",
                        "desc": "Blasts leave fire behind for 3 s", "mods": {"burn": (8, 3.0, 1.2), "rate": 1.1}},
    },
    "zombie": {
        "gutbuster": {"name": "Gutbuster", "roles": ("rapid", "splash"), "base": "rapid",
                      "desc": "Spit bursts in a small blast", "mods": {"blast": (1.2, 12), "rate": 0.9}},
        "rot_sentinel": {"name": "Rot Sentinel", "roles": ("rapid", "flak"), "base": "rapid",
                         "desc": "Longer reach and harder hits", "mods": {"range": 1.5, "damage": 1.3}},
        "death_shroud": {"name": "Death Shroud", "roles": ("sniper", "support"), "base": "sniper",
                         "desc": "Aura reaches 3 tiles, shots pierce 2", "mods": {"aura": (3.0, 1.25), "pierce": 2}},
        "bloat_siege": {"name": "Bloat Siege", "roles": ("sniper", "artillery"), "base": "artillery",
                        "desc": "Reaches 2.5 tiles further, wider and harder blast",
                        "mods": {"range": 2.5, "damage": 1.3, "blast": (2.4, 26)}},
        "bile_shaman": {"name": "Bile Shaman", "roles": ("support", "flame"), "base": "flame",
                        "desc": "Aura reaches 2 tiles, +30% fire rate, +20% damage",
                        "mods": {"aura": (2.0, 1.3), "damage": 1.2}},
        "toxic_crew": {"name": "Toxic Crew", "roles": ("splash", "flame"), "base": "splash",
                       "desc": "Blasts leave poison behind for 3 s", "mods": {"burn": (8, 3.0, 1.2), "rate": 1.1}},
    },
}

# Colours of projectiles, and of the puff left where one lands
SHOT_COLOURS = {
    "human": {"rapid": (255, 226, 120), "sniper": (200, 240, 255), "splash": (255, 140, 60),
              "support": (255, 255, 255), "flame": (255, 120, 40), "artillery": (255, 200, 90),
              "flak": (120, 230, 255)},
    "zombie": {"rapid": (190, 255, 90), "sniper": (230, 140, 255), "splash": (130, 255, 170),
               "support": (150, 255, 200), "flame": (150, 255, 60), "artillery": (120, 255, 150),
               "flak": (255, 150, 230)},
}
IMPACT_COLOURS = {"human": (255, 226, 120), "zombie": (190, 255, 90)}

# --- ENEMIES ---
# Keys are in the order basic, fast, heavy. build_wave() in waves.py relies on that order.
# speed = tiles per second, reward = gold on kill, leak = lives lost if it reaches the end of the route,
# height = how tall it looks, in tiles
ENEMY_TYPES = {
    "zombie": {
        "walker": {"name": "Walker", "hp": 60, "speed": 1.2, "reward": 5, "leak": 1, "height": 1.1},
        "runner": {"name": "Runner", "hp": 35, "speed": 2.2, "reward": 6, "leak": 1, "height": 1.0},
        "brute": {"name": "Brute", "hp": 220, "speed": 0.7, "reward": 18, "leak": 2, "height": 1.5, "armour": 0.25},
        "crow": {"name": "Crow", "hp": 30, "speed": 2.4, "reward": 6, "leak": 1, "height": 0.9, "flying": True},
        "boss": {"name": "Giant", "hp": 1500, "speed": 0.5, "reward": 120, "leak": 5, "height": 2.2, "armour": 0.15},
    },
    "human": {
        "militia": {"name": "Militia", "hp": 60, "speed": 1.2, "reward": 5, "leak": 1, "height": 1.1},
        "scout": {"name": "Scout", "hp": 35, "speed": 2.2, "reward": 6, "leak": 1, "height": 1.0},
        "heavy": {"name": "Heavy", "hp": 220, "speed": 0.7, "reward": 18, "leak": 2, "height": 1.5, "armour": 0.25},
        "drone": {"name": "Drone", "hp": 40, "speed": 2.2, "reward": 7, "leak": 1, "height": 0.9, "flying": True},
        "boss": {"name": "Colonel", "hp": 1500, "speed": 0.5, "reward": 120, "leak": 5, "height": 2.2, "armour": 0.15},
    },
}
