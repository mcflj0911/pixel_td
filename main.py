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


def handle_action(game, action):
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


def main():
    pygame.mixer.pre_init(22050, -16, 2, 512)  # Matches sounds.SR. Set before init so the format is right
    pygame.init()
    settings = load_settings()
    window = open_window(settings["fullscreen"])
    pygame.display.set_caption("Pixel TD")
    canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    fonts = make_fonts(TEXT_SCALES[settings["text_scale"]])
    camera = Camera()
    demo = Demo()
    sounds = Sounds()
    sounds.level = settings["volume"]
    sounds.muted = settings["muted"]
    records = load_records()
    logged_game = None  # The last finished run written to the records, so it is only counted once

    def persist():
        settings.update(volume=round(sounds.level, 2), muted=sounds.muted, map=setup["map"],
                        difficulty=setup["difficulty"], slot=setup["slot"], text_scale=settings["text_scale"],
                        fullscreen=settings["fullscreen"], skip_briefing=settings["skip_briefing"])
        save_settings(settings)

    def title_state():
        """What the title screen shows: the save slots, the autosave, and the best round for each faction."""
        autosave = Game.save_round(autosave_path())
        return {"saves": read_saves(), "autosave": autosave,
                "best": {f: best_round(records, f, setup["difficulty"]) for f in FACTIONS}}

    setup = {"map": settings["map"], "difficulty": settings["difficulty"], "slot": settings["slot"],
             "notice": "", "text_scale": settings["text_scale"]}
    setup.update(title_state())

    game = None  # None means we are on the title screen, watching the demo
    briefing = None  # The faction whose opening story card is showing, before the run starts
    speed_index = 0
    hover = None
    running = True
    confirm_quit = False  # Esc asks first, so a stray key press does not lose a run
    show_help = False  # F1
    show_log = False  # L: the story log
    paused = False  # P

    while running:
        dt = min(clock.tick(FPS) / 1000, 0.05)  # Clamp so a stalled window does not skip the simulation ahead
        window = pygame.display.get_surface()
        dest = fit(*window.get_size(), SCREEN_WIDTH, SCREEN_HEIGHT)
        pointer = to_canvas(pygame.mouse.get_pos(), dest, SCREEN_WIDTH, SCREEN_HEIGHT)
        frozen = confirm_quit or show_help or show_log or paused

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                settings["fullscreen"] = not settings["fullscreen"]
                window = open_window(settings["fullscreen"])
                persist()
            elif confirm_quit:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        running = False
                    elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                        confirm_quit = False
            elif show_help:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_F1, pygame.K_ESCAPE):
                    show_help = False
            elif show_log:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_l, pygame.K_ESCAPE):
                    show_log = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                sounds.toggle_mute()  # M works everywhere
                persist()
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                sounds.change_level(-VOLUME_STEP)
                persist()
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                sounds.change_level(VOLUME_STEP)
                persist()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                names = list(TEXT_SCALES)
                settings["text_scale"] = names[(names.index(settings["text_scale"]) + 1) % len(names)]
                setup["text_scale"] = settings["text_scale"]
                fonts = make_fonts(TEXT_SCALES[settings["text_scale"]])
                persist()
            elif game is None and briefing is not None:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        game = Game(briefing, map_index=setup["map"], difficulty=setup["difficulty"])
                        game.slot = setup["slot"]
                        briefing = None
                    elif event.key == pygame.K_d:
                        settings["skip_briefing"] = not settings["skip_briefing"]
                        persist()
                    elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        briefing = None
            elif game is None:
                if event.type == pygame.KEYDOWN:
                    setup["notice"] = ""
                    if event.key in (pygame.K_h, pygame.K_z):
                        faction = "human" if event.key == pygame.K_h else "zombie"
                        if settings["skip_briefing"]:
                            game = Game(faction, map_index=setup["map"], difficulty=setup["difficulty"])
                            game.slot = setup["slot"]
                        else:
                            briefing = faction
                    elif event.key in SLOT_KEYS:
                        setup["slot"] = SLOT_KEYS[event.key]
                        persist()
                    elif event.key == pygame.K_LEFT:
                        setup["map"] = (setup["map"] - 1) % MAP_CHOICES
                        persist()
                    elif event.key == pygame.K_RIGHT:
                        setup["map"] = (setup["map"] + 1) % MAP_CHOICES
                        persist()
                    elif event.key == pygame.K_d:
                        names = list(DIFFICULTIES)
                        setup["difficulty"] = names[(names.index(setup["difficulty"]) + 1) % len(names)]
                        setup.update(title_state())
                        persist()
                    elif event.key == pygame.K_c:
                        loaded, reason = Game.load_slot(save_path(setup["slot"]))
                        if loaded is not None:
                            loaded.slot = setup["slot"]
                            game = loaded
                        else:
                            setup["notice"] = SAVE_NOTICES.get(reason, "")
                    elif event.key == pygame.K_a:
                        loaded, reason = Game.load_slot(autosave_path())
                        if loaded is not None:
                            game = loaded
                        else:
                            setup["notice"] = SAVE_NOTICES.get(reason, "There is no autosave yet")
                    elif event.key == pygame.K_ESCAPE:
                        confirm_quit = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL:
                game.undo()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    confirm_quit = True
                elif event.key == pygame.K_F1:
                    show_help = True
                elif event.key == pygame.K_l:
                    show_log = True
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key in ROLE_KEYS:
                    game.selected = ROLE_KEYS[event.key]
                    game.selected_unit = None
                elif event.key == pygame.K_SPACE:
                    if not game.start_wave():
                        game.toggle_rush()
                elif event.key == pygame.K_F5:
                    game.save(save_path(game.slot))
                elif event.key == pygame.K_f:
                    speed_index = (speed_index + 1) % len(SPEEDS)
                elif event.key == pygame.K_u:
                    game.upgrade()
                elif event.key == pygame.K_g:
                    game.reinforce()
                elif event.key == pygame.K_a:
                    game.choose_ultimate(0)
                elif event.key == pygame.K_b:
                    game.choose_ultimate(1)
                elif event.key == pygame.K_x:
                    game.sell()
                elif event.key == pygame.K_r and game.status != "playing":
                    game = None
                    setup.update(title_state())
            elif event.type == pygame.MOUSEMOTION:
                hover = camera.screen_to_tile(*to_canvas(event.pos, dest, SCREEN_WIDTH, SCREEN_HEIGHT))
            elif event.type == pygame.MOUSEBUTTONDOWN and frozen:
                pass  # Clicks do nothing while paused, in help, the log or at the quit prompt
            elif event.type == pygame.MOUSEBUTTONDOWN:
                point = to_canvas(event.pos, dest, SCREEN_WIDTH, SCREEN_HEIGHT)
                if event.button == 3:
                    game.deselect()
                elif event.button == 1:
                    action = ui_action(point, game)
                    if action is not None:
                        handle_action(game, action)
                    else:
                        cell = camera.screen_to_tile(*point)
                        if cell is None:
                            game.deselect()
                        else:
                            game.click_cell(*cell)

        if game is None:
            demo.update(dt)
            demo.game.drain_sounds()  # The demo battle is silent
            scene = draw_scene(camera, demo.game, None)
            pygame.transform.scale(scene, (SCREEN_WIDTH, SCREEN_HEIGHT), canvas)
            if briefing is not None:
                draw_briefing(canvas, fonts, briefing, settings["skip_briefing"])
            else:
                draw_title(canvas, fonts, setup)
        else:
            speed = SPEEDS[speed_index]
            if not frozen:  # The battle stops while a menu, the help, the log or the quit prompt is up
                was_active = game.wave_active
                game.update(dt * speed)
                if was_active and not game.wave_active and game.status == "playing":
                    game.save(autosave_path())  # Every cleared round is an autosave
                if game.status == "lost" and game is not logged_game:
                    logged_game = game
                    if record_round(records, game.faction, game.difficulty, game.wave):
                        save_records(records)
            for event in game.drain_sounds():
                sounds.play_event(event)
            scene = draw_scene(camera, game, hover)
            pygame.transform.scale(scene, (SCREEN_WIDTH, SCREEN_HEIGHT), canvas)
            draw_hud(canvas, game, speed, fonts, pointer, sounds.status_text())
            if show_help:
                draw_help(canvas, fonts)
            elif show_log:
                draw_log(canvas, fonts, game.story_log)
            elif paused:
                draw_pause(canvas, fonts, game)

        if confirm_quit:
            draw_quit_prompt(canvas, fonts)
        window.fill((0, 0, 0))
        window.blit(pygame.transform.scale(canvas, (dest[2], dest[3])), dest[:2])
        pygame.display.flip()

    persist()
    pygame.quit()


if __name__ == "__main__":
    main()
