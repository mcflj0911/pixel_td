"""The running game: the window, the screen that is showing, and the state each screen needs.

Screens: the title (with the demo battle behind it), the briefing card before a run, and the battle itself. On top of
the battle sits at most one overlay at a time: the quit prompt, the help (F1) or the story log (L). Pause (P) is
separate: it freezes the battle, and clicks do nothing while it is on.
"""
import pygame

from camera import Camera
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, SPEEDS, ROLES, DIFFICULTIES, SAVE_SLOTS, VOLUME_STEP
from demo import Demo
from display import fit, to_canvas
from draw_kit import make_fonts
from game import Game
from hud import draw_hud
from render import draw_scene
from save import save_path, autosave_path
from screens import draw_title, draw_quit_prompt, draw_pause, draw_help, draw_briefing, draw_log
from settings import (load_settings, save_settings, load_records, save_records, best_round, record_round,
                      TEXT_SCALES, MAP_CHOICES)
from sounds import Sounds
from ui import ui_action

ROLE_KEYS = {getattr(pygame, f"K_{i + 1}"): role for i, role in enumerate(ROLES)}
SLOT_KEYS = {getattr(pygame, f"K_{i + 1}"): i + 1 for i in range(SAVE_SLOTS)}
SAVE_NOTICES = {  # Why a save slot would not load, shown on the title screen
    "unreadable": "That save file is damaged and cannot be loaded",
    "incompatible": "That save was made by another version of the game",
}
FACTIONS = ("human", "zombie")
MAX_STEP_SECONDS = 0.05  # A stalled window does not skip the simulation ahead by more than this


def handle_action(game, action):
    """Carry out a HUD click, as returned by ui.ui_action."""
    kind = action[0]
    if kind == "role":
        game.selected = action[1]
        game.selected_unit = None
    elif kind == "upgrade":
        game.upgrade()
    elif kind == "reinforce":
        game.reinforce()
    elif kind == "ultimate":
        game.choose_ultimate(action[1])
    elif kind == "sell":
        game.sell()


def read_saves():
    """The round each save slot holds, for the title screen. None means the slot is empty."""
    return {slot: Game.save_round(save_path(slot)) for slot in range(1, SAVE_SLOTS + 1)}


def open_window(fullscreen):
    """The game window: resizable, or fullscreen. The game is drawn to a fixed canvas and scaled to fit."""
    if fullscreen:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)


def _key(event, *keys):
    return event.type == pygame.KEYDOWN and event.key in keys


