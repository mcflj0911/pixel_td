"""Start Pixel TD. The screens and their controls live in app.py."""
import pygame

from app import App


def main():
    pygame.mixer.pre_init(22050, -16, 2, 512)  # Matches sounds.SR. Set before init so the format is right
    pygame.init()
    App().run()
    pygame.quit()


if __name__ == "__main__":
    main()
