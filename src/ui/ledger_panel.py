"""Intermission screen — renders the Evolutionary Ledger for the player.

Premium version with animated panels, particle effects, archetype cards,
gene change bars, SA temperature gauge, and countdown ring.
"""
import pygame
import math
from src.ai.chromosome import Archetype
from src.core.constants import SCREEN_W, SCREEN_H
from src.ui import font_manager as fm
from src.ui.ui_helpers import (
    draw_panel, draw_scanlines, draw_vignette,
    draw_pill_bar, lerp_color, brighten, dim, with_alpha,
    ParticleSystem, pulse_color,
)

INTERMISSION_AUTO_ADVANCE_SEC = 15.0

COLOR_INCREASE = (80, 255, 140)
COLOR_DECREASE = (255, 100, 100)
COLOR_STABLE   = (100, 110, 130)

# Archetype accent colors
_ARCH_COLORS = {
    Archetype.TANK:    (100, 160, 255),
    Archetype.STRIKER: (255, 180, 60),
    Archetype.RANGED:  (80, 200, 255),
    Archetype.SUPPORT: (200, 130, 255),
}

# Module-level state for animations
_particles: ParticleSystem | None = None
_fade_alpha = 255
_anim_time = 0.0


def _reset_anim() -> None:
    global _particles, _fade_alpha, _anim_time
    _particles = ParticleSystem(count=35, bounds=(SCREEN_W, SCREEN_H),
                                color=(40, 100, 80))
    _fade_alpha = 255
    _anim_time = 0.0