class App:
    def __init__(self):
        self.settings = load_settings()
        self.window = open_window(self.settings["fullscreen"])
        pygame.display.set_caption("Pixel TD")
        self.canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = make_fonts(TEXT_SCALES[self.settings["text_scale"]])
        self.camera = Camera()
        self.demo = Demo()
        self.sounds = Sounds()
        self.sounds.level = self.settings["volume"]
        self.sounds.muted = self.settings["muted"]
        self.records = load_records()
        self.logged_game = None  # The last finished run written to the records, so it is only counted once
        self.setup = {"map": self.settings["map"], "difficulty": self.settings["difficulty"],
                      "slot": self.settings["slot"], "notice": "", "text_scale": self.settings["text_scale"]}
        self.setup.update(self.title_state())

        self.game = None  # None means we are on the title screen, watching the demo
        self.briefing = None  # The faction whose opening story card is showing, before the run starts
        self.speed_index = 0
        self.hover = None  # The tile under the pointer, for the battle view
        self.dest = (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)  # Where the canvas is drawn in the window
        self.running = True
        self.overlay = None  # "quit" (Esc asks first, so a stray key press does not lose a run), "help" or "log"
        self.paused = False  # P

    # --- Shared state ---

    def title_state(self):
        """What the title screen shows: the save slots, the autosave, and the best round for each faction."""
        return {"saves": read_saves(), "autosave": Game.save_round(autosave_path()),
                "best": {f: best_round(self.records, f, self.setup["difficulty"]) for f in FACTIONS}}

    def frozen(self):
        """True while the battle is stopped: pause, or an overlay is up."""
        return self.overlay is not None or self.paused

    def persist(self):
        """Remember the current choices between sessions. If the disk refuses, the title screen says so."""
        s = self.settings
        s.update(volume=round(self.sounds.level, 2), muted=self.sounds.muted, map=self.setup["map"],
                 difficulty=self.setup["difficulty"], slot=self.setup["slot"], text_scale=s["text_scale"],
                 fullscreen=s["fullscreen"], skip_briefing=s["skip_briefing"])
        if not save_settings(s):
            self.setup["notice"] = "Could not save your settings"

    def _start_run(self, faction):
        self.game = Game(faction, map_index=self.setup["map"], difficulty=self.setup["difficulty"])
        self.game.slot = self.setup["slot"]

    # --- Main loop ---

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, MAX_STEP_SECONDS)
            self.window = pygame.display.get_surface()
            self.dest = fit(*self.window.get_size(), SCREEN_WIDTH, SCREEN_HEIGHT)
            pointer = to_canvas(pygame.mouse.get_pos(), self.dest, SCREEN_WIDTH, SCREEN_HEIGHT)

            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw(pointer)

            self.window.fill((0, 0, 0))
            self.window.blit(pygame.transform.scale(self.canvas, (self.dest[2], self.dest[3])), self.dest[:2])
            pygame.display.flip()
        self.persist()

    # --- Events ---

    def handle_event(self, event):
        """Route one event. Earlier branches take precedence: the quit key, then overlays, then the screens."""
        if event.type == pygame.QUIT:
            self.running = False
        elif _key(event, pygame.K_F11):
            self.settings["fullscreen"] = not self.settings["fullscreen"]
            self.window = open_window(self.settings["fullscreen"])
            self.persist()
        elif self.overlay == "quit":
            self._quit_prompt_event(event)
        elif self.overlay == "help":
            if _key(event, pygame.K_F1, pygame.K_ESCAPE):
                self.overlay = None
        elif self.overlay == "log":
            if _key(event, pygame.K_l, pygame.K_ESCAPE):
                self.overlay = None
        elif self._sound_or_text_key(event):
            pass  # Works on every screen
        elif self.game is None and self.briefing is not None:
            self._briefing_event(event)
        elif self.game is None:
            self._title_event(event)
        else:
            self._battle_event(event)

    def _quit_prompt_event(self, event):
        if _key(event, pygame.K_y):
            self.running = False
        elif _key(event, pygame.K_n, pygame.K_ESCAPE):
            self.overlay = None

    def _sound_or_text_key(self, event):
        """M, the volume keys and T work everywhere. Returns True if the event was one of them."""
        if _key(event, pygame.K_m):
            self.sounds.toggle_mute()
            self.persist()
        elif _key(event, pygame.K_MINUS, pygame.K_KP_MINUS):
            self.sounds.change_level(-VOLUME_STEP)
            self.persist()
        elif _key(event, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.sounds.change_level(VOLUME_STEP)
            self.persist()
        elif _key(event, pygame.K_t):
            names = list(TEXT_SCALES)
            self.settings["text_scale"] = names[(names.index(self.settings["text_scale"]) + 1) % len(names)]
            self.setup["text_scale"] = self.settings["text_scale"]
            self.fonts = make_fonts(TEXT_SCALES[self.settings["text_scale"]])
            self.persist()
        else:
            return False
        return True

    def _briefing_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._start_run(self.briefing)
            self.briefing = None
        elif event.key == pygame.K_d:
            self.settings["skip_briefing"] = not self.settings["skip_briefing"]
            self.persist()
        elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.briefing = None

    def _title_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        self.setup["notice"] = ""
        if event.key in (pygame.K_h, pygame.K_z):
            faction = "human" if event.key == pygame.K_h else "zombie"
            if self.settings["skip_briefing"]:
                self._start_run(faction)
            else:
                self.briefing = faction
        elif event.key in SLOT_KEYS:
            self.setup["slot"] = SLOT_KEYS[event.key]
            self.persist()
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            step = -1 if event.key == pygame.K_LEFT else 1
            self.setup["map"] = (self.setup["map"] + step) % MAP_CHOICES
            self.persist()
        elif event.key == pygame.K_d:
            names = list(DIFFICULTIES)
            self.setup["difficulty"] = names[(names.index(self.setup["difficulty"]) + 1) % len(names)]
            self.setup.update(self.title_state())
            self.persist()
        elif event.key == pygame.K_c:
            loaded, reason = Game.load_slot(save_path(self.setup["slot"]))
            if loaded is not None:
                loaded.slot = self.setup["slot"]
                self.game = loaded
            else:
                self.setup["notice"] = SAVE_NOTICES.get(reason, "")
        elif event.key == pygame.K_a:
            loaded, reason = Game.load_slot(autosave_path())
            if loaded is not None:
                self.game = loaded
            else:
                self.setup["notice"] = SAVE_NOTICES.get(reason, "There is no autosave yet")
        elif event.key == pygame.K_ESCAPE:
            self.overlay = "quit"

    def _battle_event(self, event):
        game = self.game
        if _key(event, pygame.K_z) and event.mod & pygame.KMOD_CTRL:
            game.undo()
        elif event.type == pygame.KEYDOWN:
            self._battle_key(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self.hover = self.camera.screen_to_tile(*to_canvas(event.pos, self.dest, SCREEN_WIDTH, SCREEN_HEIGHT))
        elif event.type == pygame.MOUSEBUTTONDOWN and self.frozen():
            pass  # Clicks do nothing while paused, in help, the log or at the quit prompt
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._battle_click(event)

    def _battle_key(self, key):
        game = self.game
        if key == pygame.K_ESCAPE:
            self.overlay = "quit"
        elif key == pygame.K_F1:
            self.overlay = "help"
        elif key == pygame.K_l:
            self.overlay = "log"
        elif key == pygame.K_p:
            self.paused = not self.paused
        elif key in ROLE_KEYS:
            game.selected = ROLE_KEYS[key]
            game.selected_unit = None
        elif key == pygame.K_SPACE:
            if not game.start_wave():
                game.toggle_rush()
        elif key == pygame.K_F5:
            game.save(save_path(game.slot))
        elif key == pygame.K_f:
            self.speed_index = (self.speed_index + 1) % len(SPEEDS)
        elif key == pygame.K_u:
            game.upgrade()
        elif key == pygame.K_g:
            game.reinforce()
        elif key == pygame.K_a:
            game.choose_ultimate(0)
        elif key == pygame.K_b:
            game.choose_ultimate(1)
        elif key == pygame.K_x:
            game.sell()
        elif key == pygame.K_r and game.status != "playing":
            self.game = None
            self.setup.update(self.title_state())

    def _battle_click(self, event):
        point = to_canvas(event.pos, self.dest, SCREEN_WIDTH, SCREEN_HEIGHT)
        if event.button == 3:
            self.game.deselect()
        elif event.button == 1:
            action = ui_action(point, self.game)
            if action is not None:
                handle_action(self.game, action)
            else:
                cell = self.camera.screen_to_tile(*point)
                if cell is None:
                    self.game.deselect()
                else:
                    self.game.click_cell(*cell)

    # --- Simulation ---

    def update(self, dt):
        if self.game is None:
            self.demo.update(dt)
            self.demo.game.drain_sounds()  # The demo battle is silent
            return
        if not self.frozen():  # The battle stops while a menu, the help, the log, the quit prompt or pause is up
            self._step_battle(dt * SPEEDS[self.speed_index])
        for event in self.game.drain_sounds():
            self.sounds.play_event(event)

    def _step_battle(self, dt):
        game = self.game
        was_active = game.wave_active
        game.update(dt)
        if was_active and not game.wave_active and game.status == "playing":
            game.save(autosave_path())  # Every cleared round is an autosave
        if game.status == "lost" and game is not self.logged_game:
            self.logged_game = game
            if record_round(self.records, game.faction, game.difficulty, game.wave):
                if not save_records(self.records):
                    self.setup["notice"] = "Could not save the best rounds"

    # --- Drawing ---

    def draw(self, pointer):
        if self.game is None:
            scene = draw_scene(self.camera, self.demo.game, None)
            pygame.transform.scale(scene, (SCREEN_WIDTH, SCREEN_HEIGHT), self.canvas)
            if self.briefing is not None:
                draw_briefing(self.canvas, self.fonts, self.briefing, self.settings["skip_briefing"])
            else:
                draw_title(self.canvas, self.fonts, self.setup)
        else:
            scene = draw_scene(self.camera, self.game, self.hover)
            pygame.transform.scale(scene, (SCREEN_WIDTH, SCREEN_HEIGHT), self.canvas)
            draw_hud(self.canvas, self.game, SPEEDS[self.speed_index], self.fonts, pointer,
                     self.sounds.status_text())
            if self.overlay == "help":
                draw_help(self.canvas, self.fonts)
            elif self.overlay == "log":
                draw_log(self.canvas, self.fonts, self.game.story_log)
            elif self.paused:
                draw_pause(self.canvas, self.fonts, self.game)
        if self.overlay == "quit":
            draw_quit_prompt(self.canvas, self.fonts)
