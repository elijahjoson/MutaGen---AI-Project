"""Combat HUD — Purge Code upload bar, wave number, enemy count, SA temp."""
import pygame
import math
from src.core.constants import SCREEN_W, SCREEN_H
from src.ui import font_manager as fm
from src.ui.ui_helpers import (
    draw_pill_bar, draw_panel, draw_scanlines,
    brighten, dim, with_alpha, lerp_color, pulse_color,
)


class HUDState:
    def __init__(self, player_hp, player_max_hp, upload_pct, wave_n,
                 enemies_remaining, sa_temperature):
        self.player_hp = player_hp
        self.player_max_hp = player_max_hp
        self.upload_pct = upload_pct
        self.wave_n = wave_n
        self.enemies_remaining = enemies_remaining
        self.sa_temperature = sa_temperature


# ── Smooth animation state (module-level for persistence) ─────────────────────
_anim_upload = 0.0
_time = 0.0


def draw_hud(screen: pygame.Surface, state: HUDState, font: pygame.font.Font,
             dt: float = 1/60) -> None:
    global _anim_upload, _time
    _time += dt

    # Smooth upload bar animation
    _anim_upload += (state.upload_pct - _anim_upload) * min(1.0, 4.0 * dt)

    _draw_purge_bar(screen, state, _anim_upload)
    _draw_wave_panel(screen, state)


# ── Purge Code Upload Bar ─────────────────────────────────────────────────────

def _draw_purge_bar(screen: pygame.Surface, state: HUDState,
                    anim_pct: float) -> None:
    bar_w = 340
    bar_h = 18
    bar_x = SCREEN_W // 2 - bar_w // 2
    bar_y = 20

    # Panel behind bar
    panel_rect = pygame.Rect(bar_x - 16, bar_y - 10, bar_w + 32, bar_h + 42)
    draw_panel(screen, panel_rect,
               border_color=(40, 80, 60),
               bg_color=(6, 10, 18, 200),
               border_radius=8)
    draw_scanlines(screen, panel_rect, alpha=8, spacing=4)

    ratio = anim_pct / 100.0

    # Bar color — transitions from green to bright cyan near completion
    if ratio < 0.7:
        fg = (45, 200, 90)
    elif ratio < 0.9:
        fg = lerp_color((45, 200, 90), (80, 255, 200), (ratio - 0.7) / 0.2)
    else:
        # Pulsing near completion
        pulse = 0.7 + 0.3 * math.sin(_time * 6.0)
        fg = lerp_color((80, 255, 200), (200, 255, 240),
                        pulse)

    glow = fg if ratio > 0.8 else None

    draw_pill_bar(screen, bar_x, bar_y, bar_w, bar_h,
                  ratio, fg, bg_color=(18, 28, 22),
                  glow_color=glow,
                  border_color=(40, 80, 60))

    # Shimmer sweep effect
    if ratio > 0:
        shimmer_x = int(bar_x + ((_time * 80) % (bar_w + 40)) - 20)
        shimmer_w = 30
        if shimmer_x < bar_x + int(bar_w * ratio):
            shimmer_surf = pygame.Surface((shimmer_w, bar_h), pygame.SRCALPHA)
            for sx in range(shimmer_w):
                frac = sx / shimmer_w
                a = int(40 * math.sin(frac * math.pi))
                pygame.draw.line(shimmer_surf, (255, 255, 255, a),
                                 (sx, 0), (sx, bar_h))
            screen.blit(shimmer_surf, (shimmer_x, bar_y))

    # Label
    label_color = (180, 255, 200) if ratio < 0.9 else (255, 255, 240)
    upload_font = fm.hud()
    label = upload_font.render(
        f"PURGE CODE UPLOAD  {state.upload_pct:.0f}%", True, label_color
    )
    screen.blit(label, label.get_rect(center=(SCREEN_W // 2, bar_y + bar_h + 16)))

    # Completion flash
    if state.upload_pct >= 100.0:
        flash_alpha = int(80 * abs(math.sin(_time * 4.0)))
        flash = pygame.Surface((bar_w + 32, bar_h + 42), pygame.SRCALPHA)
        flash.fill((200, 255, 220, flash_alpha))
        screen.blit(flash, (bar_x - 16, bar_y - 10))


# ── Wave Panel (top-right) ────────────────────────────────────────────────────

def _draw_wave_panel(screen: pygame.Surface, state: HUDState) -> None:
    panel_w = 220
    panel_h = 110
    panel_x = SCREEN_W - panel_w - 16
    panel_y = 12

    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    draw_panel(screen, panel_rect,
               border_color=(60, 40, 50),
               bg_color=(8, 10, 18, 200),
               border_radius=8)
    draw_scanlines(screen, panel_rect, alpha=6)

    # "WAVE" label
    wave_label = fm.tiny().render("WAVE", True, (140, 100, 100))
    screen.blit(wave_label, (panel_x + 12, panel_y + 10))

    # Wave number — large, right-aligned
    pulse = 0.8 + 0.2 * math.sin(_time * 1.5)
    wave_color = pulse_color((255, 130, 130), pulse)
    wave_num = fm.header().render(str(state.wave_n), True, wave_color)
    screen.blit(wave_num, (panel_x + panel_w - wave_num.get_width() - 14,
                           panel_y + 6))

    # Divider
    div_y = panel_y + 32
    pygame.draw.line(screen, (40, 35, 45),
                     (panel_x + 8, div_y), (panel_x + panel_w - 8, div_y), 1)

    # Enemies remaining
    enemy_color = (200, 200, 200) if state.enemies_remaining > 0 else (100, 200, 120)
    enemies_surf = fm.tiny().render(
        f"{state.enemies_remaining} ENEMIES", True, enemy_color
    )
    screen.blit(enemies_surf, (panel_x + 12, div_y + 8))

    # SA Temperature micro-bar
    temp_label = fm.tiny().render("SA TEMP", True, (100, 140, 160))
    temp_y = div_y + 24
    screen.blit(temp_label, (panel_x + 12, temp_y))

    # Position bar right after label with a gap
    temp_bar_x = panel_x + 12 + temp_label.get_width() + 8
    temp_bar_w = panel_w - (temp_label.get_width() + 32)
    temp_ratio = max(0.0, min(1.0, state.sa_temperature))

    # Color: blue (cold/low) → red (hot/high)
    temp_color = lerp_color((60, 160, 255), (255, 80, 60), temp_ratio)
    draw_pill_bar(screen, temp_bar_x, temp_y + 1, temp_bar_w, 8,
                  temp_ratio, temp_color, bg_color=(20, 25, 35),
                  border_color=(40, 50, 60))