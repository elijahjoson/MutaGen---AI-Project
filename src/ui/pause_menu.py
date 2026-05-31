"""
pause_menu.py — Pause overlay for MutaGen Arena combat.

Renders a semi-transparent overlay on top of the frozen game with
Resume / Restart / Quit options. Styled with neon button states.
"""
import pygame
import math
from src.core.constants import SCREEN_W, SCREEN_H
from src.ui import font_manager as fm
from src.ui.ui_helpers import (
    draw_panel, draw_scanlines, draw_vignette,
    brighten, dim, with_alpha, pulse_color,
)


class PauseMenu:
    """
    Drawn on top of a frozen combat frame.
    Returns an action string: 'resume', 'restart', 'quit', or None (still paused).
    """

    OPTIONS = [
        ("RESUME",          "resume",  pygame.K_SPACE),
        ("RESTART RUN",     "restart", pygame.K_r),
        ("QUIT TO TITLE",   "quit",    pygame.K_q),
    ]

    BTN_W   = 320
    BTN_H   = 50
    BTN_GAP = 16

    def __init__(self):
        self._hover_idx: int = -1
        self._time: float = 0.0

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Process a single event. Returns action string or None."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "resume"
            for i, (_, action, key) in enumerate(self.OPTIONS):
                if event.key == key:
                    return action

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, (_, action, _) in enumerate(self.OPTIONS):
                rect = self._btn_rect(i)
                if rect.collidepoint(mx, my):
                    return action

        return None

    def draw(self, surf: pygame.Surface) -> None:
        """Render the pause overlay."""
        mouse_pos = pygame.mouse.get_pos()
        self._hover_idx = -1
        for i in range(len(self.OPTIONS)):
            if self._btn_rect(i).collidepoint(*mouse_pos):
                self._hover_idx = i

        # Darken background
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        # Scanlines over entire screen
        draw_scanlines(surf, alpha=8)

        # Title
        pulse = 0.7 + 0.3 * math.sin(self._time * 2.0)
        title_color = pulse_color((100, 220, 180), pulse)
        title_surf = fm.mega().render("PAUSED", True, title_color)
        title_rect = title_surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 120))
        surf.blit(title_surf, title_rect)

        # Divider line
        div_y = SCREEN_H // 2 - 70
        div_alpha = int(80 * pulse)
        div_surf = pygame.Surface((400, 1), pygame.SRCALPHA)
        div_surf.fill((*title_color, div_alpha))
        surf.blit(div_surf, (SCREEN_W // 2 - 200, div_y))

        # Buttons
        for i, (label, action, key) in enumerate(self.OPTIONS):
            self._draw_button(surf, i, label, key, mouse_pos)

        # Hint
        hint = fm.tiny().render("ESC to resume", True, (60, 70, 90))
        surf.blit(hint, hint.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 180)))

    def _btn_rect(self, index: int) -> pygame.Rect:
        total_h = len(self.OPTIONS) * self.BTN_H + (len(self.OPTIONS) - 1) * self.BTN_GAP
        start_y = SCREEN_H // 2 - total_h // 2 + 20
        x = SCREEN_W // 2 - self.BTN_W // 2
        y = start_y + index * (self.BTN_H + self.BTN_GAP)
        return pygame.Rect(x, y, self.BTN_W, self.BTN_H)

    def _draw_button(self, surf: pygame.Surface, index: int,
                     label: str, key: int, mouse_pos: tuple) -> None:
        rect = self._btn_rect(index)
        hovered = (index == self._hover_idx)

        # Colors
        if hovered:
            bg = (20, 45, 35, 230)
            border = (100, 255, 180)
            text_c = (255, 255, 255)
            lift = 2
        else:
            bg = (10, 18, 28, 200)
            border = (50, 70, 90)
            text_c = (160, 170, 190)
            lift = 0

        draw_rect = pygame.Rect(rect.x, rect.y - lift, rect.w, rect.h)

        # Panel
        draw_panel(surf, draw_rect, border_color=border, bg_color=bg,
                   border_width=2 if hovered else 1, border_radius=8)

        # Glow on hover
        if hovered:
            glow = pygame.Surface((rect.w + 12, rect.h + 12), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*border[:3], 20),
                             pygame.Rect(0, 0, rect.w + 12, rect.h + 12),
                             border_radius=12)
            surf.blit(glow, (draw_rect.x - 6, draw_rect.y - 6))

        # Label
        label_surf = fm.body().render(label, True, text_c)
        label_rect = label_surf.get_rect(center=draw_rect.center)
        surf.blit(label_surf, label_rect)

        # Key hint (right side)
        key_name = pygame.key.name(key).upper()
        key_surf = fm.tiny().render(f"[{key_name}]", True, (80, 90, 110))
        surf.blit(key_surf, (draw_rect.right - key_surf.get_width() - 12,
                             draw_rect.centery - key_surf.get_height() // 2))
