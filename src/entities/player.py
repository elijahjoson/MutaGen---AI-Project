"""
player.py - Player entity for Mutagen Arena.

Responsibilities:
  - Directional movement (WASD) with arena collision
  - Evasion / dash (stamina-based)
  - Invincibility frames after being hit
  - Loadout management (2 weapons, switch with Q or TAB)
  - Stamina regen + consumption
  - HP regen at wave end

"""

import pygame
import math
from src.core.constants import (
    ARENA_W, ARENA_H, SPEED_SCALE,
    PLAYER_HP, PLAYER_SPEED, PLAYER_RADIUS,
    PLAYER_MAX_STAMINA, PLAYER_STAMINA_REGEN,
    PLAYER_DASH_COST, PLAYER_DASH_SPEED_MULT, PLAYER_DASH_DURATION,
    PLAYER_INV_FRAMES, PLAYER_HP_REGEN_WAVE, PLAYER_MAX_LOADOUT,
    C_PLAYER, C_PLAYER_BLADE, C_WHITE, C_GRAY,
    C_HP_BG, C_HP_FG, C_STAMINA_BG, C_STAMINA_FG,
    C_ACCENT, C_DANGER, C_WARN, SCREEN_W, SCREEN_H,
)
from src.entities.weapon import create_weapon, Weapon


