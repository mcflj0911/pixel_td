"""Start Pixel TD. The screens and their controls live in app.py."""
import pygame

from app import App
from paths import migrate_saves


def main():
    migrate_saves()  # Saves from older versions, kept in the game's folder, move to the user's data folder once
    pygame.mixer.pre_init(22050, -16, 2, 512)  # Matches sounds.SR. Set before init so the format is right
    pygame.init()
    App().run()
    pygame.quit()


if __name__ == "__main__":
    main()
