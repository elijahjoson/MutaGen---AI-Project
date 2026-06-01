"""
weapon.py - Weapon system for Mutagen Arena.

Contains:
  Projectile       — ranged bullet (Pulse Rifle, Arc Launcher)
  SwingHitbox      — melee hit zone (Shock Blade)
  Trap             — placed utility object (Stasis Trap)
  Weapon           — base class
  PulseRifle       — fast ranged, no stamina cost
  ShockBlade       — heavy melee
  ArcLauncher      — slow, high-damage ranged
  StasisTrap_W     — places a stasis trap on the ground
  create_weapon()  — factory function

"""

import pygame
import math
import random
from src.core.assets import AssetManager
from src.core.constants import (
    SPEED_SCALE, ARENA_W, ARENA_H,
    C_BULLET_PULSE, C_BULLET_ARC, C_SWING, C_TRAP, C_ENEMY_BULLET,
    WEAPONS,
)

# ── Projectile ────────────────────────────────────────────────────────────────

class Projectile:
    """
    A fired projectile (bullet).
    Dies when it travels >= max_range pixels OR age >= lifespan seconds
    OR leaves the arena.
    """
    def __init__(
        self, x: float, y: float,
        dx: float, dy: float,          # normalized direction
        speed_units: float,            # game units/s (will be * SPEED_SCALE)
        damage: int,
        radius: int,
        color: tuple,
        max_range: float,
        lifespan: float,
        image_path: str = None,
    ):
        self.x, self.y        = x, y
        self.dx, self.dy      = dx, dy
        self.speed            = speed_units * SPEED_SCALE  # px/s
        self.damage           = damage
        self.radius           = radius
        self.color            = color
        self.max_range        = max_range
        self.lifespan         = lifespan
        self.image = AssetManager.get_image(image_path, scale=1.0) if image_path else None
        self.alive            = True
        self._age             = 0.0
        self._dist_traveled   = 0.0
        self._trail: list[tuple] = []

    def update(self, dt: float):
        if not self.alive:
            return
        dist = self.speed * dt
        self._trail.append((self.x, self.y))
        if len(self._trail) > 5:
            self._trail.pop(0)

        self.x += self.dx * dist
        self.y += self.dy * dist
        self._dist_traveled += dist
        self._age            += dt

        if (self._dist_traveled >= self.max_range or
                self._age >= self.lifespan or
                not (0 <= self.x <= ARENA_W and 0 <= self.y <= ARENA_H)):
            self.alive = False

    def draw(self, surf: pygame.Surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        if self.image:
            # Rotate image to face direction of travel
            angle = math.degrees(math.atan2(self.dy, self.dx))
            rotated = pygame.transform.rotate(self.image, -angle - 90)
            rect = rotated.get_rect(center=(int(sx), int(sy)))
            surf.blit(rotated, rect.topleft)
        else:
            # Fallback for if image fails to load
            pygame.draw.circle(surf, self.color, (int(sx), int(sy)), self.radius)


# ── SwingHitbox ───────────────────────────────────────────────────────────────

class SwingHitbox:
    """
    A brief melee hitbox that stays alive for `duration` seconds.
    Tracks which enemy IDs have already been hit to avoid double-damage.

    TEAMMATE: check  `id(enemy) not in swing.already_hit`  before applying
    damage, then add  `swing.already_hit.add(id(enemy))`  afterward.
    """
    def __init__(
        self, x: float, y: float,
        angle: float,              # radians — direction player is facing
        radius: float,
        damage: int,
        duration: float = 0.18,
    ):
        self.x, self.y   = x, y
        self.angle        = angle
        self.radius       = radius
        self.damage       = damage
        self.duration     = duration
        self._timer       = duration
        self.alive        = True
        self.already_hit: set = set()
        self.image = AssetManager.get_image("assets/sprites/weapons/slash_fx.png", scale=4)
        
        self.total_frames = 10

    def update(self, dt: float):
        self._timer -= dt
        if self._timer <= 0:
            self.alive = False

    @property
    def progress(self) -> float:
        """0.0 = just spawned, 1.0 = about to expire."""
        return 1.0 - (self._timer / self.duration)

    def draw(self, surf: pygame.Surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        # 1. Sprite Sheet Animation (Centered 360 AOE)
        if self.image:
            # Figure out which frame we are currently on (0 through 9)
            current_frame = int(self.progress * self.total_frames)
            current_frame = min(current_frame, self.total_frames - 1)

            # Calculate how wide ONE frame is
            frame_w = self.image.get_width() // self.total_frames
            frame_h = self.image.get_height()
            
            # Create a blank, clear canvas just for this one frame
            frame_surf = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
            
            # Cut out exactly the frame we want and paste it on our blank canvas
            frame_surf.blit(self.image, (0, 0), (current_frame * frame_w, 0, frame_w, frame_h))

            # Rotate the frame based on where the mouse is aiming
            angle_deg = math.degrees(self.angle)
            rotated = pygame.transform.rotate(frame_surf, -angle_deg) 

            # Draw it exactly at the player's center (sx, sy)
            rect = rotated.get_rect(center=(int(sx), int(sy)))
            surf.blit(rotated, rect.topleft)
            return

        # 2. FALLBACK: Original Geometric Drawing
        alpha = int(180 * (1.0 - self.progress))
        s = pygame.Surface((int(self.radius)*2+4, int(self.radius)*2+4), pygame.SRCALPHA)
        pygame.draw.circle(
            s, (*C_SWING[:3], alpha),
            (int(self.radius)+2, int(self.radius)+2),
            int(self.radius)
        )
        surf.blit(s, (int(sx) - int(self.radius) - 2, int(sy) - int(self.radius) - 2))
        pygame.draw.circle(surf, C_SWING, (int(sx), int(sy)), int(self.radius), 2)
        pygame.draw.circle(surf, (255, 0, 0), (int(sx), int(sy)), int(self.radius), 1)

# ── Trap ──────────────────────────────────────────────────────────────────────

class Trap:
    """
    A placed stasis trap. Sits on the ground until an enemy steps on it.

    TEAMMATE: Each frame, for each alive (untriggered) trap, check if any
    enemy is within trap.radius of (trap.x, trap.y). If so, call
    trap.trigger() and apply trap.damage to that enemy + apply stasis.

    Stasis effect suggestion: set enemy._stasis_timer = 2.0 on the enemy
    and have the enemy reduce its speed while _stasis_timer > 0.
    """
    TRIGGER_VISUAL_DURATION = 0.4   # seconds to show explosion before removal

    def __init__(self, x: float, y: float, damage: int, radius: float):
        self.x, self.y    = x, y
        self.damage       = damage
        self.radius       = radius
        self.alive        = True
        self.triggered    = False
        self._vis_timer   = 0.0
        self._idle_pulse  = 0.0   # animation timer
        self.idle_img = AssetManager.get_image("assets/sprites/weapons/trap_idle.png", 0.75)
        self.active_img = AssetManager.get_image("assets/sprites/weapons/trap_active.png", 0.8)

    def trigger(self):
        """Call when an enemy steps on the trap."""
        if not self.triggered:
            self.triggered = True
            self._vis_timer = self.TRIGGER_VISUAL_DURATION

    def update(self, dt: float):
        self._idle_pulse += dt
        if self.triggered:
            self._vis_timer -= dt
            if self._vis_timer <= 0:
                self.alive = False

    def draw(self, surf: pygame.Surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)

        img = self.active_img if self.triggered else self.idle_img
        if img:
            rect = img.get_rect(center=(int(sx), int(sy)))
            surf.blit(img, rect.topleft)
            return

        if self.triggered:
            # Explosion ring
            progress = 1.0 - (self._vis_timer / self.TRIGGER_VISUAL_DURATION)
            r        = int(self.radius * (1.0 + progress * 1.5))
            alpha    = int(200 * (1.0 - progress))
            s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*C_TRAP[:3], alpha),
                               (r+2, r+2), r)
            surf.blit(s, (int(sx) - r - 2, int(sy) - r - 2))
        else:
            # Idle pulsing indicator
            pulse = 0.85 + 0.15 * math.sin(self._idle_pulse * 4)
            r     = int(self.radius * pulse)
            alpha = 90
            s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*C_TRAP[:3], alpha), (r+2, r+2), r)
            surf.blit(s, (int(sx) - r - 2, int(sy) - r - 2))
            # Hard outline
            pygame.draw.circle(surf, C_TRAP, (int(sx), int(sy)), r, 2)
            # Center dot
            pygame.draw.circle(surf, C_TRAP, (int(sx), int(sy)), 4)


