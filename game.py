import math
import random
from collections import Counter

from config import (MAP_BUILD_SECONDS, START_GOLD, START_LIVES, WAVE_BONUS, WAVE_BONUS_GROWTH, MAP_EVERY, UNIT_TYPES, ULTIMATES,
                    COMBINE_COST,
                    UPGRADE_COST, OPPONENT, SELL_REFUND, MAX_UNITS, SELL_CONFIRM_SECONDS, DIFFICULTIES,
                    ENEMY_TYPES, AUTO_START_SECONDS, SPAWN_RUSH, COMBO_RADIUS, REINFORCE_MAX, REINFORCE_COST, REINFORCE_GROWTH,
                    RESPEC_COST, PICKUP_EVERY, PICKUP_GOLD, RAGE_SECONDS, RAGE_FIRE, FREEZE_SECONDS,
                    FREEZE_FACTOR)
from config import BOSS_EVERY, STORY_LOG_LINES
from enemies import Enemy
from history import BuildHistory
from projectiles import Puff
from save import read_save, run_from_data, run_to_data, write_save
import story
from pickups import KINDS, Pickup
from units import Unit, group_multiplier, recipe_for
from waves import build_wave, hp_multiplier, speed_multiplier, preview, BOSS
from world import make_map

FEED_LIFE = 4.0  # Seconds a kill-feed line stays up
FEED_MAX = 5
FLAP_INTERVAL = 0.5  # Seconds between flying-enemy wing sounds
NEUTRAL = (230, 230, 230)
GOOD = (120, 220, 120)
BAD = (230, 100, 90)
NOTE = (255, 196, 40)


