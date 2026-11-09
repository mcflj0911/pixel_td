# Units, upgrades, ultimates, enemies and the colours of shots. All combat numbers live here.

# --- UNIT ROLES ---
# Each faction has eight roles. The first three are the basics, and the rest were added later:
#   rapid    : mid fire rate, mid range, cheap
#   sniper   : long range, slow fire rate, pierces at level 4
#   splash   : short range, area damage, expensive
#   support  : short range weak shots, and an aura that makes units nearby fire faster
#   flame    : very short range, very fast, sets the ground on fire
#   artillery: very long range, slow, huge blasts that arc over the map
#   flak     : anti-air only. Shoots flyers and ignores ground enemies
#   rocket   : slow homing missiles. Each one bursts and leaves a lingering cloud on the ground
ROLES = ("rapid", "sniper", "splash", "support", "flame", "artillery", "flak", "rocket")
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
            "name": "Rifleman", "short": "RIFLE", "dtype": "bullet", "cost": 50,
            "rate": 1.0, "range": 4.5, "damage": 10,
            "splash": 0.0, "splash_damage": 0,
            "shot_speed": 10, "height": 1.2,
        },
        "sniper": {
            "name": "Marksman", "short": "SNIPER", "dtype": "pierce", "cost": 90,
            "rate": 0.4, "range": 9.0, "damage": 40,
            "splash": 0.0, "splash_damage": 0,
            "shot_speed": 16, "height": 1.3,
        },
        "splash": {
            "name": "Grenadier", "short": "GRENADE", "dtype": "explosion", "cost": 160,
            "rate": 0.6, "range": 3.0, "damage": 14,
            "splash": 1.5, "splash_damage": 14,
            "shot_speed": 6, "height": 1.0,
        },
        "support": {
            "name": "Medic", "short": "MEDIC", "dtype": "bullet", "cost": 70,
            "rate": 0.8, "range": 2.0, "damage": 3,
            "splash": 0.0, "splash_damage": 0,
            "aura": (2.5, 1.3), "aura_damage": 1.15,
            "shot_speed": 10, "height": 1.2,
        },
        "flame": {
            "name": "Flamethrower", "short": "FLAME", "dtype": "burn", "cost": 110,
            "rate": 4.0, "range": 2.2, "damage": 3,
            "splash": 0.0, "splash_damage": 0,
            "burn": (6.0, 1.5, 0.8),
            "shot_speed": 14, "height": 1.1,
        },
        "artillery": {
            "name": "Mortar", "short": "MORTAR", "dtype": "explosion", "cost": 220,
            "rate": 0.3, "range": 7.5, "damage": 30,
            "splash": 2.2, "splash_damage": 20,
            "shot_speed": 7, "height": 1.4,
        },
        "flak": {
            "name": "Flak Gunner", "short": "FLAK", "dtype": "flak", "cost": 120,
            "rate": 1.2, "range": 5.0, "damage": 22,
            "splash": 0.0, "splash_damage": 0,
            "air_only": True,
            "shot_speed": 14, "height": 1.3,
        },
        "rocket": {
            "name": "Rocketeer", "short": "ROCKET", "dtype": "explosion", "cost": 190,
            "rate": 0.5, "range": 6.5, "damage": 16,
            "splash": 1.0, "splash_damage": 8,
            "burn": (5.0, 4.0, 1.1),
            "shot_speed": 7, "height": 1.3,
        },
    },
    "zombie": {
        "rapid": {
            "name": "Spitter", "short": "SPIT", "dtype": "bullet", "cost": 50,
            "rate": 1.0, "range": 4.5, "damage": 10,
            "splash": 0.0, "splash_damage": 0,
            "shot_speed": 10, "height": 1.2,
        },
        "sniper": {
            "name": "Lobber", "short": "LOBBER", "dtype": "pierce", "cost": 90,
            "rate": 0.4, "range": 9.0, "damage": 40,
            "splash": 0.0, "splash_damage": 0,
            "shot_speed": 16, "height": 1.3,
        },
        "splash": {
            "name": "Bloater", "short": "BLOAT", "dtype": "explosion", "cost": 160,
            "rate": 0.6, "range": 3.0, "damage": 14,
            "splash": 1.5, "splash_damage": 14,
            "shot_speed": 6, "height": 1.0,
        },
        "support": {
            "name": "Shaman", "short": "SHAMAN", "dtype": "bullet", "cost": 70,
            "rate": 0.8, "range": 2.0, "damage": 3,
            "splash": 0.0, "splash_damage": 0,
            "aura": (2.5, 1.3), "aura_damage": 1.15,
            "shot_speed": 10, "height": 1.2,
        },
        "flame": {
            "name": "Bile Spewer", "short": "BILE", "dtype": "burn", "cost": 110,
            "rate": 4.0, "range": 2.2, "damage": 3,
            "splash": 0.0, "splash_damage": 0,
            "burn": (6.0, 1.5, 0.8),
            "shot_speed": 14, "height": 1.1,
        },
        "artillery": {
            "name": "Spore Mortar", "short": "SPORE", "dtype": "explosion", "cost": 220,
            "rate": 0.3, "range": 7.5, "damage": 30,
            "splash": 2.2, "splash_damage": 20,
            "shot_speed": 7, "height": 1.4,
        },
        "flak": {
            "name": "Spore Caster", "short": "CASTER", "dtype": "flak", "cost": 120,
            "rate": 1.2, "range": 5.0, "damage": 22,
            "splash": 0.0, "splash_damage": 0,
            "air_only": True,
            "shot_speed": 14, "height": 1.3,
        },
        "rocket": {
            "name": "Spore Colony", "short": "COLONY", "dtype": "explosion", "cost": 190,
            "rate": 0.5, "range": 6.5, "damage": 16,
            "splash": 1.0, "splash_damage": 8,
            "burn": (5.0, 4.0, 1.1),
            "shot_speed": 7, "height": 1.3,
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
        "rocket": [
            {"name": "Barrage Missiles", "desc": "Fires 1.8x as fast, cloud lingers 7 s", "mods": {"rate": 1.8, "burn": (5.0, 7.0, 1.1)}},
            {"name": "Thermobaric", "desc": "Bigger, hotter cloud that lingers 6 s", "mods": {"splash": 1.6, "splash_damage": 1.8, "burn": (8.0, 6.0, 1.8)}},
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
        "rocket": [
            {"name": "Spore Volley", "desc": "Fires 1.8x as fast, cloud lingers 7 s", "mods": {"rate": 1.8, "burn": (5.0, 7.0, 1.1)}},
            {"name": "Bloom", "desc": "Bigger, thicker cloud that lingers 6 s", "mods": {"splash": 1.6, "splash_damage": 1.8, "burn": (8.0, 6.0, 1.8)}},
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
    "rocket": "Slow missiles that leave a lingering, harmful cloud.",
}

# --- COMBINATIONS ---
# Combine a unit with the units next to it (press C with it selected) and they become one unit of the recipe's type.
# Each recipe names the roles it joins (two for a pair, three for a trio, four for the ultimate combination, which
# needs three units around it), the role the new unit fights as (`base`), and its mods. The mods use the same keys
# as ULTIMATES, plus:
#   blast: (radius, damage) of a splash blast set outright, for a unit that has no splash of its own
# `form` is the add-ons drawn on the new unit (see sprites.py), and `scale` makes it taller on the map. Humans get
# mechanical parts and a bit of height; zombies get mutations and a lot more.
# Only units at level 3 or below can combine, and a combined unit cannot combine again. The biggest recipe is tried
# first: a quad, then a trio, then a pair.
COMBINATIONS = {
    "human": {
        "breacher": {"name": "Breacher", "roles": ("rapid", "splash"), "base": "rapid", "shot": "cluster",
                     "desc": "Rifle shots burst in a small blast", "mods": {"blast": (1.2, 12), "rate": 0.9},
                     "form": ("shield", "rocket_pods"), "scale": 1.05},
        "sentinel": {"name": "Sentinel", "roles": ("rapid", "flak"), "base": "rapid", "shot": "twin",
                     "desc": "Longer reach and harder hits", "mods": {"range": 1.5, "damage": 1.3},
                     "form": ("antenna", "scanner"), "scale": 1.05},
        "overwatch": {"name": "Overwatch", "roles": ("sniper", "support"), "base": "sniper", "shot": "beam",
                      "desc": "Aura reaches 3 tiles, shots pierce 2", "mods": {"aura": (3.0, 1.25), "pierce": 2},
                      "form": ("turret_head", "antenna"), "scale": 1.05},
        "siege_gun": {"name": "Siege Gun", "roles": ("sniper", "artillery"), "base": "artillery", "shot": "heavy",
                      "desc": "Reaches 2.5 tiles further, wider and harder blast",
                      "mods": {"range": 2.5, "damage": 1.3, "blast": (2.4, 26)},
                      "form": ("turret_head", "exhaust"), "scale": 1.05},
        "flame_medic": {"name": "Flame Medic", "roles": ("support", "flame"), "base": "flame", "shot": "ember",
                        "desc": "Aura reaches 2 tiles, +30% fire rate, +20% damage",
                        "mods": {"aura": (2.0, 1.3), "damage": 1.2},
                        "form": ("jetpack", "exhaust"), "scale": 1.05},
        "napalm_crew": {"name": "Napalm Crew", "roles": ("splash", "flame"), "base": "splash", "shot": "ember",
                        "desc": "Blasts leave fire behind for 3 s", "mods": {"burn": (8, 3.0, 1.2), "rate": 1.1},
                        "form": ("armour", "exhaust"), "scale": 1.05},
        "iron_walker": {"name": "Iron Walker", "roles": ("rapid", "support", "splash"), "base": "rapid", "shot": "twin",
                        "desc": "Armoured walker: faster, aura, blasts on hit",
                        "mods": {"rate": 1.2, "aura": (2.5, 1.2), "blast": (1.0, 9)},
                        "form": ("treads", "shield", "twin_cannon"), "scale": 1.2},
        "sky_battery": {"name": "Sky Battery", "roles": ("flak", "sniper", "artillery"), "base": "sniper", "shot": "beam",
                        "desc": "Hits flyers and ground, longer reach, blasts",
                        "mods": {"range": 2.0, "rate": 2.0, "blast": (2.2, 18)},
                        "form": ("turret_head", "rocket_pods", "antenna"), "scale": 1.2},
        "command_tank": {"name": "Command Tank", "roles": ("support", "flame", "sniper"), "base": "flame", "shot": "heavy",
                         "desc": "Aura to 3 tiles, +35% fire rate, bigger fire",
                         "mods": {"aura": (3.0, 1.35), "damage": 1.4, "burn": (9, 3.0, 1.2)},
                         "form": ("treads", "armour", "scanner"), "scale": 1.2},
        "bombardier": {"name": "Bombardier", "roles": ("rocket", "artillery"), "base": "artillery", "shot": "heavy",
                       "desc": "Faster fire, and clouds that burn longer",
                       "mods": {"rate": 1.2, "burn": (7.0, 4.0, 1.3)},
                       "form": ("rocket_pods", "exhaust"), "scale": 1.05},
        "incendiary": {"name": "Incendiary Pods", "roles": ("rocket", "flame"), "base": "flame", "shot": "ember",
                       "desc": "Flames reach 2 tiles further and leave fire for 4 s",
                       "mods": {"range": 2.0, "burn": (8.0, 4.0, 1.2)},
                       "form": ("rocket_pods", "jetpack"), "scale": 1.05},
        "stalker": {"name": "Stalker", "roles": ("sniper", "rocket"), "base": "sniper", "shot": "beam",
                    "desc": "Heavy shots, a small blast, and one more pierce",
                    "mods": {"damage": 1.2, "blast": (1.4, 14), "pierce": 1},
                    "form": ("scanner", "rocket_pods"), "scale": 1.05},
        "shock_squad": {"name": "Shock Squad", "roles": ("rapid", "flame", "splash"), "base": "splash", "shot": "cluster",
                        "desc": "Blasts set the ground alight, rifles fire faster",
                        "mods": {"burn": (7.0, 3.0, 1.0), "rate": 1.15},
                        "form": ("shield", "exhaust", "armour"), "scale": 1.2},
        "rocket_battery": {"name": "Rocket Battery", "roles": ("rocket", "artillery", "sniper"), "base": "artillery", "shot": "cluster",
                           "desc": "Long reach, heavy blasts, and clouds that linger",
                           "mods": {"range": 2.0, "blast": (2.0, 20), "burn": (6.0, 4.0, 1.3)},
                           "form": ("rocket_pods", "turret_head", "exhaust"), "scale": 1.2},
        "field_launcher": {"name": "Field Launcher", "roles": ("rapid", "support", "rocket"), "base": "rocket", "shot": "twin",
                           "desc": "Aura to 2.5 tiles, fires faster, clouds linger 6 s",
                           "mods": {"aura": (2.5, 1.2), "rate": 1.2, "burn": (6.0, 6.0, 1.1)},
                           "form": ("shield", "rocket_pods", "antenna"), "scale": 1.2},
        # The ultimate combination: four roles in one unit. It needs three units around it (a plus shape)
        "bastion": {"name": "Bastion", "roles": ("rapid", "sniper", "splash", "support"), "base": "splash", "shot": "barrage",
                    "desc": "Aura 3.5 tiles, faster fire, bigger blasts",
                    "mods": {"aura": (3.5, 1.3), "rate": 1.2, "blast": (1.8, 22), "pierce": 2},
                    "form": ("turret_head", "rocket_pods", "shield", "antenna"), "scale": 1.35},
    },
    "zombie": {
        "gutbuster": {"name": "Gutbuster", "roles": ("rapid", "splash"), "base": "rapid", "shot": "cluster",
                      "desc": "Spit bursts in a small blast", "mods": {"blast": (1.2, 12), "rate": 0.9},
                      "form": ("bloat", "spikes"), "scale": 1.15},
        "rot_sentinel": {"name": "Rot Sentinel", "roles": ("rapid", "flak"), "base": "rapid", "shot": "twin",
                         "desc": "Longer reach and harder hits", "mods": {"range": 1.5, "damage": 1.3},
                         "form": ("tendril", "eye"), "scale": 1.15},
        "death_shroud": {"name": "Death Shroud", "roles": ("sniper", "support"), "base": "sniper", "shot": "beam",
                         "desc": "Aura reaches 3 tiles, shots pierce 2", "mods": {"aura": (3.0, 1.25), "pierce": 2},
                         "form": ("horns", "tendril"), "scale": 1.15},
        "bloat_siege": {"name": "Bloat Siege", "roles": ("sniper", "artillery"), "base": "artillery", "shot": "heavy",
                        "desc": "Reaches 2.5 tiles further, wider and harder blast",
                        "mods": {"range": 2.5, "damage": 1.3, "blast": (2.4, 26)},
                        "form": ("bloat", "extra_arm"), "scale": 1.15},
        "bile_shaman": {"name": "Bile Shaman", "roles": ("support", "flame"), "base": "flame", "shot": "ember",
                        "desc": "Aura reaches 2 tiles, +30% fire rate, +20% damage",
                        "mods": {"aura": (2.0, 1.3), "damage": 1.2},
                        "form": ("maw", "tumor"), "scale": 1.15},
        "toxic_crew": {"name": "Toxic Crew", "roles": ("splash", "flame"), "base": "splash", "shot": "ember",
                       "desc": "Blasts leave poison behind for 3 s", "mods": {"burn": (8, 3.0, 1.2), "rate": 1.1},
                       "form": ("spikes", "tumor"), "scale": 1.15},
        "abomination": {"name": "Abomination", "roles": ("rapid", "support", "splash"), "base": "rapid", "shot": "twin",
                        "desc": "Swollen with growths: faster, aura, blasts",
                        "mods": {"rate": 1.2, "aura": (2.5, 1.2), "blast": (1.0, 9)},
                        "form": ("bloat", "spikes", "extra_arm"), "scale": 1.4},
        "spore_tower": {"name": "Spore Tower", "roles": ("flak", "sniper", "artillery"), "base": "sniper", "shot": "beam",
                        "desc": "Hits flyers and ground, longer reach, blasts",
                        "mods": {"range": 2.0, "rate": 2.0, "blast": (2.2, 18)},
                        "form": ("tendril", "maw", "spikes"), "scale": 1.4},
        "plague_engine": {"name": "Plague Engine", "roles": ("support", "flame", "sniper"), "base": "flame", "shot": "heavy",
                          "desc": "Aura to 3 tiles, +35% fire rate, bigger fire",
                          "mods": {"aura": (3.0, 1.35), "damage": 1.4, "burn": (9, 3.0, 1.2)},
                          "form": ("tumor", "horns", "bloat"), "scale": 1.4},
        "spore_bombardier": {"name": "Spore Bombardier", "roles": ("rocket", "artillery"), "base": "artillery", "shot": "heavy",
                             "desc": "Faster fire, and acid that lingers longer",
                             "mods": {"rate": 1.2, "burn": (7.0, 4.0, 1.3)},
                             "form": ("bloat", "extra_arm"), "scale": 1.15},
        "bile_launcher": {"name": "Bile Launcher", "roles": ("rocket", "flame"), "base": "flame", "shot": "ember",
                          "desc": "Acid reaches 2 tiles further and stays for 4 s",
                          "mods": {"range": 2.0, "burn": (8.0, 4.0, 1.2)},
                          "form": ("tumor", "spikes"), "scale": 1.15},
        "venom_spine": {"name": "Venom Spine", "roles": ("sniper", "rocket"), "base": "sniper", "shot": "beam",
                        "desc": "Heavy spines, a small burst, one more pierce",
                        "mods": {"damage": 1.2, "blast": (1.4, 14), "pierce": 1},
                        "form": ("tendril", "spikes"), "scale": 1.15},
        "toxic_bloom": {"name": "Toxic Bloom", "roles": ("rapid", "flame", "splash"), "base": "splash", "shot": "cluster",
                        "desc": "Bursts leave acid, and the spit fires faster",
                        "mods": {"burn": (7.0, 3.0, 1.0), "rate": 1.15},
                        "form": ("bloat", "maw", "tendril"), "scale": 1.3},
        "rocket_hive": {"name": "Rocket Hive", "roles": ("rocket", "artillery", "sniper"), "base": "artillery", "shot": "cluster",
                        "desc": "Long reach, heavy bursts, and acid that lingers",
                        "mods": {"range": 2.0, "blast": (2.0, 20), "burn": (6.0, 4.0, 1.3)},
                        "form": ("tendril", "bloat", "spikes"), "scale": 1.3},
        "spore_crier": {"name": "Spore Crier", "roles": ("rapid", "support", "rocket"), "base": "rocket", "shot": "twin",
                        "desc": "Aura to 2.5 tiles, fires faster, clouds linger 6 s",
                        "mods": {"aura": (2.5, 1.2), "rate": 1.2, "burn": (6.0, 6.0, 1.1)},
                        "form": ("tumor", "horns", "tendril"), "scale": 1.3},
        # The ultimate combination: four roles in one unit. It needs three units around it (a plus shape)
        "hive_colossus": {"name": "Hive Colossus", "roles": ("rapid", "sniper", "splash", "support"), "base": "splash", "shot": "barrage",
                          "desc": "Aura 3.5 tiles, faster fire, bigger bursts",
                          "mods": {"aura": (3.5, 1.3), "rate": 1.2, "blast": (1.8, 22), "pierce": 2},
                          "form": ("bloat", "spikes", "extra_arm", "horns"), "scale": 1.5},
    },
}

# Colours of projectiles, and of the puff left where one lands
SHOT_COLOURS = {
    "human": {"rapid": (255, 226, 120), "sniper": (200, 240, 255), "splash": (255, 140, 60),
              "support": (255, 255, 255), "flame": (255, 120, 40), "artillery": (255, 200, 90),
              "flak": (120, 230, 255), "rocket": (240, 240, 235)},
    "zombie": {"rapid": (190, 255, 90), "sniper": (230, 140, 255), "splash": (130, 255, 170),
               "support": (150, 255, 200), "flame": (150, 255, 60), "artillery": (120, 255, 150),
               "flak": (255, 150, 230), "rocket": (200, 90, 255)},
}
IMPACT_COLOURS = {"human": (255, 226, 120), "zombie": (190, 255, 90)}

# --- ENEMIES ---
# Keys are in the order basic, fast, heavy. build_wave() in waves.py relies on that order.
# speed = tiles per second, reward = gold on kill, leak = lives lost if it reaches the end of the route,
# height = how tall it looks, in tiles
# vs = damage multiplier per damage type (see DAMAGE_TYPES). Above 1 is a weakness, below 1 a resistance. Missing = 1.
# Armour still applies on top of it.
ENEMY_TYPES = {
    "zombie": {
        "walker": {"name": "Walker", "hp": 60, "speed": 1.2, "reward": 5, "leak": 1, "height": 1.1,
                   "vs": {"burn": 1.5}},
        "runner": {"name": "Runner", "hp": 35, "speed": 2.2, "reward": 6, "leak": 1, "height": 1.0,
                   "vs": {"pierce": 1.3, "explosion": 0.8}},
        "brute": {"name": "Brute", "hp": 220, "speed": 0.7, "reward": 18, "leak": 2, "height": 1.5, "armour": 0.25,
                  "vs": {"pierce": 1.5, "bullet": 0.8}},
        "crow": {"name": "Crow", "hp": 30, "speed": 2.4, "reward": 6, "leak": 1, "height": 0.9, "flying": True,
                 "vs": {"flak": 1.6, "bullet": 0.9}},
        "boss": {"name": "Giant", "hp": 1500, "speed": 0.5, "reward": 120, "leak": 5, "height": 2.2, "armour": 0.15,
                 "vs": {"pierce": 1.2, "explosion": 0.8, "burn": 0.7}},
    },
    "human": {
        "militia": {"name": "Militia", "hp": 60, "speed": 1.2, "reward": 5, "leak": 1, "height": 1.1},
        "scout": {"name": "Scout", "hp": 35, "speed": 2.2, "reward": 6, "leak": 1, "height": 1.0,
                  "vs": {"pierce": 1.3, "explosion": 0.8}},
        "heavy": {"name": "Heavy", "hp": 220, "speed": 0.7, "reward": 18, "leak": 2, "height": 1.5, "armour": 0.25,
                  "vs": {"pierce": 1.5, "bullet": 0.8}},
        "drone": {"name": "Drone", "hp": 40, "speed": 2.2, "reward": 7, "leak": 1, "height": 0.9, "flying": True,
                  "vs": {"flak": 1.6, "bullet": 0.9}},
        "boss": {"name": "Colonel", "hp": 1500, "speed": 0.5, "reward": 120, "leak": 5, "height": 2.2, "armour": 0.15,
                 "vs": {"pierce": 1.2, "explosion": 0.8}},
    },
}

# --- DAMAGE TYPES ---
# Every shot has one type, set by its role (`dtype` in UNIT_TYPES). Blasts always deal explosion damage, and fire or
# acid left on the ground always deals burn damage, whatever the shot that made them. The type decides how much each
# enemy takes (`vs` in ENEMY_TYPES). The help page's Damage tab is built from these tables.
DAMAGE_TYPES = ("bullet", "pierce", "explosion", "burn", "flak")
DAMAGE_NAMES = {"bullet": "Bullet", "pierce": "Armour-piercing", "explosion": "Explosion", "burn": "Burn", "flak": "Flak"}
DAMAGE_NOTES = {"burn": "fire for humans, acid for zombies"}  # Shown after the name on the help page
# Floating damage numbers: a weakness hit is orange, a resisted hit is grey
WEAK_HIT_COLOUR = (255, 150, 60)
RESIST_HIT_COLOUR = (150, 160, 178)

# --- CHARGED ATTACKS AND ATTACK ANIMATIONS ---
# Every role charges, and so does every combination. Each CHARGE_KILLS kills fill the charge, and the next shot is then a
# charged attack: CHARGE_DAMAGE times the damage, CHARGE_PIERCE more enemies pierced. A charged grenade or shell blasts
# CHARGE_BLAST times wider, and a charged flame or rocket leaves CHARGE_BURN times the fire or acid. The meter stays
# full until that shot is fired.
CHARGE_ROLES = ROLES
CHARGE_KILLS = 10
CHARGE_DAMAGE = 3.0
CHARGE_PIERCE = 2
CHARGE_BLAST = 1.6
CHARGE_BURN = 2.0
CHARGE_COLOUR = (255, 226, 120)  # The gold of a charged shot and its impact
# How far a sprite is pushed back when it fires, in tiles, and how long the recoil lasts. Each role kicks differently
ATTACK_RECOIL = {"rapid": 0.06, "sniper": 0.14, "splash": 0.12, "support": 0.03, "flame": 0.04,
                 "artillery": 0.2, "flak": 0.08, "rocket": 0.1}
ATTACK_ANIM_SECONDS = 0.16
# A defender that is moved hops to its new tile over this long. An enemy that dies falls over for this long
MOVE_SECONDS = 0.4
DEATH_SECONDS = 0.6
# The name of each combined shot style, for the help page
SHOT_NAMES = {"twin": "Twin tracers", "beam": "Beam", "heavy": "Heavy round", "cluster": "Cluster",
              "ember": "Embers", "barrage": "Barrage"}
