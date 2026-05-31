"""Entry point for Mutagen Arena."""
import pygame
import sys

# Import constants to set up the game window
from src.core.constants import SCREEN_W, SCREEN_H, FPS
from src.systems.controller import GameController

def main():
    # 1. Turn on the Pygame Engine
    pygame.init()
    pygame.font.init()

    # 2. Create the exact screen and clock that controller.py is asking for
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Mutagen Arena: Project Sentinel")
    clock = pygame.time.Clock()

    # 3. Boot up the brain of the game
    controller = GameController()

    # 4. The Core Game Loop
    while controller.running:
        # Calculate delta time (dt) so the game runs at the same speed on all computers
        dt = clock.tick(FPS) / 1000.0
        
        # Capture mouse clicks and keyboard presses
        events = pygame.event.get()

        # Feed the events, screen, and clock directly into the controller
        controller.handle_events(events)
        controller.update(dt, events, screen=screen, clock=clock)
        
        # Draw everything to the screen
        if controller.running:
            controller.render(screen)
            pygame.display.flip()

    # 5. Shut down cleanly when the player closes the window
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()