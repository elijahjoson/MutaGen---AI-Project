"""Combat HUD — HP, Purge Code upload %, wave number."""
import pygame
from src.core.constants import SCREEN_W

class HUDState:
    def __init__(self, player_hp, player_max_hp, upload_pct, wave_n, enemies_remaining, sa_temperature):
        self.player_hp = player_hp
        self.player_max_hp = player_max_hp
        self.upload_pct = upload_pct
        self.wave_n = wave_n
        self.enemies_remaining = enemies_remaining
        self.sa_temperature = sa_temperature

def _draw_bar(screen, x, y, w, h, frac, color_fg, color_bg=(40, 40, 50)):
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(screen, color_bg, (x, y, w, h))
    if frac > 0:
        pygame.draw.rect(screen, color_fg, (x, y, int(w * frac), h))

def draw_hud(screen: pygame.Surface, state: HUDState, font: pygame.font.Font) -> None:
    # Top-center: Purge Code upload
    bar_w = 280
    bar_x = SCREEN_W // 2 - bar_w // 2
    _draw_bar(screen, bar_x, 24, bar_w, 14, state.upload_pct / 100.0, color_fg=(255, 201, 127))
    upload_text = font.render(f"PURGE CODE UPLOAD  {state.upload_pct:.0f}%", True, (220, 220, 220))
    screen.blit(upload_text, upload_text.get_rect(center=(SCREEN_W // 2, 52)))

    # Top-right: wave + enemies remaining
    wave_text = font.render(f"WAVE {state.wave_n}", True, (255, 127, 127))
    screen.blit(wave_text, wave_text.get_rect(topright=(SCREEN_W - 24, 24)))

    rem_text = font.render(f"{state.enemies_remaining} ENEMIES REMAIN", True, (200, 200, 200))
    screen.blit(rem_text, rem_text.get_rect(topright=(SCREEN_W - 24, 46)))

    # SA Temperature Display
    temp_text = font.render(f"SA TEMP: {state.sa_temperature:.2f}", True, (127, 255, 255))
    screen.blit(temp_text, temp_text.get_rect(topright=(SCREEN_W - 24, 68)))