# ── Base Weapon ───────────────────────────────────────────────────────────────

class Weapon:
    def __init__(self, name: str):
        cfg = WEAPONS[name]
        self.name          = name
        self.damage        = cfg["damage"]
        self.range         = cfg["range"]
        self.cooldown      = cfg["cooldown"]
        self.stamina_cost  = cfg["stamina_cost"]
        self.weapon_type   = cfg["type"]
        self.color         = cfg.get("color", (255, 255, 255))
        self.description   = cfg.get("description", "")

        self._cd_timer     = 0.0   # counts down to 0 = ready

        # All active threat objects — wave_manager checks these for collisions
        self.projectiles:    list[Projectile]  = []
        self.swing_hitboxes: list[SwingHitbox] = []
        self.traps:          list[Trap]        = []

    # ── Stamina / cooldown checks ─────────────────────────────────────────────

    def is_ready(self, stamina: float) -> bool:
        return self._cd_timer <= 0 and stamina >= self.stamina_cost

    @property
    def cooldown_ratio(self) -> float:
        """0 = fully charged, 1 = just fired."""
        return min(1.0, self._cd_timer / self.cooldown) if self.cooldown > 0 else 0.0

    # ── Public fire interface ─────────────────────────────────────────────────

    def try_fire(
        self,
        player_x: float, player_y: float,
        target_x: float, target_y: float,
        stamina:  float,
    ) -> float:
        """
        Attempt to fire the weapon toward (target_x, target_y).
        Returns the stamina cost deducted (0 if weapon wasn't ready).
        """
        if not self.is_ready(stamina):
            return 0.0
        self._cd_timer = self.cooldown
        self._fire(player_x, player_y, target_x, target_y)
        return float(self.stamina_cost)

    def _fire(self, px, py, tx, ty):
        """Override in subclasses."""
        raise NotImplementedError

    # ── Apply upgrades ────────────────────────────────────────────────────────

    def apply_upgrade(self, stat: str, value):
        if stat == "damage":
            self.damage = int(self.damage * (1 + value))
        elif stat == "cooldown":
            self.cooldown = max(0.1, self.cooldown * (1 + value))
        elif stat == "proj_speed":
            # Subclasses that have projectile_speed will override
            pass

    # ── Update / Draw ─────────────────────────────────────────────────────────

    def update(self, dt: float, player_x: float = 0, player_y: float = 0):
        self._cd_timer = max(0.0, self._cd_timer - dt)

        for p in self.projectiles:    p.update(dt)
        for s in self.swing_hitboxes: s.update(dt)
        for t in self.traps:          t.update(dt)

        self.projectiles    = [p for p in self.projectiles    if p.alive]
        self.swing_hitboxes = [s for s in self.swing_hitboxes if s.alive]
        self.traps          = [t for t in self.traps          if t.alive]

    def draw(self, surf: pygame.Surface, camera):
        for p in self.projectiles:    p.draw(surf, camera)
        for s in self.swing_hitboxes: s.draw(surf, camera)
        for t in self.traps:          t.draw(surf, camera)


