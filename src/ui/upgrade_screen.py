"""Upgrade screen shown at the end of intermission.

Premium version with glassmorphism cards, hover glow, stat icons,
animated selection, and styled title.
"""
import pygame
import math
import random
from src.core.constants import SCREEN_W, SCREEN_H, UPGRADES, FPS
from src.ui import font_manager as fm
from src.ui.ui_helpers import (
    draw_panel, draw_scanlines, draw_vignette,
    draw_pill_bar, lerp_color, brighten, dim, with_alpha,
    draw_stat_icon, STAT_COLORS, ParticleSystem, pulse_color,
)


class UpgradeScreen:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        # FIXED ISSUE 9: Reads directly from constants.py
        self.choices = random.sample(UPGRADES, min(3, len(UPGRADES)))

        self.card_width, self.card_height, self.gap = 340, 380, 24
        self.start_x = (SCREEN_W - (3 * self.card_width + 2 * self.gap)) // 2
        self.cards_y = 160

        # Animation state
        self._time = 0.0
        self._selected_flash: int = -1
        self._flash_timer: float = 0.0
        self._particles = ParticleSystem(count=20, bounds=(SCREEN_W, SCREEN_H),
                                         color=(80, 200, 120))
        self._fade_in = 255

    def run(self):
        """
        Blocks until player selects an upgrade.
        Returns the selected upgrade dict, or None if player quit.

        IMPORTANT: Caller must pass the returned upgrade to player.apply_upgrade(upgrade)
        — this screen does not apply the upgrade itself!
        """
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self._time += dt
            self._particles.update(dt)

            # Fade in
            if self._fade_in > 0:
                self._fade_in = max(0, self._fade_in - int(500 * dt))

            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, upgrade in enumerate(self.choices):
                        rect = pygame.Rect(
                            self.start_x + i * (self.card_width + self.gap),
                            self.cards_y, self.card_width, self.card_height
                        )
                        if rect.collidepoint(mouse_pos):
                            return upgrade
                # Number keys 1-3
                if event.type == pygame.KEYDOWN:
                    key_map = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
                    if event.key in key_map:
                        idx = key_map[event.key]
                        if idx < len(self.choices):
                            return self.choices[idx]

            self._draw(mouse_pos)
            pygame.display.flip()

    def _draw(self, mouse_pos):
        # Background
        self.screen.fill((6, 10, 20))

        # Gradient overlay
        for y_band in range(0, SCREEN_H, 4):
            frac = y_band / SCREEN_H
            r = int(6 + 8 * frac)
            g = int(10 + 8 * frac)
            b = int(20 + 12 * frac)
            pygame.draw.rect(self.screen, (r, g, b),
                             (0, y_band, SCREEN_W, 4))

        # Particles
        self._particles.draw(self.screen)

        # Scanlines
        draw_scanlines(self.screen, alpha=5)

        # Vignette
        draw_vignette(self.screen, intensity=60)

        # ── Title ─────────────────────────────────────────────────────────
        pulse = 0.7 + 0.3 * math.sin(self._time * 2.0)
        title_color = pulse_color((80, 255, 120), pulse)
        title_font = fm.title()
        title = title_font.render("EVOLUTION COMPLETE", True, title_color)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 55)))

        # Subtitle
        sub = fm.body().render("Choose your upgrade", True, (160, 170, 180))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 100)))

        # Decorative divider
        div_w = 400
        div_x = SCREEN_W // 2 - div_w // 2
        div_y = 125
        line_alpha = int(50 * pulse)
        div_surf = pygame.Surface((div_w, 1), pygame.SRCALPHA)
        div_surf.fill((*title_color, line_alpha))
        self.screen.blit(div_surf, (div_x, div_y))

        # DNA helix decoration
        self._draw_dna_helix(div_x - 30, div_y - 20, 40)
        self._draw_dna_helix(div_x + div_w - 10, div_y - 20, 40)

        # ── Cards ─────────────────────────────────────────────────────────
        for i, upgrade in enumerate(self.choices):
            x = self.start_x + i * (self.card_width + self.gap)
            rect = pygame.Rect(x, self.cards_y, self.card_width, self.card_height)
            hover = rect.collidepoint(mouse_pos)
            self._draw_card(x, self.cards_y, upgrade, hover, i)

        # ── Hint ──────────────────────────────────────────────────────────
        hint = fm.tiny().render("Click a card or press [1] [2] [3] to select",
                                True, (60, 70, 90))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2, SCREEN_H - 30)))

        # Fade in
        if self._fade_in > 0:
            fade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            fade.fill((0, 0, 0, self._fade_in))
            self.screen.blit(fade, (0, 0))

    def _draw_card(self, x, y, upgrade, hover, index):
        w, h = self.card_width, self.card_height
        stat = upgrade["stat"]
        stat_color = STAT_COLORS.get(stat, (140, 180, 200))

        # Lift effect on hover
        lift = 8 if hover else 0
        y -= lift

        # Background
        if hover:
            bg = (14, 28, 22, 235)
            border = brighten(stat_color, 1.2)
            bw = 2
        else:
            bg = (10, 16, 26, 210)
            border = dim(stat_color, 0.4)
            bw = 1

        card_rect = pygame.Rect(x, y, w, h)
        draw_panel(self.screen, card_rect, border_color=border,
                   bg_color=bg, border_width=bw, border_radius=10)

        # Hover glow
        if hover:
            glow = pygame.Surface((w + 16, h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*stat_color[:3], 18),
                             pygame.Rect(0, 0, w + 16, h + 16),
                             border_radius=14)
            self.screen.blit(glow, (x - 8, y - 8))

        # Top accent stripe
        accent = pygame.Surface((w - 2, 3), pygame.SRCALPHA)
        accent.fill((*stat_color[:3], 160 if hover else 80))
        self.screen.blit(accent, (x + 1, y + 1))

        # Stat icon (large, centered in top area — drawn with pygame shapes)
        icon_color = stat_color if hover else dim(stat_color, 0.6)
        draw_stat_icon(self.screen, x + w // 2, y + 80, 48, stat, icon_color)

        # Divider
        div_y = y + 130
        pygame.draw.line(self.screen, dim(stat_color, 0.3),
                         (x + 16, div_y), (x + w - 16, div_y), 1)

        # Upgrade name
        name_font = fm.header()
        name_color = (255, 255, 255) if hover else (200, 200, 210)
        name_surf = name_font.render(upgrade["name"], True, name_color)
        self.screen.blit(name_surf,
                         name_surf.get_rect(center=(x + w // 2, div_y + 30)))

        # Description
        desc_font = fm.small()
        desc_color = (170, 175, 185) if hover else (120, 125, 135)
        desc_surf = desc_font.render(upgrade["desc"], True, desc_color)
        self.screen.blit(desc_surf,
                         desc_surf.get_rect(center=(x + w // 2, div_y + 65)))

        # Stat type badge
        badge_text = f"Affects: {upgrade['stat'].upper()}"
        badge_font = fm.tiny()
        badge_surf = badge_font.render(badge_text, True, stat_color)
        badge_rect = badge_surf.get_rect(center=(x + w // 2, div_y + 95))

        # Badge background
        badge_bg = pygame.Rect(badge_rect.x - 8, badge_rect.y - 3,
                               badge_rect.w + 16, badge_rect.h + 6)
        draw_panel(self.screen, badge_bg,
                   border_color=dim(stat_color, 0.4),
                   bg_color=(12, 18, 28, 180),
                   border_radius=4)
        self.screen.blit(badge_surf, badge_rect)

        # Key hint (bottom)
        key_surf = fm.tiny().render(f"[{index + 1}]", True, (60, 70, 85))
        self.screen.blit(key_surf,
                         key_surf.get_rect(center=(x + w // 2, y + h - 20)))

        # "SELECT" hover prompt
        if hover:
            pulse = 0.6 + 0.4 * math.sin(self._time * 4.0)
            sel_color = pulse_color(stat_color[:3], pulse)
            sel_surf = fm.small().render("▶ SELECT ◀", True, sel_color)
            self.screen.blit(sel_surf,
                             sel_surf.get_rect(center=(x + w // 2, y + h - 45)))

    def _draw_dna_helix(self, x, y, height):
        """Draw a small decorative DNA helix."""
        for i in range(0, height, 3):
            t = (i / height) * math.pi * 2 + self._time * 3
            x1 = x + int(10 * math.sin(t))
            x2 = x + int(10 * math.sin(t + math.pi))
            yi = y + i
            alpha = int(60 + 40 * abs(math.sin(t)))
            c1 = (80, 255, 120, alpha)
            c2 = (120, 200, 255, alpha)
            ps1 = pygame.Surface((4, 4), pygame.SRCALPHA)
            ps2 = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(ps1, c1, (2, 2), 2)
            pygame.draw.circle(ps2, c2, (2, 2), 2)
            self.screen.blit(ps1, (x1 - 2, yi - 2))
            self.screen.blit(ps2, (x2 - 2, yi - 2))