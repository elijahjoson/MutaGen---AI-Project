"""Upgrade screen shown at the end of intermission."""
import pygame
import random
from src.core.constants import SCREEN_W, SCREEN_H, UPGRADES, FPS

class UpgradeScreen:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        # FIXED ISSUE 9: Reads directly from constants.py
        self.choices = random.sample(UPGRADES, min(3, len(UPGRADES)))
        
        self.card_width, self.card_height, self.gap = 250, 350, 40
        self.start_x = (SCREEN_W - (3 * self.card_width + 2 * self.gap)) // 2
        
        pygame.font.init()
        self.f_title = pygame.font.SysFont("consolas", 36, bold=True)
        self.f_name = pygame.font.SysFont("consolas", 20, bold=True)
        self.f_desc = pygame.font.SysFont("consolas", 14)

    def run(self):
        """
        Blocks until player selects an upgrade.
        Returns the selected upgrade dict, or None if player quit.
        
        IMPORTANT: Caller must pass the returned upgrade to player.apply_upgrade(upgrade)
        — this screen does not apply the upgrade itself!
        """
        while True:
            self.clock.tick(FPS)
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, upgrade in enumerate(self.choices):
                        rect = pygame.Rect(self.start_x + i * (self.card_width + self.gap), 200, self.card_width, self.card_height)
                        if rect.collidepoint(mouse_pos): return upgrade
            
            self._draw(mouse_pos)
            pygame.display.flip()

    def _draw(self, mouse_pos):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 230))
        self.screen.blit(overlay, (0, 0))
        
        title = self.f_title.render("EVOLUTION COMPLETE - CHOOSE UPGRADE", True, (127, 255, 127))
        self.screen.blit(title, title.get_rect(center=(SCREEN_W//2, 80)))

        for i, upgrade in enumerate(self.choices):
            x = self.start_x + i * (self.card_width + self.gap)
            rect = pygame.Rect(x, 200, self.card_width, self.card_height)
            hover = rect.collidepoint(mouse_pos)
            color, bg_color = ((255, 201, 127), (25, 35, 55)) if hover else ((140, 140, 140), (15, 20, 30))
            
            pygame.draw.rect(self.screen, bg_color, rect, border_radius=10)
            pygame.draw.rect(self.screen, color, rect, 3, border_radius=10)
            
            self.screen.blit(self.f_name.render(upgrade["name"], True, (255, 255, 255)), (x + 20, 220))
            self.screen.blit(self.f_desc.render(upgrade["desc"], True, (180, 180, 180)), (x + 20, 280))
            self.screen.blit(self.f_desc.render(f"Affects: {upgrade['stat']}", True, (255, 201, 127)), (x + 20, 310))