# ── Pulse Rifle ───────────────────────────────────────────────────────────────

class PulseRifle(Weapon):
    """
    Fast ranged weapon. No stamina cost. Short range.
    Fires a single projectile toward the cursor.
    """
    def __init__(self):
        super().__init__("Pulse Rifle")
        cfg = WEAPONS["Pulse Rifle"]
        self._proj_speed    = cfg["projectile_speed"]
        self._proj_lifespan = cfg["projectile_lifespan"]
        self._proj_radius   = cfg["proj_radius"]

    def _fire(self, px, py, tx, ty):
        dx, dy = _normalize(tx - px, ty - py)
        angle = math.atan2(dy, dx)
        forward_offset = 30  # Distance forward to the gun tip
        right_offset = 15    # Distance to the right arm
        
        barrel_x = px + math.cos(angle) * forward_offset + math.cos(angle + math.pi / 2) * right_offset
        barrel_y = py + math.sin(angle) * forward_offset + math.sin(angle + math.pi / 2) * right_offset
        
        self.projectiles.append(Projectile(
            barrel_x, barrel_y, dx, dy,
            speed_units = self._proj_speed,
            damage      = self.damage,
            radius      = self._proj_radius,
            color       = self.color,
            max_range   = self.range,
            lifespan    = self._proj_lifespan,
            image_path  = "assets/sprites/weapons/bullet_pulse.png"
        ))

    def apply_upgrade(self, stat, value):
        super().apply_upgrade(stat, value)
        if stat == "proj_speed":
            self._proj_speed *= (1 + value)


# ── Shock Blade ───────────────────────────────────────────────────────────────

class ShockBlade(Weapon):
    """
    Heavy melee weapon. Creates a brief hitbox in a radius around the player.
    Hits every enemy within `range` pixels simultaneously.
    """
    def __init__(self):
        super().__init__("Shock Blade")
        self._swing_dur = WEAPONS["Shock Blade"]["swing_duration"]

    def _fire(self, px, py, tx, ty):
        angle = math.atan2(ty - py, tx - px)
        self.swing_hitboxes.append(SwingHitbox(
            x        = px,
            y        = py,
            angle    = angle,
            radius   = self.range,
            damage   = self.damage,
            duration = self._swing_dur,
        ))


# ── Arc Launcher ──────────────────────────────────────────────────────────────

class ArcLauncher(Weapon):
    """
    Slow, heavy ranged weapon. Deals massive damage per shot.
    High stamina cost. Projectile is large and slow.
    """
    def __init__(self):
        super().__init__("Arc Launcher")
        cfg = WEAPONS["Arc Launcher"]
        self._proj_speed    = cfg["projectile_speed"]
        self._proj_lifespan = cfg["projectile_lifespan"]
        self._proj_radius   = cfg["proj_radius"]

    def _fire(self, px, py, tx, ty):
        dx, dy = _normalize(tx - px, ty - py)
        angle = math.atan2(dy, dx)
        forward_offset = 30  
        right_offset = 15    
        
        barrel_x = px + math.cos(angle) * forward_offset + math.cos(angle + math.pi / 2) * right_offset
        barrel_y = py + math.sin(angle) * forward_offset + math.sin(angle + math.pi / 2) * right_offset
        
        # Slight spread for visual feel
        spread = random.uniform(-0.04, 0.04)
        dx2    = dx * math.cos(spread) - dy * math.sin(spread)
        dy2    = dx * math.sin(spread) + dy * math.cos(spread)
        self.projectiles.append(Projectile(
            barrel_x, barrel_y, dx2, dy2,
            speed_units = self._proj_speed,
            damage      = self.damage,
            radius      = self._proj_radius,
            color       = self.color,
            max_range   = self.range,
            lifespan    = self._proj_lifespan,
            image_path  = "assets/sprites/weapons/bullet_arc.png"
        ))

    def apply_upgrade(self, stat, value):
        super().apply_upgrade(stat, value)
        if stat == "proj_speed":
            self._proj_speed *= (1 + value)


# ── Stasis Trap ───────────────────────────────────────────────────────────────

class StasisTrap_W(Weapon):
    """
    Places a trap at the cursor position (within `range` pixels of player).
    The trap stays until triggered by an enemy walking over it.

    TEAMMATE:
      Each frame, for each trap in weapon.traps:
        for each alive enemy:
          dist = distance(enemy, trap)
          if dist < trap.radius and not trap.triggered:
              trap.trigger()
              enemy.take_damage(trap.damage)
              enemy._stasis_timer = 2.0   # slow enemy for 2s
    """
    def __init__(self):
        super().__init__("Stasis Trap")
        cfg = WEAPONS["Stasis Trap"]
        self._trap_radius = cfg["trap_radius"]

    def _fire(self, px, py, tx, ty):
        # Clamp placement to max range
        dist = math.sqrt((tx-px)**2 + (ty-py)**2)
        if dist > self.range:
            ratio = self.range / dist
            tx = px + (tx - px) * ratio
            ty = py + (ty - py) * ratio

        self.traps.append(Trap(
            x      = tx,
            y      = ty,
            damage = self.damage,
            radius = self._trap_radius,
        ))


# ── Factory ───────────────────────────────────────────────────────────────────

_WEAPON_CLASSES = {
    "Pulse Rifle":  PulseRifle,
    "Shock Blade":  ShockBlade,
    "Arc Launcher": ArcLauncher,
    "Stasis Trap":  StasisTrap_W,
}

def create_weapon(name: str) -> Weapon:
    """Returns a fresh weapon instance by name."""
    cls = _WEAPON_CLASSES.get(name)
    if cls is None:
        raise ValueError(f"Unknown weapon: {name!r}")
    return cls()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(dx: float, dy: float) -> tuple[float, float]:
    length = math.sqrt(dx*dx + dy*dy)
    if length < 1e-6:
        return 1.0, 0.0
    return dx / length, dy / length