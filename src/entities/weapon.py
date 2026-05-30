"""
weapon.py - Weapon system for Mutagen Arena.
Owner: Joson (Elijah)

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

TEAMMATE INTERFACE (wave_manager.py / Tabuena):
  After player fires, iterate over all weapons in player.loadout:
    for weapon in player.loadout:
        for proj  in weapon.projectiles:    # Projectile objects
        for swing in weapon.swing_hitboxes: # SwingHitbox objects
        for trap  in weapon.traps:          # Trap objects

  Each threat object has: .x .y .radius .damage .alive
  Set  .alive = False  to consume/destroy the threat after a hit.
  For Trap: also call  trap.trigger()  to play the trigger animation.
"""

import pygame
import math
import random
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
    ):
        self.x, self.y        = x, y
        self.dx, self.dy      = dx, dy
        self.speed            = speed_units * SPEED_SCALE  # px/s
        self.damage           = damage
        self.radius           = radius
        self.color            = color
        self.max_range        = max_range
        self.lifespan         = lifespan

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
        # Trail
        for i, (tx, ty) in enumerate(self._trail):
            sx, sy = camera.world_to_screen(tx, ty)
            alpha  = int(160 * (i / max(len(self._trail), 1)))
            tr     = max(1, self.radius - (len(self._trail) - i))
            s = pygame.Surface((tr*2+2, tr*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color[:3], alpha), (tr+1, tr+1), tr)
            surf.blit(s, (int(sx) - tr - 1, int(sy) - tr - 1))
        # Body
        sx, sy = camera.world_to_screen(self.x, self.y)
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
        alpha  = int(180 * (1.0 - self.progress))
        # Draw a semi-transparent arc / circle
        s = pygame.Surface((int(self.radius)*2+4, int(self.radius)*2+4),
                           pygame.SRCALPHA)
        pygame.draw.circle(
            s, (*C_SWING[:3], alpha),
            (int(self.radius)+2, int(self.radius)+2),
            int(self.radius)
        )
        surf.blit(s, (int(sx) - int(self.radius) - 2,
                      int(sy) - int(self.radius) - 2))
        # Outline
        pygame.draw.circle(surf, C_SWING,
                           (int(sx), int(sy)), int(self.radius), 2)


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
    TRIGGER_VISUAL_DURATION = 0.6   # seconds to show explosion before removal

    def __init__(self, x: float, y: float, damage: int, radius: float):
        self.x, self.y    = x, y
        self.damage       = damage
        self.radius       = radius
        self.alive        = True
        self.triggered    = False
        self._vis_timer   = 0.0
        self._idle_pulse  = 0.0   # animation timer

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
        self.projectiles.append(Projectile(
            px, py, dx, dy,
            speed_units = self._proj_speed,
            damage      = self.damage,
            radius      = self._proj_radius,
            color       = self.color,
            max_range   = self.range,
            lifespan    = self._proj_lifespan,
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
        # Slight spread for visual feel
        spread = random.uniform(-0.04, 0.04)
        dx2    = dx * math.cos(spread) - dy * math.sin(spread)
        dy2    = dx * math.sin(spread) + dy * math.cos(spread)
        self.projectiles.append(Projectile(
            px, py, dx2, dy2,
            speed_units = self._proj_speed,
            damage      = self.damage,
            radius      = self._proj_radius,
            color       = self.color,
            max_range   = self.range,
            lifespan    = self._proj_lifespan,
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

    TEAMMATE (Tabuena — wave_manager.py):
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