class Player:
    # ── Init ──────────────────────────────────────────────────────────────────

    def __init__(self, loadout_names: list[str]):
        """
        loadout_names: list of 2 weapon name strings, e.g.
          ["Pulse Rifle", "Shock Blade"]
        Comes from the loadout selection screen.
        """
        # World position — start at center of the arena
        self.x: float = ARENA_W / 2
        self.y: float = ARENA_H / 2

        # Stats
        self.max_hp:  float = float(PLAYER_HP)
        self.hp:      float = float(PLAYER_HP)
        self.speed:   float = float(PLAYER_SPEED)   # game units/s
        self.radius:  int   = PLAYER_RADIUS
        self.alive:   bool  = True

        # Stamina
        self.max_stamina:   float = float(PLAYER_MAX_STAMINA)
        self.stamina:       float = float(PLAYER_MAX_STAMINA)
        self._stam_regen:   float = float(PLAYER_STAMINA_REGEN)

        # Dash state
        self._dashing:      bool  = False
        self._dash_timer:   float = 0.0
        self._dash_dx:      float = 0.0
        self._dash_dy:      float = 0.0
        self._dash_speed:   float = (PLAYER_SPEED * PLAYER_DASH_SPEED_MULT
                                     * SPEED_SCALE)

        # Invincibility frames
        self._inv_timer:    float = 0.0

        # Facing direction (radians toward mouse)
        self.facing_angle:  float = 0.0

        # Loadout
        self.loadout: list[Weapon] = [create_weapon(n) for n in loadout_names]
        self.active_weapon_idx: int = 0

        # Visual / animation
        self._flicker:      bool  = False
        self._bob_timer:    float = 0.0

        # Damage taken tracking (for Centeno's fitness function)
        self.total_damage_taken: float = 0.0

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def active_weapon(self) -> Weapon:
        return self.loadout[self.active_weapon_idx]

    # ── Public update entry point ──────────────────────────────────────────────

    def update(
        self,
        dt: float,
        mouse_world: tuple[float, float],
        events: list[pygame.event.Event],
    ):
        """
        Call once per frame from the main game loop.
        mouse_world: cursor position in world coordinates
          (use camera.screen_to_world(pygame.mouse.get_pos()))
        events: pygame event list for this frame (for key-down detection)
        """
        if not self.alive:
            return

        mx, my = mouse_world
        self.facing_angle = math.atan2(my - self.y, mx - self.x)

        self._handle_events(events, mx, my)
        self._handle_movement(dt)
        self._handle_shooting(dt, mx, my)
        self._tick_timers(dt)
        self._update_weapons(dt)
        self._bob_timer += dt

    # ── Event handling (key-down, one-shots) ──────────────────────────────────

    def _handle_events(self, events: list, mx: float, my: float):
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Weapon switch
                if event.key in (pygame.K_q, pygame.K_TAB):
                    self._switch_weapon()
                # Dash
                if event.key in (pygame.K_SPACE, pygame.K_LSHIFT,
                                  pygame.K_RSHIFT):
                    self._try_dash()
                # Number keys for direct weapon select
                if event.key == pygame.K_1:
                    self.active_weapon_idx = 0
                if event.key == pygame.K_2 and len(self.loadout) > 1:
                    self.active_weapon_idx = 1

            # Right-click also triggers dash
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self._try_dash()

    # ── Movement ──────────────────────────────────────────────────────────────

    def _handle_movement(self, dt: float):
        keys = pygame.key.get_pressed()

        if self._dashing:
            # Dash movement overrides normal movement
            self._dash_timer -= dt
            spd = self._dash_speed
            nx  = self.x + self._dash_dx * spd * dt
            ny  = self.y + self._dash_dy * spd * dt
            self._clamp_to_arena(nx, ny)
            if self._dash_timer <= 0:
                self._dashing = False
            return

        # Normal WASD / arrow key movement
        dx = dy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:   dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:   dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:  dx += 1

        if dx != 0 or dy != 0:
            length = math.sqrt(dx*dx + dy*dy)
            dx /= length
            dy /= length

        px_speed = self.speed * SPEED_SCALE    # pixels per second
        nx = self.x + dx * px_speed * dt
        ny = self.y + dy * px_speed * dt
        self._clamp_to_arena(nx, ny)

    def _clamp_to_arena(self, nx: float, ny: float):
        self.x = max(float(self.radius), min(float(ARENA_W - self.radius), nx))
        self.y = max(float(self.radius), min(float(ARENA_H - self.radius), ny))

    # ── Dash ──────────────────────────────────────────────────────────────────

    def _try_dash(self):
        if self._dashing:
            return
        if self.stamina < PLAYER_DASH_COST:
            return

        # Dash in the direction currently moving; fallback to facing direction
        keys = pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:   dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:   dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:  dx += 1

        if dx == 0 and dy == 0:
            dx = math.cos(self.facing_angle)
            dy = math.sin(self.facing_angle)

        length = math.sqrt(dx*dx + dy*dy)
        self._dash_dx     = dx / length
        self._dash_dy     = dy / length
        self._dashing     = True
        self._dash_timer  = PLAYER_DASH_DURATION
        self._inv_timer   = PLAYER_DASH_DURATION   # invincible during dash

        self.stamina = max(0.0, self.stamina - PLAYER_DASH_COST)

    # ── Shooting (held LMB fires active weapon) ───────────────────────────────

    def _handle_shooting(self, dt: float, mx: float, my: float):
        if pygame.mouse.get_pressed()[0]:   # LMB held
            cost = self.active_weapon.try_fire(
                self.x, self.y, mx, my, self.stamina
            )
            self.stamina = max(0.0, self.stamina - cost)

    # ── Timers & regen ────────────────────────────────────────────────────────

    def _tick_timers(self, dt: float):
        # Invincibility
        if self._inv_timer > 0:
            self._inv_timer = max(0.0, self._inv_timer - dt)

        # Flicker flag for draw
        self._flicker = (self._inv_timer > 0 and
                         int(self._inv_timer * 16) % 2 == 0)

        # Stamina regen (not during dash — cost already paid)
        self.stamina = min(
            self.max_stamina,
            self.stamina + self._stam_regen * dt
        )

    def _update_weapons(self, dt: float):
        for weapon in self.loadout:
            weapon.update(dt, self.x, self.y)

    # ── Weapon switch ─────────────────────────────────────────────────────────

    def _switch_weapon(self):
        if len(self.loadout) > 1:
            self.active_weapon_idx = (self.active_weapon_idx + 1) % len(self.loadout)

    # ── Damage ────────────────────────────────────────────────────────────────

    def take_damage(self, amount: float):
        """
        Apply damage to the player. Respects invincibility frames.
        Called by wave_manager (Tabuena) on enemy contact / bullet hit.
        """
        if self._inv_timer > 0:
            return
        self.hp = max(0.0, self.hp - amount)
        self.total_damage_taken += amount
        self._inv_timer = 1.0
        if self.hp <= 0:
            self.alive = False

    def regen_hp_wave(self):
        self.hp = min(self.max_hp, self.hp + PLAYER_HP_REGEN_WAVE)

    # ── Upgrades ─────────────────────────────────────────────────────────────

    def apply_upgrade(self, upgrade: dict):
        """
        Called by Tabuena's upgrade screen when player picks an upgrade.
        Upgrade dict format: {"stat": str, "value": float/int}
        """
        stat  = upgrade["stat"]
        value = upgrade["value"]

        if stat == "max_hp":
            self.max_hp += int(value)
            self.hp = min(self.hp + int(value), self.max_hp)
        elif stat == "speed":
            self.speed *= (1 + value)
        elif stat == "max_stamina":
            self.max_stamina += int(value)
        elif stat == "stam_regen":
            self._stam_regen *= (1 + value)
        elif stat == "dash":
            # Just reset stamina so they can dash immediately after upgrade
            self.stamina = self.max_stamina
        else:
            # Pass weapon-related upgrades to all weapons in loadout
            for weapon in self.loadout:
                weapon.apply_upgrade(stat, value)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surf: pygame.Surface, camera):
        """Draw the player and all active weapon effects."""
        # Draw all weapon effects (projectiles, traps, swing hitboxes)
        for weapon in self.loadout:
            weapon.draw(surf, camera)

        if not self.alive:
            return

        # Invincibility flicker — skip drawing every other frame
        if self._flicker:
            return

        sx, sy = camera.world_to_screen(self.x, self.y)
        isx, isy = int(sx), int(sy)

        # Dash glow
        if self._dashing:
            glow_r = self.radius + 10
            gs = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*C_PLAYER[:3], 80),
                               (glow_r, glow_r), glow_r)
            surf.blit(gs, (isx - glow_r, isy - glow_r))

        # Body
        pygame.draw.circle(surf, C_PLAYER, (isx, isy), self.radius)

        # Gun barrel (points toward cursor)
        barrel_len = self.radius + 10
        ex = sx + math.cos(self.facing_angle) * barrel_len
        ey = sy + math.sin(self.facing_angle) * barrel_len
        pygame.draw.line(surf, C_PLAYER_BLADE,
                         (isx, isy), (int(ex), int(ey)), 4)

        # Inner dot
        pygame.draw.circle(surf, C_WHITE, (isx, isy), 5)

        # Active weapon indicator dot (colored by weapon)
        w_color = self.active_weapon.color
        pygame.draw.circle(surf, w_color, (isx, isy - self.radius - 6), 4)

    # ── HUD helpers ───────────────────────────────────────────────────────────

    def draw_hud(self, surf: pygame.Surface):
        """
        Draw player status bars (HP, stamina, active weapon, loadout slots).
        Call this from hud.py or directly from the game loop.
        """
        self._draw_hp_bar(surf)
        self._draw_stamina_bar(surf)
        self._draw_loadout_slots(surf)

    def _draw_hp_bar(self, surf):
        from src.ui.ui_helpers import draw_pill_bar, draw_panel, draw_scanlines, lerp_color
        from src.ui import font_manager as fm

        x, y, w, h = 20, SCREEN_H - 74, 260, 18
        ratio = self.hp / self.max_hp if self.max_hp > 0 else 0

        # Panel behind HP bar
        panel_rect = pygame.Rect(x - 8, y - 22, w + 16, h + 34)
        draw_panel(surf, panel_rect,
                   border_color=(60, 30, 30) if ratio > 0.25 else (120, 40, 40),
                   bg_color=(6, 8, 14, 210),
                   border_radius=6)
        draw_scanlines(surf, panel_rect, alpha=6, spacing=4)

        # Color transitions based on HP ratio
        if ratio > 0.5:
            fg = C_HP_FG
            glow = None
        elif ratio > 0.25:
            fg = C_WARN
            glow = None
        else:
            # Critical — pulsing glow
            pulse = 0.6 + 0.4 * math.sin(self._bob_timer * 6.0)
            fg = lerp_color(C_DANGER, (255, 100, 100), pulse)
            glow = (255, 60, 60)

        draw_pill_bar(surf, x, y, w, h, ratio, fg,
                      bg_color=C_HP_BG, glow_color=glow,
                      border_color=(80, 35, 35))

        # Label — ensure it stays within the panel area
        hp_font = fm.tiny()
        hp_label = hp_font.render(
            f"HP  {int(self.hp)}/{int(self.max_hp)}", True,
            (255, 200, 200) if ratio > 0.25 else (255, 130, 130)
        )
        surf.blit(hp_label, (x + 2, y - 18))

        # Cross icon — right side, vertically centered with label
        cx_icon = x + w - 8
        cy_icon = y - 12
        icon_color = fg[:3] if ratio > 0.25 else (255, 80, 80)
        pygame.draw.line(surf, icon_color, (cx_icon - 4, cy_icon), (cx_icon + 4, cy_icon), 2)
        pygame.draw.line(surf, icon_color, (cx_icon, cy_icon - 4), (cx_icon, cy_icon + 4), 2)

    def _draw_stamina_bar(self, surf):
        from src.ui.ui_helpers import draw_pill_bar, lerp_color
        from src.ui import font_manager as fm

        x, y, w, h = 20, SCREEN_H - 34, 260, 10
        ratio = self.stamina / self.max_stamina if self.max_stamina > 0 else 0

        # Determine state
        can_dash = self.stamina >= PLAYER_DASH_COST
        regenerating = ratio < 1.0 and not self._dashing

        # Bar color — brighter when full, flickers when below dash cost
        if not can_dash:
            pulse = 0.5 + 0.5 * math.sin(self._bob_timer * 8.0)
            fg = lerp_color((30, 80, 160), (60, 160, 255), pulse)
        elif regenerating:
            fg = (50, 140, 240)
        else:
            fg = C_STAMINA_FG

        glow = (60, 160, 255) if regenerating and ratio < 0.3 else None

        draw_pill_bar(surf, x, y, w, h, ratio, fg,
                      bg_color=C_STAMINA_BG, glow_color=glow,
                      border_color=(30, 50, 80))

        # Label — left of bar, above it
        stam_font = fm.tiny()
        stam_color = (100, 180, 255) if can_dash else (80, 100, 140)
        stam_label = stam_font.render(
            f"STAMINA {int(self.stamina)}", True, stam_color
        )
        surf.blit(stam_label, (x + 2, y - 12))

        # Dash cost marker (small tick on the bar)
        cost_ratio = PLAYER_DASH_COST / self.max_stamina
        cx = int(x + cost_ratio * w)
        marker_color = C_WARN if can_dash else (80, 60, 40)
        pygame.draw.line(surf, marker_color, (cx, y - 1), (cx, y + h + 1), 2)

    def _draw_loadout_slots(self, surf):
        """Draw the 2 weapon slots in the bottom-right area."""
        from src.ui.ui_helpers import draw_panel, draw_pill_bar, brighten
        from src.ui import font_manager as fm

        slot_w, slot_h = 180, 50
        gap            = 10
        start_x        = SCREEN_W - (slot_w * len(self.loadout) + gap * (len(self.loadout) - 1)) - 20
        y              = SCREEN_H - slot_h - 14

        font_sm = fm.tiny()
        font_md = fm.tiny()  # Use tiny for weapon names to fit

        for i, weapon in enumerate(self.loadout):
            x       = start_x + i * (slot_w + gap)
            active  = (i == self.active_weapon_idx)

            # Panel styling
            if active:
                bg = (14, 40, 28, 230)
                border = weapon.color
                bw = 2
            else:
                bg = (8, 14, 24, 180)
                border = (50, 60, 70)
                bw = 1

            slot_rect = pygame.Rect(x, y, slot_w, slot_h)
            draw_panel(surf, slot_rect, border_color=border,
                       bg_color=bg, border_width=bw, border_radius=6)

            # Active glow
            if active:
                glow_surf = pygame.Surface((slot_w + 8, slot_h + 8), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*weapon.color[:3], 20),
                                 pygame.Rect(0, 0, slot_w + 8, slot_h + 8),
                                 border_radius=8)
                surf.blit(glow_surf, (x - 4, y - 4))

            # Key hint — top-left corner, small
            key_text = "Q" if i == 0 else str(i + 1)
            hint = font_sm.render(f"[{key_text}]", True, (70, 80, 100))
            surf.blit(hint, (x + 6, y + 4))

            # Weapon name — right of key hint, truncated to fit
            name_color = weapon.color if active else C_GRAY
            # Measure available space for name (slot width minus padding and hint)
            name_x = x + hint.get_width() + 10
            max_name_w = slot_w - hint.get_width() - 18
            # Truncate name to fit
            display_name = weapon.name
            name_surf = font_md.render(display_name, True, name_color)
            while name_surf.get_width() > max_name_w and len(display_name) > 3:
                display_name = display_name[:-1]
                name_surf = font_md.render(display_name + "..", True, name_color)
            surf.blit(name_surf, (name_x, y + 4))

            # Cooldown bar inside slot
            cd = 1.0 - weapon.cooldown_ratio
            bar_y = y + slot_h - 12
            bar_w = slot_w - 16
            cd_fg = weapon.color if active else (80, 90, 100)
            draw_pill_bar(surf, x + 8, bar_y, bar_w, 5,
                          cd, cd_fg, bg_color=(25, 30, 40),
                          border_color=(40, 45, 55))