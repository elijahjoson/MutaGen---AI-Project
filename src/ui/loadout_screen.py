"""
loadout_screen.py - Weapon loadout selection screen.

Shows all 4 available weapons. Player selects up to PLAYER_MAX_LOADOUT (2).
Returns the selected weapon names to the game controller.

"""

import pygame
import math
import sys
from src.core.constants import (
    SCREEN_W, SCREEN_H, FPS,
    WEAPONS, WEAPON_NAMES, PLAYER_MAX_LOADOUT,
    C_BG, C_WHITE, C_GRAY, C_DARK, C_ACCENT, C_DANGER, C_WARN,
    C_PLAYER,
)


# ── Color helpers ────────────────────────────────────────────────────────────

def _sysf(size, bold=False):
    try:
        return pygame.font.SysFont("Courier New", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


_STAT_LABELS = {
    "ranged":  [("Damage",   "damage"),
                ("Range",    "range"),
                ("Cooldown", "cooldown"),
                ("Stamina",  "stamina_cost"),
                ("Proj Spd", "projectile_speed")],
    "melee":   [("Damage",   "damage"),
                ("Range",    "range"),
                ("Cooldown", "cooldown"),
                ("Stamina",  "stamina_cost")],
    "utility": [("Damage",   "damage"),
                ("Range",    "range"),
                ("Cooldown", "cooldown"),
                ("Stamina",  "stamina_cost")],
}

_TYPE_BADGE = {
    "ranged":  ((60, 140, 220), "RANGED"),
    "melee":   ((200, 230, 255), "MELEE"),
    "utility": ((100, 255, 160), "UTILITY"),
}


class LoadoutScreen:
    """
    Full-screen loadout selection UI.
    Call  .run()  — it blocks until the player confirms their selection
    and returns a list of 2 weapon name strings.
    """

    CARD_W = 240
    CARD_H = 300
    GAP    = 24

    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen = screen
        self.clock  = clock

        self._selected: list[str] = []   # up to PLAYER_MAX_LOADOUT names
        self._hover_idx: int = -1
        self._confirm_hover = False
        self._time = 0.0

        # Pre-build fonts
        self.f_title  = _sysf(52, bold=True)
        self.f_sub    = _sysf(18)
        self.f_card   = _sysf(17, bold=True)
        self.f_stat   = _sysf(14)
        self.f_badge  = _sysf(12, bold=True)
        self.f_desc   = _sysf(13)
        self.f_btn    = _sysf(20, bold=True)
        self.f_hint   = _sysf(14)

        # Layout: center 4 cards
        total_w = 4 * self.CARD_W + 3 * self.GAP
        self._start_x = (SCREEN_W - total_w) // 2
        self._cards_y = 180

        # Confirm button rect
        self._btn_rect = pygame.Rect(
            SCREEN_W // 2 - 140, SCREEN_H - 90, 280, 48
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> list[str] | None:
        """
        Blocks until selection is confirmed.
        Returns list of weapon name strings, or None if player quit.
        """
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self._time += dt

            mouse_pos = pygame.mouse.get_pos()
            self._update_hover(mouse_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    result = self._handle_key(event.key)
                    if result is not None:
                        return result
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    result = self._handle_click(mouse_pos)
                    if result is not None:
                        return result

            self._draw()
            pygame.display.flip()

    # ── Input ─────────────────────────────────────────────────────────────────

    def _update_hover(self, mouse_pos):
        mx, my = mouse_pos
        self._hover_idx     = -1
        self._confirm_hover = self._btn_rect.collidepoint(mx, my)

        for i, name in enumerate(WEAPON_NAMES):
            x = self._start_x + i * (self.CARD_W + self.GAP)
            y = self._cards_y
            if (x <= mx <= x + self.CARD_W and
                    y <= my <= y + self.CARD_H):
                self._hover_idx = i
                break

    def _handle_click(self, mouse_pos) -> list[str] | None:
        mx, my = mouse_pos

        # Confirm button
        if self._btn_rect.collidepoint(mx, my):
            if len(self._selected) == PLAYER_MAX_LOADOUT:
                return list(self._selected)
            return None   # not enough selected yet

        # Card click
        for i, name in enumerate(WEAPON_NAMES):
            x = self._start_x + i * (self.CARD_W + self.GAP)
            y = self._cards_y
            if (x <= mx <= x + self.CARD_W and
                    y <= my <= y + self.CARD_H):
                self._toggle(name)
                break

        return None

    def _handle_key(self, key) -> list[str] | None:
        if key == pygame.K_ESCAPE:
            return None   # quit signal

        # Number keys 1-4 toggle weapons
        key_map = {
            pygame.K_1: 0, pygame.K_2: 1,
            pygame.K_3: 2, pygame.K_4: 3,
        }
        if key in key_map:
            idx = key_map[key]
            if idx < len(WEAPON_NAMES):
                self._toggle(WEAPON_NAMES[idx])

        # Enter confirms if ready
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if len(self._selected) == PLAYER_MAX_LOADOUT:
                return list(self._selected)

        return None

    def _toggle(self, name: str):
        if name in self._selected:
            self._selected.remove(name)
        elif len(self._selected) < PLAYER_MAX_LOADOUT:
            self._selected.append(name)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw(self):
        surf = self.screen
        surf.fill(C_BG)

        self._draw_bg_grid(surf)
        self._draw_header(surf)
        self._draw_cards(surf)
        self._draw_selection_summary(surf)
        self._draw_confirm_button(surf)
        self._draw_instructions(surf)

    def _draw_bg_grid(self, surf):
        step  = 60
        alpha = 25 + int(10 * math.sin(self._time * 0.5))
        for x in range(0, SCREEN_W + step, step):
            s = pygame.Surface((1, SCREEN_H), pygame.SRCALPHA)
            s.fill((40, 80, 60, alpha))
            surf.blit(s, (x, 0))
        for y in range(0, SCREEN_H + step, step):
            s = pygame.Surface((SCREEN_W, 1), pygame.SRCALPHA)
            s.fill((40, 80, 60, alpha))
            surf.blit(s, (0, y))

    def _draw_header(self, surf):
        # Pulsing accent line
        pulse = 0.5 + 0.5 * math.sin(self._time * 1.5)

        title = self.f_title.render("MUTAGEN ARENA", True, C_ACCENT)
        surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 28))

        sub = self.f_sub.render(
            "SELECT YOUR LOADOUT  —  choose 2 weapons", True, C_GRAY
        )
        surf.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 98))

        # Divider
        line_color = tuple(int(c * pulse) for c in C_ACCENT)
        pygame.draw.line(surf, line_color,
                         (SCREEN_W // 2 - 260, 130),
                         (SCREEN_W // 2 + 260, 130), 1)

    def _draw_cards(self, surf):
        for i, name in enumerate(WEAPON_NAMES):
            x        = self._start_x + i * (self.CARD_W + self.GAP)
            y        = self._cards_y
            selected = name in self._selected
            hovered  = (i == self._hover_idx)
            order    = (self._selected.index(name) + 1
                        if selected else None)
            self._draw_card(surf, x, y, name, selected, hovered, order, i)

    def _draw_card(self, surf, x, y, name, selected, hovered, order, key_num):
        cfg  = WEAPONS[name]
        w, h = self.CARD_W, self.CARD_H

        # Elevation / lift on hover or select
        lift = 10 if selected else (4 if hovered else 0)
        y   -= lift

        # Background
        if selected:
            bg = (18, 48, 30, 240)
        elif hovered:
            bg = (14, 24, 40, 220)
        else:
            bg = (10, 16, 28, 200)

        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill(bg)
        surf.blit(panel, (x, y))

        # Border
        border_color = (cfg.get("color", C_ACCENT) if selected
                        else (cfg.get("color", C_GRAY) if hovered
                              else (35, 45, 65)))
        border_w = 2 if selected else 1
        pygame.draw.rect(surf, border_color, (x, y, w, h), border_w,
                         border_radius=4)

        # Type badge
        wtype  = cfg["type"]
        b_col, b_label = _TYPE_BADGE.get(wtype, (C_GRAY, wtype.upper()))
        badge  = self.f_badge.render(b_label, True, b_col)
        bx     = x + w - badge.get_width() - 8
        by     = y + 8
        surf.blit(badge, (bx, by))

        # Weapon name
        name_surf = self.f_card.render(name, True,
                                       cfg.get("color", C_WHITE))
        surf.blit(name_surf, (x + 10, y + 8))

        # Divider
        pygame.draw.line(surf, border_color,
                         (x + 8, y + 34), (x + w - 8, y + 34), 1)

        # Description
        desc  = cfg.get("description", "")
        lines = _wrap_text(desc, self.f_desc, w - 20)
        for j, line in enumerate(lines[:3]):
            ls = self.f_desc.render(line, True, C_GRAY)
            surf.blit(ls, (x + 10, y + 42 + j * 18))

        # Stats
        stat_keys = _STAT_LABELS.get(wtype, _STAT_LABELS["ranged"])
        sy = y + 42 + len(lines[:3]) * 18 + 12
        pygame.draw.line(surf, (30, 45, 65),
                         (x + 8, sy - 4), (x + w - 8, sy - 4), 1)

        for label, key in stat_keys:
            val = cfg.get(key)
            if val is None:
                continue
            label_s = self.f_stat.render(f"{label:<10}", True, C_GRAY)
            val_s   = self.f_stat.render(str(val),       True, C_WHITE)
            surf.blit(label_s, (x + 10, sy))
            surf.blit(val_s,   (x + w - val_s.get_width() - 10, sy))
            sy += 20

        # Selected order badge
        if order is not None:
            badge_s = self.f_btn.render(f"SLOT {order}", True, C_BG)
            bw      = badge_s.get_width() + 16
            bh      = badge_s.get_height() + 8
            br      = pygame.Rect(x + w//2 - bw//2,
                                  y + h - bh - 10, bw, bh)
            pygame.draw.rect(surf, cfg.get("color", C_ACCENT), br,
                             border_radius=4)
            surf.blit(badge_s, (br.x + 8, br.y + 4))
        elif hovered and name not in self._selected:
            hint_s = self.f_stat.render(
                "CLICK to select" if len(self._selected) < PLAYER_MAX_LOADOUT
                else "LOADOUT FULL",
                True, C_GRAY
            )
            surf.blit(hint_s,
                      (x + w//2 - hint_s.get_width()//2, y + h - 22))

        # Key hint
        key_s = self.f_stat.render(f"[{key_num+1}]", True, C_GRAY)
        surf.blit(key_s, (x + 6, y + h - 20))

    def _draw_selection_summary(self, surf):
        """Show the 2 selected weapon names side-by-side above the button."""
        y   = self._btn_rect.top - 40
        cx  = SCREEN_W // 2
        gap = 30

        for i in range(PLAYER_MAX_LOADOUT):
            bx = cx - self.CARD_W//2 - gap//2 + i * (self.CARD_W + gap)
            if i < len(self._selected):
                name    = self._selected[i]
                color   = WEAPONS[name].get("color", C_ACCENT)
                lbl     = self.f_card.render(f"SLOT {i+1}: {name}", True, color)
            else:
                lbl = self.f_card.render(f"SLOT {i+1}: — empty —", True, C_DARK)
            surf.blit(lbl, (bx, y))

    def _draw_confirm_button(self, surf):
        ready = len(self._selected) == PLAYER_MAX_LOADOUT

        if ready:
            pulse = 0.75 + 0.25 * math.sin(self._time * 3)
            color = tuple(int(c * pulse) for c in C_ACCENT)
            bg    = (18, 50, 30, 230)
        else:
            color = (50, 60, 70)
            bg    = (12, 16, 22, 200)

        r   = self._btn_rect
        s   = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        s.fill(bg)
        surf.blit(s, r.topleft)
        pygame.draw.rect(surf, color, r, 2, border_radius=6)

        label_str = ("▶  START RUN  ◀" if ready
                     else f"SELECT  {PLAYER_MAX_LOADOUT - len(self._selected)}  MORE  WEAPON(S)")
        label = self.f_btn.render(label_str, True,
                                   color if ready else C_GRAY)
        surf.blit(label,
                  (r.x + r.w//2 - label.get_width()//2,
                   r.y + r.h//2 - label.get_height()//2))

    def _draw_instructions(self, surf):
        text = ("Keys [1-4] toggle weapons    ENTER to confirm    ESC to quit")
        s    = self.f_hint.render(text, True, (60, 70, 90))
        surf.blit(s, (SCREEN_W//2 - s.get_width()//2, SCREEN_H - 22))


# ── Text wrap helper ──────────────────────────────────────────────────────────

def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words  = text.split()
    lines  = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines