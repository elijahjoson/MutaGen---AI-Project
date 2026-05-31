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
from src.core.assets import AssetManager
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

        # --- NEW CLEAN ASSET LOADING ---
        SCALE = 1.5
        self.sprites = {
            "Pulse Rifle": AssetManager.get_image("assets/sprites/player/player_pulse.png", SCALE),
            "Arc Launcher": AssetManager.get_image("assets/sprites/player/player_arc.png", SCALE),
            "Stasis Trap": AssetManager.get_image("assets/sprites/player/player_trap.png", SCALE),
            "Shock Blade": AssetManager.get_image("assets/sprites/player/player_blade.png", SCALE)
        }
        
        self.default_sprite = self.sprites["Pulse Rifle"]
        
        # Load death and UI sprites (Scale is handled inside the manager!)
        self.death_sprite = AssetManager.get_image("assets/sprites/player/player_death.png", 1.0)
        self.crosshair_img = AssetManager.get_image("assets/sprites/player/crosshair.png", 0.2)
        
        self.death_timer = 0.0

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
        THICK_TOP    = 100
        THICK_BOTTOM = 40
        THICK_LEFT   = 16
        THICK_RIGHT  = 16
        
        # Calculate the safe inner bounds using the custom thicknesses
        min_x = THICK_LEFT + self.radius
        max_x = ARENA_W - THICK_RIGHT - self.radius
        min_y = THICK_TOP + self.radius
        max_y = ARENA_H - THICK_BOTTOM - self.radius

        # Clamp the player's position inside those bounds
        self.x = max(float(min_x), min(float(max_x), nx))
        self.y = max(float(min_y), min(float(max_y), ny))

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
        # 1. KEEP: Draw all weapon effects (projectiles, traps, swing hitboxes)
        for weapon in self.loadout:
            weapon.draw(surf, camera)

        sx, sy = camera.world_to_screen(self.x, self.y)
        isx, isy = int(sx), int(sy)

        # 2. KEEP: Death check
        if not self.alive:
            if self.death_sprite:
                pygame.mouse.set_visible(True) # <--- ADD THIS: Give the player their mouse back!
                if getattr(self, 'death_sprite', None):
                    self.death_timer += 0.05 
                    scale_factor = 1.0 + (self.death_timer * 2) 
                
                # 3. Stop growing after it gets massive (e.g., 4x size)
                if scale_factor < 4.0:
                    scaled_death = pygame.transform.scale_by(self.death_sprite, scale_factor)
                    death_rect = scaled_death.get_rect(center=(isx, isy))
                    surf.blit(scaled_death, death_rect.topleft)
            return

        # 3. KEEP: Invincibility flicker — skip drawing every other frame
        if self._flicker:
            return

        # 4. KEEP: Dash glow (This will act as a cool under-glow beneath your new sprite!)
        if self._dashing:
            glow_r = self.radius + 10
            gs = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*C_PLAYER[:3], 80),
                               (glow_r, glow_r), glow_r)
            surf.blit(gs, (isx - glow_r, isy - glow_r))

        # --- 5. NEW: SPRITE DRAWING LOGIC (Replaces the circles and lines) ---
        weapon_name = self.active_weapon.name if self.active_weapon else "Pulse Rifle"
        base_image = self.sprites.get(weapon_name, self.default_sprite)

        if base_image:
            # Convert the facing angle to degrees and invert it for Pygame
            angle_deg = math.degrees(-self.facing_angle)
            
            # Rotate the image
            rotated_image = pygame.transform.rotate(base_image, angle_deg)
            
            # The Wobble Fix: Force the center of the image to exactly match the player's X/Y
            img_rect = rotated_image.get_rect(center=(isx, isy))
            
            # Draw the perfectly centered, rotated sprite
            surf.blit(rotated_image, img_rect.topleft)
        else:
            # Fallback: If images failed to load, draw the old geometric body just in case
            pygame.draw.circle(surf, C_PLAYER, (isx, isy), self.radius)
            barrel_len = self.radius + 10
            ex = sx + math.cos(self.facing_angle) * barrel_len
            ey = sy + math.sin(self.facing_angle) * barrel_len
            pygame.draw.line(surf, C_PLAYER_BLADE, (isx, isy), (int(ex), int(ey)), 4)
            pygame.draw.circle(surf, C_WHITE, (isx, isy), 5)

        if getattr(self, 'crosshair_img', None):
            pygame.mouse.set_visible(False) # Hide the normal cursor
            mx, my = pygame.mouse.get_pos()
            ch_rect = self.crosshair_img.get_rect(center=(mx, my))
            surf.blit(self.crosshair_img, ch_rect.topleft)
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
        x, y, w, h = 20, SCREEN_H - 70, 240, 18
        ratio = self.hp / self.max_hp if self.max_hp > 0 else 0

        color = (C_HP_FG if ratio > 0.5 else
                 C_WARN  if ratio > 0.25 else C_DANGER)

        _draw_bar(surf, x, y, w, h, ratio, C_HP_BG, color)

        try:
            font = pygame.font.SysFont("Courier New", 15, bold=True)
            lbl  = font.render(f"HP  {int(self.hp)}/{int(self.max_hp)}",
                               True, C_WHITE)
            surf.blit(lbl, (x, y - 18))
        except Exception:
            pass

    def _draw_stamina_bar(self, surf):
        x, y, w, h = 20, SCREEN_H - 38, 240, 12
        ratio = self.stamina / self.max_stamina if self.max_stamina > 0 else 0

        _draw_bar(surf, x, y, w, h, ratio, C_STAMINA_BG, C_STAMINA_FG)

        try:
            font = pygame.font.SysFont("Courier New", 14)
            lbl  = font.render(f"STAMINA  {int(self.stamina)}", True,
                               (100, 180, 255))
            surf.blit(lbl, (x, y - 17))
        except Exception:
            pass

        # Dash cost indicator
        cost_ratio = PLAYER_DASH_COST / self.max_stamina
        cx = int(x + cost_ratio * w)
        pygame.draw.line(surf, C_WARN, (cx, y - 2), (cx, y + h + 2), 2)

    def _draw_loadout_slots(self, surf):
        """Draw the 2 weapon slots in the bottom-right area."""
        slot_w, slot_h = 110, 36
        gap            = 6
        start_x        = SCREEN_W - (slot_w * 2 + gap) - 20
        y              = SCREEN_H - slot_h - 16

        try:
            font_sm = pygame.font.SysFont("Courier New", 13)
            font_md = pygame.font.SysFont("Courier New", 15, bold=True)
        except Exception:
            font_sm = font_md = pygame.font.Font(None, 16)

        for i, weapon in enumerate(self.loadout):
            x       = start_x + i * (slot_w + gap)
            active  = (i == self.active_weapon_idx)
            bg      = (20, 50, 30, 220) if active else (10, 18, 30, 180)

            # Panel
            s = pygame.Surface((slot_w, slot_h), pygame.SRCALPHA)
            s.fill(bg)
            surf.blit(s, (x, y))
            border = weapon.color if active else C_GRAY
            pygame.draw.rect(surf, border, (x, y, slot_w, slot_h), 2)

            # Weapon name
            name_lbl = font_md.render(weapon.name[:14], True,
                                      weapon.color if active else C_GRAY)
            surf.blit(name_lbl, (x + 6, y + 4))

            # Cooldown bar inside slot
            cd = 1.0 - weapon.cooldown_ratio
            bar_y = y + slot_h - 8
            pygame.draw.rect(surf, C_GRAY, (x+4, bar_y, slot_w-8, 5))
            pygame.draw.rect(surf, weapon.color,
                             (x+4, bar_y, int((slot_w-8) * cd), 5))

            # Key hint
            hint = font_sm.render(f"[{'Q/TAB' if i==0 else '  2  '}]",
                                  True, C_GRAY)
            surf.blit(hint, (x + 6, y + 18))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _draw_bar(surf, x, y, w, h, ratio, bg_color, fg_color):
    panel = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 140))
    surf.blit(panel, (x - 2, y - 2))
    pygame.draw.rect(surf, bg_color, (x, y, w, h))
    pygame.draw.rect(surf, fg_color, (x, y, max(0, int(w * ratio)), h))
    pygame.draw.rect(surf, (80, 80, 100), (x, y, w, h), 1)