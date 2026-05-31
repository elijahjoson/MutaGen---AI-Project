"""
loadout_screen.py - Weapon loadout selection screen.

Shows all 4 available weapons. Player selects up to PLAYER_MAX_LOADOUT (2).
Returns the selected weapon names to the game controller.

Premium version with animated hex grid, weapon icons, neon selection glow,
visual stat bars, and styled confirm button.
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
from src.ui import font_manager as fm
from src.ui.ui_helpers import (
    draw_panel, draw_scanlines, draw_vignette, draw_pill_bar,
    draw_weapon_icon, brighten, dim, with_alpha, lerp_color,
    ParticleSystem, pulse_color,
)


# ── Stat display config ─────────────────────────────────────────────────────

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

# Max values for stat bars (for normalization)
_STAT_MAXES = {
    "damage": 100, "range": 700, "cooldown": 3.0,
    "stamina_cost": 25, "projectile_speed": 15,
}


class LoadoutScreen:
    """
    Full-screen loadout selection UI.
    Call  .run()  — it blocks until the player confirms their selection
    and returns a list of 2 weapon name strings.
    """

    CARD_W = 290
    CARD_H = 400
    GAP    = 12

    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen = screen
        self.clock  = clock

        self._selected: list[str] = []   # up to PLAYER_MAX_LOADOUT names
        self._hover_idx: int = -1
        self._confirm_hover = False
        self._time = 0.0

        # Layout: center 4 cards
        total_w = 4 * self.CARD_W + 3 * self.GAP
        self._start_x = (SCREEN_W - total_w) // 2
        self._cards_y = 130

        # Confirm button rect
        self._btn_rect = pygame.Rect(
            SCREEN_W // 2 - 160, SCREEN_H - 90, 320, 52
        )

        # Particles
        self._particles = ParticleSystem(count=25, bounds=(SCREEN_W, SCREEN_H),
                                          color=(50, 120, 80))

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> list[str] | None:
        """
        Blocks until selection is confirmed.
        Returns list of weapon name strings, or None if player quit.
        """
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self._time += dt
            self._particles.update(dt)

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

        # Background gradient
        for y_band in range(0, SCREEN_H, 4):
            frac = y_band / SCREEN_H
            r = int(6 + 6 * frac)
            g = int(8 + 10 * frac)
            b = int(16 + 14 * frac)
            pygame.draw.rect(surf, (r, g, b), (0, y_band, SCREEN_W, 4))

        self._draw_bg_grid(surf)
        self._particles.draw(surf)
        draw_scanlines(surf, alpha=4)
        draw_vignette(surf, intensity=50)

        self._draw_header(surf)
        self._draw_cards(surf)
        self._draw_selection_summary(surf)
        self._draw_confirm_button(surf)
        self._draw_instructions(surf)

    def _draw_bg_grid(self, surf):
        """Animated hex-grid pattern."""
        step  = 60
        pulse = 0.5 + 0.5 * math.sin(self._time * 0.4)
        alpha = int(15 + 10 * pulse)

        for x in range(0, SCREEN_W + step, step):
            s = pygame.Surface((1, SCREEN_H), pygame.SRCALPHA)
            s.fill((40, 80, 60, alpha))
            surf.blit(s, (x, 0))
        for y in range(0, SCREEN_H + step, step):
            s = pygame.Surface((SCREEN_W, 1), pygame.SRCALPHA)
            s.fill((40, 80, 60, alpha))
            surf.blit(s, (0, y))

        # Hex accents at intersections
        hex_alpha = int(alpha * 0.4)
        for gx in range(0, SCREEN_W + step, step):
            for gy in range(0, SCREEN_H + step, step):
                if (gx + gy) % (step * 2) == 0:
                    ps = pygame.Surface((6, 6), pygame.SRCALPHA)
                    pygame.draw.circle(ps, (60, 120, 80, hex_alpha), (3, 3), 3)
                    surf.blit(ps, (gx - 3, gy - 3))

    def _draw_header(self, surf):
        # Pulsing accent
        pulse = 0.6 + 0.4 * math.sin(self._time * 1.5)

        title_font = fm.title()
        title_color = pulse_color(C_ACCENT, pulse)
        title = title_font.render("MUTAGEN ARENA", True, title_color)
        surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 24))

        sub = fm.body().render(
            "SELECT YOUR LOADOUT  —  choose 2 weapons", True, C_GRAY
        )
        surf.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 80))

        # Divider with corner accents
        div_y = 115
        div_w = 520
        div_x = SCREEN_W // 2 - div_w // 2
        line_surf = pygame.Surface((div_w, 1), pygame.SRCALPHA)
        line_surf.fill((*title_color, int(60 * pulse)))
        surf.blit(line_surf, (div_x, div_y))

        acc = 16
        pygame.draw.line(surf, title_color, (div_x, div_y), (div_x + acc, div_y), 2)
        pygame.draw.line(surf, title_color,
                         (div_x + div_w - acc, div_y), (div_x + div_w, div_y), 2)

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
        wtype = cfg["type"]
        weapon_color = cfg.get("color", C_ACCENT)

        # Elevation / lift on hover or select
        lift = 12 if selected else (6 if hovered else 0)
        y   -= lift

        # Colors
        if selected:
            bg = (14, 45, 28, 240)
            border = weapon_color
            bw = 2
        elif hovered:
            bg = (12, 22, 38, 225)
            border = weapon_color
            bw = 1
        else:
            bg = (8, 14, 24, 200)
            border = (30, 40, 55)
            bw = 1

        card_rect = pygame.Rect(x, y, w, h)
        draw_panel(surf, card_rect, border_color=border,
                   bg_color=bg, border_width=bw, border_radius=8)

        # Selection glow pulse
        if selected:
            glow_alpha = int(25 + 10 * math.sin(self._time * 3.0))
            glow = pygame.Surface((w + 12, h + 12), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*weapon_color[:3], glow_alpha),
                             pygame.Rect(0, 0, w + 12, h + 12),
                             border_radius=12)
            surf.blit(glow, (x - 6, y - 6))
        elif hovered:
            glow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*weapon_color[:3], 15),
                             pygame.Rect(0, 0, w + 8, h + 8),
                             border_radius=10)
            surf.blit(glow, (x - 4, y - 4))

        # Top accent stripe
        accent = pygame.Surface((w - 2, 3), pygame.SRCALPHA)
        accent.fill((*weapon_color[:3], 160 if selected else (80 if hovered else 40)))
        surf.blit(accent, (x + 1, y + 1))

        # Weapon icon (centered, top area)
        icon_size = 36
        icon_x = x + w // 2 - icon_size // 2
        icon_y = y + 14
        icon_col = weapon_color if (selected or hovered) else dim(weapon_color, 0.5)
        draw_weapon_icon(surf, icon_x, icon_y, icon_size, wtype, icon_col)

        # Type badge (below icon)
        b_col, b_label = _TYPE_BADGE.get(wtype, (C_GRAY, wtype.upper()))
        badge_font = fm.tiny()
        badge = badge_font.render(b_label, True,
                                  b_col if (selected or hovered) else dim(b_col, 0.5))
        badge_rect = badge.get_rect(center=(x + w // 2, y + 56))
        surf.blit(badge, badge_rect)

        # Weapon name
        name_font = fm.header()
        name_color = weapon_color if (selected or hovered) else C_GRAY
        name_surf = name_font.render(name, True, name_color)
        surf.blit(name_surf, name_surf.get_rect(center=(x + w // 2, y + 80)))

        # Divider
        div_y = y + 100
        pygame.draw.line(surf, (30, 40, 55) if not selected else dim(weapon_color, 0.3),
                         (x + 12, div_y), (x + w - 12, div_y), 1)

        # Description
        desc = cfg.get("description", "")
        lines = _wrap_text(desc, fm.small(), w - 24)
        desc_color = (160, 165, 175) if (selected or hovered) else (100, 105, 115)
        for j, line in enumerate(lines[:3]):
            ls = fm.small().render(line, True, desc_color)
            surf.blit(ls, (x + 12, y + 110 + j * 16))

        # Stats as visual bars
        stat_keys = _STAT_LABELS.get(wtype, _STAT_LABELS["ranged"])
        sy = y + 110 + len(lines[:3]) * 16 + 10
        pygame.draw.line(surf, (25, 35, 50),
                         (x + 12, sy - 4), (x + w - 12, sy - 4), 1)

        for label, key in stat_keys:
            val = cfg.get(key)
            if val is None:
                continue

            label_font = fm.tiny()
            label_s = label_font.render(f"{label}", True, C_GRAY)
            surf.blit(label_s, (x + 12, sy + 1))

            # Value text
            val_s = label_font.render(str(val), True, C_WHITE)
            surf.blit(val_s, (x + w - val_s.get_width() - 12, sy + 1))

            # Mini stat bar
            max_val = _STAT_MAXES.get(key, 100)
            # Invert for cooldown (lower = better)
            if key == "cooldown":
                ratio = 1.0 - min(1.0, val / max_val)
            else:
                ratio = min(1.0, val / max_val)

            bar_y = sy + 15
            bar_w = w - 24
            bar_fg = weapon_color if (selected or hovered) else dim(weapon_color, 0.4)
            draw_pill_bar(surf, x + 12, bar_y, bar_w, 4, ratio, bar_fg,
                          bg_color=(18, 22, 32), border_color=(28, 34, 45))

            sy += 22

        # Selected order badge
        if order is not None:
            badge_font = fm.body()
            badge_s = badge_font.render(f"SLOT {order}", True, C_BG)
            bw_badge = badge_s.get_width() + 20
            bh_badge = badge_s.get_height() + 10
            br = pygame.Rect(x + w // 2 - bw_badge // 2,
                             y + h - bh_badge - 12, bw_badge, bh_badge)
            pygame.draw.rect(surf, weapon_color, br, border_radius=6)
            surf.blit(badge_s, (br.x + 10, br.y + 5))
        elif hovered and name not in self._selected:
            hint_text = ("CLICK to select" if len(self._selected) < PLAYER_MAX_LOADOUT
                         else "LOADOUT FULL")
            pulse = 0.6 + 0.4 * math.sin(self._time * 3.0)
            hint_color = pulse_color(weapon_color[:3], pulse)
            hint_s = fm.small().render(hint_text, True, hint_color)
            surf.blit(hint_s, hint_s.get_rect(center=(x + w // 2, y + h - 24)))

        # Key hint
        key_s = fm.tiny().render(f"[{key_num + 1}]", True, (60, 70, 85))
        surf.blit(key_s, (x + 8, y + h - 18))

    def _draw_selection_summary(self, surf):
        """Show the 2 selected weapon names side-by-side above the button."""
        y   = self._btn_rect.top - 44
        cx  = SCREEN_W // 2
        slot_w = 240
        gap = 30

        for i in range(PLAYER_MAX_LOADOUT):
            bx = cx - slot_w - gap // 2 + i * (slot_w + gap)

            if i < len(self._selected):
                name    = self._selected[i]
                color   = WEAPONS[name].get("color", C_ACCENT)

                # Slot panel
                slot_rect = pygame.Rect(bx, y - 4, slot_w, 28)
                draw_panel(surf, slot_rect,
                           border_color=dim(color, 0.5),
                           bg_color=(10, 20, 16, 180),
                           border_radius=4)

                lbl = fm.hud().render(f"SLOT {i+1}: {name}", True, color)
                surf.blit(lbl, (bx + 8, y))
            else:
                slot_rect = pygame.Rect(bx, y - 4, slot_w, 28)
                draw_panel(surf, slot_rect,
                           border_color=(30, 35, 45),
                           bg_color=(8, 12, 18, 140),
                           border_radius=4)

                lbl = fm.hud().render(f"SLOT {i+1}: — empty —", True, C_DARK)
                surf.blit(lbl, (bx + 8, y))

    def _draw_confirm_button(self, surf):
        ready = len(self._selected) == PLAYER_MAX_LOADOUT

        if ready:
            pulse = 0.7 + 0.3 * math.sin(self._time * 3)
            color = pulse_color(C_ACCENT, pulse)
            bg = (14, 42, 28, 230)
        else:
            color = (45, 55, 65)
            bg = (10, 14, 20, 200)

        r = self._btn_rect
        draw_panel(surf, r, border_color=color, bg_color=bg,
                   border_width=2 if ready else 1, border_radius=8)

        # Glow behind button when ready
        if ready and self._confirm_hover:
            glow = pygame.Surface((r.w + 12, r.h + 12), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*C_ACCENT[:3], 20),
                             pygame.Rect(0, 0, r.w + 12, r.h + 12),
                             border_radius=12)
            surf.blit(glow, (r.x - 6, r.y - 6))

        # Sweep animation when ready
        if ready:
            sweep_x = int((self._time * 120) % (r.w + 60)) - 30
            sweep_surf = pygame.Surface((30, r.h), pygame.SRCALPHA)
            for sx in range(30):
                a = int(20 * math.sin(sx / 30 * math.pi))
                pygame.draw.line(sweep_surf, (255, 255, 255, a),
                                 (sx, 0), (sx, r.h))
            surf.blit(sweep_surf, (r.x + sweep_x, r.y))

        label_str = ("▶  START RUN  ◀" if ready
                     else f"SELECT  {PLAYER_MAX_LOADOUT - len(self._selected)}  MORE  WEAPON(S)")
        label_font = fm.body()
        label = label_font.render(label_str, True,
                                   color if ready else C_GRAY)
        surf.blit(label,
                  (r.x + r.w // 2 - label.get_width() // 2,
                   r.y + r.h // 2 - label.get_height() // 2))

    def _draw_instructions(self, surf):
        text = "Keys [1-4] toggle weapons    ENTER to confirm    ESC to quit"
        s = fm.tiny().render(text, True, (50, 60, 75))
        surf.blit(s, (SCREEN_W // 2 - s.get_width() // 2, SCREEN_H - 22))


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