class Game:
    """Game rules and state. No drawing or input here, so it can be tested without a window.

    Sandbox: rounds never run out. Every MAP_EVERY rounds the route is redrawn at random, and the game only
    ends when the lives run out.
    """

    def __init__(self, faction, map_index=0, difficulty="Normal"):
        self.faction = faction  # The player's faction
        self.enemy_faction = OPPONENT[faction]
        self.difficulty = difficulty
        self.map = make_map(map_index)
        self.gold = START_GOLD
        self.lives = START_LIVES
        self.wave = 0  # The round that is running, or was last run
        self.kills = 0
        self.units = []  # Placed units
        self.all_units = []  # Every unit this run has had, including sold ones, for the stats screen
        self.leaks = Counter()  # Enemy name -> how many got through
        self.enemies = []
        self.projectiles = []
        self.zones = []  # Burn zones on the ground
        self.effects = []  # Short-lived puffs
        self.selected = "rapid"  # Role the player will build next
        self.selected_unit = None  # A placed unit being inspected or upgraded
        self.status = "playing"  # "playing" or "lost"
        self.message = ""  # Feedback line, such as "Need 50 gold"
        self.wave_active = False
        self.hp_mult = 1.0  # Per-round hp growth (difficulty is applied on top of this when spawning)
        self.speed_mult = 1.0
        self._queue = []  # Spawns still to come in the active round: (time, kind)
        self.rushing = False  # Space during a round: spawn the queue faster
        self._wave_time = 0.0
        self._sell_unit = None  # The unit a first SELL click has armed
        self._sell_timer = 0.0  # Seconds left to confirm the sale
        self.countdown = AUTO_START_SECONDS  # Counts down between rounds, then the next round starts itself
        self.countdown_locked = False  # True during the build time after a map change: the clock must run out
        # HUD feedback
        self.feed = []  # [text, colour, seconds left], newest last
        self.banner = ""
        self.banner_life = 0.0
        self.hitmark = 0.0  # Seconds the hit marker stays up after a kill
        self.gain = 0  # Last reward, shown next to the gold
        self.gain_life = 0.0
        self.narrative = ""  # The story line for this round, shown under the banner
        self.story_log = []  # Every story line of this run, newest last, for the story log (L)
        self.narrative_life = 0.0
        # Sound events for the audio layer to play. main.py drains them every frame
        self.sound_events = []
        self._groan_timer = 0.0
        self._flap_timer = 0.0
        self.history = BuildHistory()  # Placements and sales this build phase, for undo
        self.slot = 1  # Save slot this run writes to
        self._rng = random.Random()
        self.pickups = []  # Map pickups on the route, during a round
        self._pickup_timer = PICKUP_EVERY
        self.rage = 0.0  # Seconds of rage left (every unit fires faster)
        self.freeze = 0.0  # Seconds of freeze left (ground enemies are slowed)

    @property
    def _hp_scale(self):
        return DIFFICULTIES[self.difficulty]["hp"]

    @property
    def _reward_scale(self):
        return DIFFICULTIES[self.difficulty]["reward"]

    def drain_sounds(self):
        events, self.sound_events = self.sound_events, []
        return events

    # --- BUILDING ---

    def unit_at(self, col, row):
        for unit in self.units:
            if int(unit.x) == col and int(unit.y) == row:
                return unit
        return None

    def placement_error(self, col, row, role=None):
        """None if a unit of this role can be built on the cell, otherwise the reason."""
        role = role or self.selected
        if self.status != "playing":
            return "Game over"
        if not self.map.is_buildable(col, row) or self.unit_at(col, row) is not None:
            return "Can't build there"
        if len(self.units) >= MAX_UNITS:
            return f"Unit cap: {MAX_UNITS} units. Sell or combine one first"
        cost = UNIT_TYPES[self.faction][role]["cost"]
        if cost > self.gold:
            return f"Need {cost} gold"
        return None

    def place(self, col, row, role=None):
        role = role or self.selected
        error = self.placement_error(col, row, role)
        if error:
            self.message = error
            return None
        self.gold -= UNIT_TYPES[self.faction][role]["cost"]
        unit = Unit(self.faction, role, col + 0.5, row + 0.5)
        self.units.append(unit)
        self.all_units.append(unit)
        self.history.record(("place", unit))
        self.message = ""
        return unit

    def click_cell(self, col, row):
        """A click on a tile: collect a pickup there, select the unit on it, or build on it if it is empty."""
        pickup = self.pickup_at(col, row)
        if pickup is not None:
            self.collect(pickup)
            return None
        unit = self.unit_at(col, row)
        if unit is not None:
            self.selected_unit = unit
            self.message = ""
            self.sound_events.append(("select", unit.faction, unit.kind))
            return unit
        self.selected_unit = None
        return self.place(col, row)

    def deselect(self):
        self.selected_unit = None
        self.message = ""
        self._sell_timer = 0.0

    # --- UPGRADES AND SELLING ---

    def upgrade_cost(self, unit):
        return round(unit.cost * UPGRADE_COST[unit.level - 1])

    def upgrade(self):
        """Raise the selected unit one level, up to level 3. The step to level 4 needs choose_ultimate()."""
        unit = self.selected_unit
        if unit is None:
            self.message = "Select a unit first"
            return False
        if unit.level >= 3:
            self.message = "Pick an ultimate: A or B"
            return False
        cost = self.upgrade_cost(unit)
        if cost > self.gold:
            self.message = f"Need {cost} gold"
            return False
        self.gold -= cost
        unit.spent += cost
        unit.level += 1
        self.message = f"{UNIT_TYPES[unit.faction][unit.kind]['name']} is now level {unit.level}"
        return True

    def choose_ultimate(self, index):
        """Turn the selected level-3 unit into one of its two ultimate forms (index 0 or 1)."""
        unit = self.selected_unit
        if unit is None:
            self.message = "Select a unit first"
            return False
        if unit.level < 3:
            self.message = "Reach level 3 first"
            return False
        if index not in (0, 1):
            return False
        if unit.level >= 4:
            return self._respec(unit, index)
        cost = self.upgrade_cost(unit)
        if cost > self.gold:
            self.message = f"Need {cost} gold"
            return False
        self.gold -= cost
        unit.spent += cost
        unit.level = 4
        unit.ultimate_index = index
        unit.ultimate = ULTIMATES[unit.faction][unit.kind][index]
        self.message = f"{unit.ultimate['name']}!"
        return True

    def _respec(self, unit, index):
        """Switch a level 4 unit to its other ultimate. Between rounds only, and it costs part of the unit price."""
        if unit.ultimate_index == index:
            self.message = "Already using that ultimate"
            return False
        if self.wave_active:
            self.message = "Switch ultimates between rounds"
            return False
        cost = round(unit.cost * RESPEC_COST)
        if cost > self.gold:
            self.message = f"Need {cost} gold"
            return False
        self.gold -= cost
        unit.spent += cost
        unit.ultimate_index = index
        unit.ultimate = ULTIMATES[unit.faction][unit.kind][index]
        self.message = f"Switched to {unit.ultimate['name']}"
        return True

    def sell_refund(self, unit):
        return round(unit.spent * SELL_REFUND)

    @property
    def sell_time_left(self):
        """Seconds left to confirm a sale that has been armed."""
        return self._sell_timer

    def sell_armed(self, unit):
        """True while the first SELL click on this unit is waiting for a second click."""
        return self._sell_timer > 0 and self._sell_unit is unit

    def sell(self):
        """Sell the selected unit for a share of the gold spent on it. Takes two clicks: the first arms it,
        the second, within SELL_CONFIRM_SECONDS, confirms. Returns True when the unit is sold."""
        unit = self.selected_unit
        if unit is None:
            self.message = "Select a unit to sell"
            return False
        refund = self.sell_refund(unit)
        if not self.sell_armed(unit):
            self._sell_unit = unit
            self._sell_timer = SELL_CONFIRM_SECONDS
            self.message = f"Press SELL again to confirm: +{refund} gold"
            return False
        self._sell_timer = 0.0
        index = self.units.index(unit)
        self.units.remove(unit)
        self.history.record(("sell", unit, index))
        self.selected_unit = None
        self.gold += refund
        self.sound_events.append(("cash",))
        name = UNIT_TYPES[unit.faction][unit.kind]["name"]
        self.message = f"Sold {name} for {refund} gold"
        self._log(f"{name} sold  +{refund}", NOTE)
        return True

    # --- COMBINING ---

    NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))  # Edge-sharing cells

    def combine_option(self, unit):
        """The adjacent unit that `unit` can combine with, as (partner, recipe_id, recipe), or None.
        Ultimates and already-combined units take no part. Neighbours are tried in NEIGHBOURS order."""
        if unit is None or unit.level > 3 or unit.recipe is not None:
            return None
        col, row = int(unit.x), int(unit.y)
        for dc, dr in self.NEIGHBOURS:
            other = self.unit_at(col + dc, row + dr)
            if other is None or other.level > 3 or other.recipe is not None:
                continue
            found = recipe_for(self.faction, unit.kind, other.kind)
            if found is not None:
                return (other,) + found
        return None

    def combine_cost(self, unit, partner):
        """Gold to combine two units: a share of their base prices, scaled by the difficulty."""
        return round((unit.cost + partner.cost) * COMBINE_COST * DIFFICULTIES[self.difficulty]["combine"])

    def combine(self):
        """Fuse the selected unit with the adjacent unit it has a recipe for. The result takes the first unit's
        tile, and two units become one, so a slot is freed. Returns True when the units are combined."""
        unit = self.selected_unit
        if unit is None:
            self.message = "Select a unit first"
            return False
        option = self.combine_option(unit)
        if option is None:
            self.message = "Put a unit it combines with next to it"
            return False
        partner, recipe_id, recipe = option
        cost = self.combine_cost(unit, partner)
        if cost > self.gold:
            self.message = f"Need {cost} gold"
            return False
        self.gold -= cost
        fused = Unit(self.faction, recipe["base"], unit.x, unit.y, recipe=recipe_id)
        fused.level = max(unit.level, partner.level)  # Both are at most level 3, so the result is too
        fused.spent = unit.spent + partner.spent + cost
        first, second = self.units.index(unit), self.units.index(partner)
        self.units.remove(unit)
        self.units.remove(partner)
        self.units.insert(min(first, second), fused)
        self.all_units.append(fused)
        self.selected_unit = fused
        self.history.record(("combine", unit, partner, fused, first, second))
        self.sound_events.append(("cash",))
        self.message = f"{recipe['name']} formed  -{cost} gold"
        self._log(f"{recipe['name']} combined  -{cost}", NOTE)
        return True

    # --- ROUNDS AND MAPS ---

    def next_round_preview(self):
        """What the next round brings, as [(enemy name, count)], most common first."""
        counts = preview(self.enemy_faction, self.wave + 1)
        rows = []
        for kind, n in counts.most_common():
            spec = ENEMY_TYPES[self.enemy_faction][kind]
            rows.append((spec["name"] + (" (air)" if spec.get("flying") else ""), n))
        return rows

    def next_round_warnings(self):
        """Tags for things the next round brings that need a plan: BOSS and FLYERS."""
        warnings = []
        if (self.wave + 1) % BOSS_EVERY == 0:
            warnings.append("BOSS")
        if self.next_round_has_flyers():
            warnings.append("FLYERS")
        return warnings

    def next_round_has_flyers(self):
        return any(ENEMY_TYPES[self.enemy_faction][kind].get("flying")
                   for kind in preview(self.enemy_faction, self.wave + 1))

    def toggle_rush(self):
        """Space during a round: spawn the rest of the round faster. Press again to go back to normal."""
        if not self.wave_active:
            return False
        self.rushing = not self.rushing
        self._log("Spawning fast" if self.rushing else "Spawning normal", NOTE)
        return True

    def start_wave(self):
        if self.status != "playing" or self.wave_active:
            return False
        if self.countdown_locked:
            self.message = f"The new map is still being built: {math.ceil(self.countdown)} s"
            return False
        self.countdown = AUTO_START_SECONDS
        self.wave = self.wave + 1
        self.history.clear()  # Rounds lock in the build
        self._queue = build_wave(self.enemy_faction, self.wave)
        self._wave_time = 0.0
        self.hp_mult = hp_multiplier(self.wave)
        self.speed_mult = speed_multiplier(self.wave)
        self.wave_active = True
        self.rushing = False
        self.message = ""
        self._announce(f"ROUND {self.wave}", 2.5)
        self._narrate(story.round_line(self.faction, self.wave), 8.0)
        return True

    def _new_map(self):
        """Redraw the route. Units standing on the new route are refunded in full and removed. Called when a round
        clears, so the player has the build time to put the removed units back."""
        new_map = make_map(self.map.index + 1)
        refund = 0
        kept = []
        for unit in self.units:
            if not new_map.is_buildable(int(unit.x), int(unit.y)):
                refund += unit.spent
            else:
                kept.append(unit)
        removed = len(self.units) - len(kept)
        self.units = kept
        if self.selected_unit not in kept:
            self.selected_unit = None
        self.map = new_map
        self.projectiles = []
        self.zones = []
        self.history.clear()  # The build it would undo is gone
        self.gold += refund
        if removed:
            self._log(f"Route moved: {removed} unit(s) refunded {refund} gold", NOTE)

    # --- SIMULATION ---

    def _route_for(self, kind):
        """Ground enemies follow the route. Flyers cut straight from the start marker to the end marker."""
        if ENEMY_TYPES[self.enemy_faction][kind].get("flying"):
            return [self.map.route[0], self.map.route[-1]]
        return self.map.route

    def _spawn(self, kind):
        spec = ENEMY_TYPES[self.enemy_faction][kind]
        self.enemies.append(Enemy(self.enemy_faction, kind, self._route_for(kind),
                                  hp_mult=self.hp_mult * self._hp_scale, speed_mult=self.speed_mult))
        if kind == BOSS:
            self._announce(f"BOSS: {spec['name'].upper()}", 3.0)
            self._narrate(story.boss_line(self.faction), 10.0)
            self.sound_events.append(("boss",))

    def update(self, dt, real_dt=None):
        """Advance the game by dt seconds of play. real_dt is the wall-clock time for the same step, which the
        map build time counts in; it defaults to dt. The steps run in this order, which the rules depend on."""
        self._tick_hud(dt)
        if self.status != "playing":
            return
        self._tick_pickups(dt)
        self._tick_countdown(dt, dt if real_dt is None else real_dt)
        self._spawn_due(dt)
        self._advance_enemies(dt)
        self.zones = [zone for zone in self.zones if zone.update(dt, self.enemies)]
        self._tick_ambience(dt)
        self._apply_auras()
        self._fire_and_hit(dt)
        self._resolve_deaths()

        if self.lives <= 0:
            self.lives = 0
            self.status = "lost"
            self.wave_active = False
            return
        self._check_round_cleared()

    def _tick_countdown(self, dt, real_dt):
        """Between rounds the next one starts itself when the countdown runs out. The map build time runs on the
        real clock, so fast forward and fast spawning do not shorten it."""
        if not self.wave_active:
            self.countdown -= real_dt if self.countdown_locked else dt
            if self.countdown <= 0:
                self.countdown_locked = False
                self.start_wave()

    def _spawn_due(self, dt):
        """Release the queued enemies whose spawn time has come. Fast spawning runs the clock faster."""
        if self.wave_active:
            self._wave_time += dt * (SPAWN_RUSH if self.rushing else 1.0)
            while self._queue and self._queue[0][0] <= self._wave_time:
                _, kind = self._queue.pop(0)
                self._spawn(kind)

    def _advance_enemies(self, dt):
        """Move the enemies along the route. Any that reach the end cost lives and are taken out of play."""
        for enemy in self.enemies:
            if enemy.alive and enemy.advance(dt):
                enemy.leaked = True
                enemy.hp = 0  # Takes it out of play so towers stop targeting it
                self.lives -= enemy.spec["leak"]
                self.leaks[enemy.spec["name"]] += 1
                self._log(f"! {enemy.spec['name']} breached  -{enemy.spec['leak']} life", BAD)

    def _tick_ambience(self, dt):
        """Sound cues: zombies groan while any are alive, and flyers beat their wings while they are up."""
        self._groan_timer -= dt
        zombies = [e for e in self.enemies if e.alive and e.faction == "zombie" and not e.flying]
        if zombies and self._groan_timer <= 0:
            self.sound_events.append(("groan",))
            self._groan_timer = self._rng.uniform(0.8, 1.8)

        self._flap_timer -= dt
        if self._flap_timer <= 0 and any(e.alive and e.flying for e in self.enemies):
            self.sound_events.append(("flap", self.enemy_faction))
            self._flap_timer = FLAP_INTERVAL

    def _fire_and_hit(self, dt):
        """Units shoot, shots fly and hit, and puffs fade."""
        for unit in self.units:
            shots = unit.update(dt, self.enemies)
            if shots:
                self.sound_events.append(("fire", unit.faction, unit.kind))
                self.projectiles.extend(shots)
        for projectile in self.projectiles:
            projectile.update(dt, self.enemies, self.zones, self.effects)
        self.projectiles = [p for p in self.projectiles if not p.done]
        self.effects = [puff for puff in self.effects if puff.update(dt)]

    def _resolve_deaths(self):
        """Pay out and count the enemies killed this step. Leakers were already paid for by their lives."""
        still_alive = []
        for enemy in self.enemies:
            if enemy.alive:
                still_alive.append(enemy)
            elif not enemy.leaked:
                reward = round(enemy.spec["reward"] * self._reward_scale)
                self.gold += reward
                self.kills += 1
                self.gain = reward
                self.gain_life = 1.0
                self.hitmark = 0.15
                self._log(f"{enemy.spec['name']} eliminated  +{reward}", NEUTRAL)
                self.effects.append(Puff(enemy.x, enemy.y, (230, 230, 210), size=3.0, life=0.4))
        self.enemies = still_alive

    def _check_round_cleared(self):
        """A round is cleared once every enemy has spawned and been dealt with. Pays the bonus and starts the
        countdown to the next round."""
        if self.wave_active and not self._queue and not self.enemies:
            self.wave_active = False
            self.rushing = False
            self.pickups = []
            bonus = WAVE_BONUS + WAVE_BONUS_GROWTH * (self.wave - 1)
            self.gold += bonus
            self._announce(f"ROUND {self.wave} CLEARED  +{bonus}", 2.5)
            if self.wave % MAP_EVERY == 0:  # The next round is on a new map: give the player time to rebuild
                self._new_map()
                self._announce(f"NEW MAP  BUILD {MAP_BUILD_SECONDS:.0f} SECONDS", 4.0)
                self.countdown = MAP_BUILD_SECONDS
                self.countdown_locked = True
            else:
                self.countdown = AUTO_START_SECONDS

    def _apply_groups(self):
        """Combo groups: same-type units standing close together. Each unit learns its group size.
        A chime plays when a unit's group reaches a new damage tier."""
        for unit in self.units:
            before = group_multiplier(unit.group)
            near = [other for other in self.units
                    if other is not unit and (other.x - unit.x) ** 2 + (other.y - unit.y) ** 2 <= COMBO_RADIUS ** 2]
            unit.group = 1 + sum(1 for other in near if other.kind == unit.kind)
            unit.mixed = len({other.kind for other in near if other.kind != unit.kind})
            if group_multiplier(unit.group) > before:
                self.sound_events.append(("combo",))

    def _apply_auras(self):
        self._apply_groups()
        for unit in self.units:
            unit.buff = 1.0
            unit.dmg_buff = 1.0
        for source in self.units:
            stats = source.stats
            if not stats["aura"]:
                continue
            radius, boost = stats["aura"]
            for unit in self.units:
                if unit is not source and ((unit.x - source.x) ** 2 + (unit.y - source.y) ** 2) <= radius ** 2:
                    unit.buff = max(unit.buff, boost)
                    unit.dmg_buff = max(unit.dmg_buff, stats["aura_damage"])
        if self.rage > 0:
            for unit in self.units:
                unit.buff *= RAGE_FIRE

    # --- MAP PICKUPS ---

    def _tick_pickups(self, dt):
        self.rage = max(0.0, self.rage - dt)
        self.freeze = max(0.0, self.freeze - dt)
        self.pickups = [p for p in self.pickups if p.update(dt)]
        if self.wave_active:
            self._pickup_timer -= dt
            if self._pickup_timer <= 0:
                self._pickup_timer = PICKUP_EVERY
                self._drop_pickup()
        if self.freeze > 0:
            for enemy in self.enemies:
                if enemy.alive and not enemy.flying:
                    enemy.apply_slow(FREEZE_FACTOR, 0.25)

    def _drop_pickup(self):
        taken = {(p.col, p.row) for p in self.pickups}
        cells = [cell for cell in sorted(self.map.cells) if cell not in taken]
        if cells:
            col, row = self._rng.choice(cells)
            self.pickups.append(Pickup(col, row, self._rng.choice(KINDS)))

    def pickup_at(self, col, row):
        for pickup in self.pickups:
            if (pickup.col, pickup.row) == (col, row):
                return pickup
        return None

    def collect(self, pickup):
        self.pickups.remove(pickup)
        if pickup.kind == "gold":
            self.gold += PICKUP_GOLD
            self._log(f"Gold pickup  +{PICKUP_GOLD}", GOOD)
        elif pickup.kind == "rage":
            self.rage = RAGE_SECONDS
            self._log(f"RAGE: units fire faster for {RAGE_SECONDS:.0f} s", NOTE)
        elif pickup.kind == "freeze":
            self.freeze = FREEZE_SECONDS
            self._log(f"FREEZE: ground enemies slowed for {FREEZE_SECONDS:.0f} s", NEUTRAL)
        self.sound_events.append(("cash",))

    def _tick_hud(self, dt):
        self.banner_life = max(0.0, self.banner_life - dt)
        self.hitmark = max(0.0, self.hitmark - dt)
        self.gain_life = max(0.0, self.gain_life - dt)
        self.narrative_life = max(0.0, self.narrative_life - dt)
        self._sell_timer = max(0.0, self._sell_timer - dt)
        for entry in self.feed:
            entry[2] -= dt
        self.feed = [entry for entry in self.feed if entry[2] > 0]

    def _narrate(self, text, seconds):
        self.narrative = text
        self.story_log = (self.story_log + [text])[-STORY_LOG_LINES:]
        self.narrative_life = seconds

    def _announce(self, text, seconds):
        self.banner = text
        self.banner_life = seconds

    def _log(self, text, colour):
        self.feed.append([text, colour, FEED_LIFE])
        self.feed = self.feed[-FEED_MAX:]

    # --- POST-LOSS REPORT ---

    def report(self):
        """What the stats screen shows: the best three damage dealers and the three most common leakers."""
        damage = [(f"{UNIT_TYPES[u.faction][u.kind]['name']} L{u.level}", round(u.damage), u.kills)
                  for u in self.all_units if u.damage > 0]
        damage.sort(key=lambda row: -row[1])
        return {"round": self.wave, "kills": self.kills, "damage": damage[:3], "leaks": self.leaks.most_common(3)}

    # --- SAVE AND LOAD (between rounds only) ---

    def save(self, path):
        """Write the run to `path`. Only allowed between rounds, so there are no enemies or shots to store."""
        if self.status != "playing" or self.wave_active:
            self.message = "Save between rounds"
            return False
        ok, self.message = write_save(path, run_to_data(self))
        return ok

    @staticmethod
    def load_slot(path):
        """(game, None) from the save at `path`, or (None, reason). The reason is "empty", "unreadable" or
        "incompatible", so the title screen can explain why a slot did not load."""
        data, reason = read_save(path)
        if data is None:
            return None, reason
        try:
            game = run_from_data(data)
        except (KeyError, TypeError, ValueError, IndexError):
            return None, "unreadable"
        game.message = "Game loaded"
        return game, None

    @staticmethod
    def load(path):
        """A game from the save at `path`, or None if there is no usable save."""
        return Game.load_slot(path)[0]

    @staticmethod
    def save_round(path):
        """The round a save slot holds, or None if the slot is empty, unreadable or from another version."""
        data, _ = read_save(path)
        return None if data is None else data.get("wave")

    # --- UNDO AND REINFORCEMENT ---

    def undo(self):
        """Take back the most recent placement or sale. Only between rounds. See history.py."""
        return self.history.undo(self)

    def reinforce_cost(self, unit):
        growth = 1 + REINFORCE_GROWTH * max(0, self.wave - 1)
        return max(1, round(unit.cost * REINFORCE_COST * growth))

    def reinforce(self):
        """Permanent damage bonus for an ultimate unit. Costs more the later it is bought."""
        unit = self.selected_unit
        if unit is None:
            self.message = "Select a unit first"
            return False
        if unit.level < 4:
            self.message = "Reinforce needs an ultimate"
            return False
        if unit.reinforce >= REINFORCE_MAX:
            self.message = "Fully reinforced"
            return False
        cost = self.reinforce_cost(unit)
        if cost > self.gold:
            self.message = f"Need {cost} gold"
            return False
        self.gold -= cost
        unit.spent += cost
        unit.reinforce += 1
        self.message = f"Reinforced ({unit.reinforce}/{REINFORCE_MAX})"
        return True