def draw_ledger(
    screen: pygame.Surface, ledger: dict, wave_finished: int,
    sa_temperature: float, elapsed_in_intermission: float,
    title_font: pygame.font.Font, header_font: pygame.font.Font,
    body_font: pygame.font.Font,
) -> None:
    global _particles, _fade_alpha, _anim_time

    dt = 1 / 60  # approximate dt
    _anim_time += dt

    # Initialize particles on first call
    if _particles is None:
        _reset_anim()

    # Fade in
    if _fade_alpha > 0:
        _fade_alpha = max(0, _fade_alpha - int(400 * dt))

    _particles.update(dt)

    # ── Background ────────────────────────────────────────────────────────
    # Gradient fill
    for y_band in range(0, SCREEN_H, 4):
        frac = y_band / SCREEN_H
        r = int(8 + 4 * frac)
        g = int(12 + 6 * frac)
        b = int(24 + 10 * frac)
        pygame.draw.rect(screen, (r, g, b),
                         (0, y_band, SCREEN_W, 4))

    # Particles
    _particles.draw(screen)

    # Scanlines
    draw_scanlines(screen, alpha=6, spacing=3)

    # Vignette
    draw_vignette(screen, intensity=80)

    # ── Title Banner ──────────────────────────────────────────────────────
    # "INTERMISSION" subtitle
    inter_font = fm.header()
    pulse = 0.6 + 0.4 * math.sin(_anim_time * 2.0)
    inter_color = pulse_color((100, 160, 255), pulse)
    inter_surf = inter_font.render("INTERMISSION", True, inter_color)
    screen.blit(inter_surf,
                inter_surf.get_rect(center=(SCREEN_W // 2, 50)))

    # Wave transition
    wave_font = fm.title()
    wave_text = f"WAVE {wave_finished}  →  WAVE {wave_finished + 1}"
    wave_surf = wave_font.render(wave_text, True, (240, 240, 240))
    screen.blit(wave_surf,
                wave_surf.get_rect(center=(SCREEN_W // 2, 95)))

    # Decorative divider
    div_y = 130
    div_w = 500
    div_x = SCREEN_W // 2 - div_w // 2
    line_alpha = int(60 * pulse)
    div_surf = pygame.Surface((div_w, 1), pygame.SRCALPHA)
    div_surf.fill((*inter_color, line_alpha))
    screen.blit(div_surf, (div_x, div_y))
    # Corner accents
    acc_len = 12
    pygame.draw.line(screen, inter_color,
                     (div_x, div_y), (div_x + acc_len, div_y), 2)
    pygame.draw.line(screen, inter_color,
                     (div_x + div_w - acc_len, div_y),
                     (div_x + div_w, div_y), 2)

    # ── Archetype Cards ───────────────────────────────────────────────────
    archetypes = list(Archetype)
    card_w = 260
    card_gap = 20
    total_cards_w = len(archetypes) * card_w + (len(archetypes) - 1) * card_gap
    cards_start_x = (SCREEN_W - total_cards_w) // 2
    card_y = 155
    card_h = 360

    for i, archetype in enumerate(archetypes):
        x = cards_start_x + i * (card_w + card_gap)
        accent = _ARCH_COLORS.get(archetype, (140, 140, 140))

        # Card panel
        card_rect = pygame.Rect(x, card_y, card_w, card_h)
        draw_panel(screen, card_rect,
                   border_color=dim(accent, 0.5),
                   bg_color=(8, 12, 22, 210),
                   border_width=1, border_radius=8)

        # Top accent bar
        accent_bar = pygame.Surface((card_w - 2, 3), pygame.SRCALPHA)
        accent_bar.fill((*accent[:3], 140))
        screen.blit(accent_bar, (x + 1, card_y + 1))

        # Archetype name
        arch_font = fm.header()
        arch_name = archetype.value.upper()
        name_surf = arch_font.render(arch_name, True, accent)
        screen.blit(name_surf, (x + 14, card_y + 16))

        # Divider line inside card
        inner_div_y = card_y + 48
        pygame.draw.line(screen, dim(accent, 0.3),
                         (x + 10, inner_div_y), (x + card_w - 10, inner_div_y), 1)

        # Gene change entries
        entries = ledger.get(archetype, [])
        entry_y = card_y + 60

        if not entries:
            stable_surf = fm.small().render("No significant change", True,
                                            COLOR_STABLE)
            screen.blit(stable_surf, (x + 14, entry_y))
        else:
            for j, (gene, pct) in enumerate(entries):
                if j >= 8:  # max displayed
                    break
                _draw_gene_entry(screen, x + 14, entry_y + j * 36,
                                 card_w - 28, gene, pct, accent)

    # ── SA Temperature Gauge ──────────────────────────────────────────────
    _draw_sa_gauge(screen, sa_temperature)

    # ── Bottom Prompt + Countdown ─────────────────────────────────────────
    remaining = max(0.0, INTERMISSION_AUTO_ADVANCE_SEC - elapsed_in_intermission)
    _draw_countdown(screen, remaining, elapsed_in_intermission)

    # ── Fade In Overlay ───────────────────────────────────────────────────
    if _fade_alpha > 0:
        fade_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        fade_surf.fill((0, 0, 0, _fade_alpha))
        screen.blit(fade_surf, (0, 0))


def _draw_gene_entry(screen, x, y, w, gene: str, pct: float,
                     accent: tuple) -> None:
    """Draw a single gene change entry with arrow and bar."""
    increasing = pct > 0

    # Arrow icon
    arrow = "▲" if increasing else "▼"
    arrow_color = COLOR_INCREASE if increasing else COLOR_DECREASE
    arrow_surf = fm.small().render(arrow, True, arrow_color)
    screen.blit(arrow_surf, (x, y + 2))

    # Gene name
    gene_surf = fm.small().render(gene.upper(), True, (200, 200, 210))
    screen.blit(gene_surf, (x + 18, y + 2))

    # Percentage
    pct_text = f"{'+' if pct > 0 else ''}{pct:.0f}%"
    pct_color = COLOR_INCREASE if increasing else COLOR_DECREASE
    pct_surf = fm.small().render(pct_text, True, pct_color)
    screen.blit(pct_surf, (x + w - pct_surf.get_width(), y + 2))

    # Mini change bar
    bar_y = y + 20
    bar_w = w
    bar_h = 6
    ratio = min(1.0, abs(pct) / 50.0)  # normalize to 50% max

    bg = (20, 24, 35)
    fg = COLOR_INCREASE if increasing else COLOR_DECREASE
    draw_pill_bar(screen, x, bar_y, bar_w, bar_h, ratio, fg,
                  bg_color=bg, border_color=(35, 40, 55))


def _draw_sa_gauge(screen, sa_temperature: float) -> None:
    """Draw SA temperature as a small circular gauge in the bottom-left."""
    cx, cy = 60, SCREEN_H - 80
    radius = 32

    # Background circle
    pygame.draw.circle(screen, (15, 20, 30), (cx, cy), radius)
    pygame.draw.circle(screen, (40, 50, 65), (cx, cy), radius, 2)

    # Temperature arc
    temp = max(0.0, min(1.0, sa_temperature))
    temp_color = lerp_color((60, 160, 255), (255, 80, 60), temp)

    # Draw arc segments
    segments = int(temp * 24)
    for seg in range(segments):
        angle = -math.pi / 2 + (seg / 24) * 2 * math.pi
        next_angle = -math.pi / 2 + ((seg + 1) / 24) * 2 * math.pi
        inner_r = radius - 6
        outer_r = radius - 1
        points = [
            (cx + math.cos(angle) * inner_r, cy + math.sin(angle) * inner_r),
            (cx + math.cos(angle) * outer_r, cy + math.sin(angle) * outer_r),
            (cx + math.cos(next_angle) * outer_r, cy + math.sin(next_angle) * outer_r),
            (cx + math.cos(next_angle) * inner_r, cy + math.sin(next_angle) * inner_r),
        ]
        pygame.draw.polygon(screen, temp_color,
                            [(int(px), int(py)) for px, py in points])

    # Center text
    temp_text = f"{temp:.2f}"
    temp_surf = fm.tiny().render(temp_text, True, temp_color)
    screen.blit(temp_surf, temp_surf.get_rect(center=(cx, cy - 4)))

    # Label below
    label = fm.tiny().render("SA TEMP", True, (80, 100, 120))
    screen.blit(label, label.get_rect(center=(cx, cy + 14)))


def _draw_countdown(screen, remaining: float,
                    elapsed: float) -> None:
    """Draw the bottom prompt with countdown ring."""
    cy = SCREEN_H - 45

    # Prompt text
    prompt_font = fm.body()
    prompt_color = (180, 190, 200)
    prompt_surf = prompt_font.render("Press SPACE to continue", True,
                                     prompt_color)
    screen.blit(prompt_surf,
                prompt_surf.get_rect(center=(SCREEN_W // 2, cy)))

    # Countdown ring
    ring_cx = SCREEN_W // 2 + prompt_surf.get_width() // 2 + 30
    ring_cy = cy
    ring_r = 14

    progress = elapsed / INTERMISSION_AUTO_ADVANCE_SEC
    progress = max(0.0, min(1.0, progress))

    # Background ring
    pygame.draw.circle(screen, (25, 30, 40), (ring_cx, ring_cy), ring_r)
    pygame.draw.circle(screen, (50, 60, 75), (ring_cx, ring_cy), ring_r, 2)

    # Progress arc
    segments = int(progress * 20)
    for seg in range(segments):
        angle = -math.pi / 2 + (seg / 20) * 2 * math.pi
        next_angle = -math.pi / 2 + ((seg + 1) / 20) * 2 * math.pi
        inner_r = ring_r - 4
        outer_r = ring_r - 1
        points = [
            (ring_cx + math.cos(angle) * inner_r,
             ring_cy + math.sin(angle) * inner_r),
            (ring_cx + math.cos(angle) * outer_r,
             ring_cy + math.sin(angle) * outer_r),
            (ring_cx + math.cos(next_angle) * outer_r,
             ring_cy + math.sin(next_angle) * outer_r),
            (ring_cx + math.cos(next_angle) * inner_r,
             ring_cy + math.sin(next_angle) * inner_r),
        ]
        ring_color = lerp_color((60, 180, 120), (255, 180, 60), progress)
        pygame.draw.polygon(screen, ring_color,
                            [(int(px), int(py)) for px, py in points])

    # Seconds remaining text
    sec_text = f"{int(remaining)}"
    sec_surf = fm.tiny().render(sec_text, True, (200, 200, 200))
    screen.blit(sec_surf, sec_surf.get_rect(center=(ring_cx, ring_cy)))


def reset_intermission_anim() -> None:
    """Call when entering intermission to reset animation state."""
    _reset_anim()