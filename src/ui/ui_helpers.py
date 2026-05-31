"""
ui_helpers.py — Shared drawing primitives for the MutaGen Arena UI.

Provides reusable rendering functions: pill bars, panels, scanlines,
vignette, particles, color utilities, and fade transitions.
"""
import pygame
import math
import random

# ── Color Utilities ───────────────────────────────────────────────────────────

def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    """Linearly interpolate between two RGB(A) colors."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def brighten(color: tuple, factor: float = 1.3) -> tuple:
    """Brighten an RGB color by a factor, capping at 255."""
    return tuple(min(255, int(c * factor)) for c in color[:3])


def dim(color: tuple, factor: float = 0.5) -> tuple:
    """Dim an RGB color by a factor."""
    return tuple(max(0, int(c * factor)) for c in color[:3])


def with_alpha(color: tuple, alpha: int) -> tuple:
    """Return color with a specific alpha value."""
    return (*color[:3], alpha)


def pulse_color(color: tuple, factor: float) -> tuple:
    """Multiply color by a factor, clamping each channel to [0, 255].

    Safe to use with oscillating values like sin() that might overshoot.
    """
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


# ── Pill Bar ──────────────────────────────────────────────────────────────────

def draw_pill_bar(
    surf: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ratio: float,
    fg_color: tuple,
    bg_color: tuple = (20, 24, 40),
    glow_color: tuple | None = None,
    border_color: tuple = (50, 60, 80),
    border_radius: int = -1,
) -> None:
    """
    Draw a rounded bar with optional glow halo effect.
    ratio: 0.0 to 1.0
    """
    ratio = max(0.0, min(1.0, ratio))
    if border_radius < 0:
        border_radius = h // 2

    # Glow halo (drawn behind bar)
    if glow_color and ratio > 0:
        glow_surf = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        glow_rect = pygame.Rect(0, 0, max(8, int(w * ratio) + 8), h + 8)
        pygame.draw.rect(glow_surf, (*glow_color[:3], 35), glow_rect,
                         border_radius=border_radius + 2)
        surf.blit(glow_surf, (x - 4, y - 4))

    # Background
    bg_rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surf, bg_color, bg_rect, border_radius=border_radius)

    # Fill
    if ratio > 0:
        fill_w = max(border_radius * 2, int(w * ratio))
        fill_rect = pygame.Rect(x, y, fill_w, h)
        pygame.draw.rect(surf, fg_color, fill_rect, border_radius=border_radius)

        # Highlight stripe (top third of bar, lighter color)
        hl_h = max(1, h // 3)
        hl_surf = pygame.Surface((fill_w, hl_h), pygame.SRCALPHA)
        hl_surf.fill((*brighten(fg_color, 1.4)[:3], 50))
        surf.blit(hl_surf, (x, y))

    # Border
    pygame.draw.rect(surf, border_color, bg_rect, 1, border_radius=border_radius)


# ── Panel ─────────────────────────────────────────────────────────────────────

def draw_panel(
    surf: pygame.Surface,
    rect: pygame.Rect,
    border_color: tuple = (50, 70, 100),
    bg_color: tuple = (8, 12, 24, 200),
    border_width: int = 1,
    border_radius: int = 6,
) -> None:
    """Draw a semi-transparent panel with neon border."""
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    panel.fill(bg_color)
    surf.blit(panel, rect.topleft)
    pygame.draw.rect(surf, border_color, rect, border_width,
                     border_radius=border_radius)


# ── Scanlines ─────────────────────────────────────────────────────────────────

def draw_scanlines(
    surf: pygame.Surface,
    rect: pygame.Rect | None = None,
    alpha: int = 12,
    spacing: int = 3,
) -> None:
    """Overlay faint horizontal scanlines for CRT aesthetic."""
    if rect is None:
        rect = surf.get_rect()
    scanline_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    for y_offset in range(0, rect.h, spacing):
        pygame.draw.line(scanline_surf, (0, 0, 0, alpha),
                         (0, y_offset), (rect.w, y_offset))
    surf.blit(scanline_surf, rect.topleft)


# ── Vignette ──────────────────────────────────────────────────────────────────

_vignette_cache: pygame.Surface | None = None
_vignette_size: tuple = (0, 0)

def draw_vignette(surf: pygame.Surface, intensity: int = 120) -> None:
    """Darken the screen edges for a cinematic vignette effect."""
    global _vignette_cache, _vignette_size
    sw, sh = surf.get_size()

    if _vignette_cache is None or _vignette_size != (sw, sh):
        _vignette_cache = pygame.Surface((sw, sh), pygame.SRCALPHA)
        cx, cy = sw // 2, sh // 2
        max_dist = math.sqrt(cx * cx + cy * cy)
        # Build radial gradient with concentric rects for performance
        steps = 20
        for i in range(steps):
            frac = i / steps
            alpha = int(intensity * (frac ** 2))
            r = int(max_dist * (1 - frac))
            vr = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
            vr.clamp_ip(pygame.Rect(0, 0, sw, sh))
            border_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            # Draw border ring
            pygame.draw.rect(border_surf, (0, 0, 0, alpha),
                             pygame.Rect(0, 0, sw, sh))
            inner = pygame.Rect(
                int(sw * frac * 0.5), int(sh * frac * 0.5),
                int(sw * (1 - frac)), int(sh * (1 - frac))
            )
            pygame.draw.rect(border_surf, (0, 0, 0, 0), inner)
            _vignette_cache.blit(border_surf, (0, 0))
        _vignette_size = (sw, sh)

    surf.blit(_vignette_cache, (0, 0))


# ── Particle System ──────────────────────────────────────────────────────────

class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'color', 'size')

    def __init__(self, x: float, y: float, color: tuple,
                 vx: float = 0, vy: float = -15,
                 life: float = 3.0, size: float = 2.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size


class ParticleSystem:
    """Lightweight ambient particle emitter."""

    def __init__(self, count: int = 30, bounds: tuple = (1280, 720),
                 color: tuple = (60, 180, 120)):
        self.bounds = bounds
        self.base_color = color
        self.particles: list[Particle] = []
        for _ in range(count):
            self._spawn()

    def _spawn(self) -> None:
        x = random.uniform(0, self.bounds[0])
        y = random.uniform(0, self.bounds[1])
        vx = random.uniform(-8, 8)
        vy = random.uniform(-20, -5)
        life = random.uniform(2.0, 5.0)
        size = random.uniform(1.0, 3.0)
        c = tuple(min(255, max(0, v + random.randint(-20, 20)))
                  for v in self.base_color[:3])
        self.particles.append(Particle(x, y, c, vx, vy, life, size))

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
        # Remove dead, respawn
        dead = [p for p in self.particles if p.life <= 0]
        self.particles = [p for p in self.particles if p.life > 0]
        for _ in dead:
            self._spawn()

    def draw(self, surf: pygame.Surface) -> None:
        for p in self.particles:
            alpha = int(255 * (p.life / p.max_life) * 0.6)
            alpha = max(0, min(255, alpha))
            sz = max(1, int(p.size * (p.life / p.max_life)))
            ps = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*p.color[:3], alpha), (sz, sz), sz)
            surf.blit(ps, (int(p.x) - sz, int(p.y) - sz))


# ── Fade Transition ───────────────────────────────────────────────────────────

def draw_fade(surf: pygame.Surface, alpha: int) -> None:
    """Full-screen fade overlay. alpha: 0 (transparent) to 255 (opaque black)."""
    if alpha <= 0:
        return
    alpha = min(255, alpha)
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    surf.blit(overlay, (0, 0))


# ── Glitch Text ───────────────────────────────────────────────────────────────

_GLITCH_CHARS = "!@#$%^&*<>?/\\|{}[]~`"

def render_glitch_text(
    font: pygame.font.Font,
    text: str,
    color: tuple,
    glitch_intensity: float = 0.0,
) -> pygame.Surface:
    """
    Render text with random character substitution for a glitch effect.
    glitch_intensity: 0.0 (no glitch) to 1.0 (fully garbled)
    """
    if glitch_intensity <= 0:
        return font.render(text, True, color)

    glitched = ""
    for ch in text:
        if ch != " " and random.random() < glitch_intensity * 0.3:
            glitched += random.choice(_GLITCH_CHARS)
        else:
            glitched += ch
    return font.render(glitched, True, color)


# ── Animated Bar Lerp Helper ─────────────────────────────────────────────────

def smooth_approach(current: float, target: float, speed: float, dt: float) -> float:
    """Smoothly approach a target value."""
    diff = target - current
    if abs(diff) < 0.001:
        return target
    return current + diff * min(1.0, speed * dt)


# ── Weapon Icon Renderer ─────────────────────────────────────────────────────

def draw_weapon_icon(surf: pygame.Surface, x: int, y: int, size: int,
                     weapon_type: str, color: tuple) -> None:
    """Draw a simple geometric icon representing a weapon type."""
    cx, cy = x + size // 2, y + size // 2
    r = size // 2 - 2

    if weapon_type == "ranged":
        # Crosshair icon
        pygame.draw.circle(surf, color, (cx, cy), r, 2)
        pygame.draw.circle(surf, color, (cx, cy), r // 2, 1)
        pygame.draw.line(surf, color, (cx - r, cy), (cx + r, cy), 1)
        pygame.draw.line(surf, color, (cx, cy - r), (cx, cy + r), 1)

    elif weapon_type == "melee":
        # Blade / sword icon
        points = [
            (cx, cy - r),
            (cx + r // 3, cy + r // 2),
            (cx, cy + r // 3),
            (cx - r // 3, cy + r // 2),
        ]
        pygame.draw.polygon(surf, color, points, 2)
        pygame.draw.line(surf, color, (cx - r // 2, cy + r * 2 // 3),
                         (cx + r // 2, cy + r * 2 // 3), 2)

    elif weapon_type == "utility":
        # Trap / diamond icon
        points = [
            (cx, cy - r),
            (cx + r, cy),
            (cx, cy + r),
            (cx - r, cy),
        ]
        pygame.draw.polygon(surf, color, points, 2)
        pygame.draw.circle(surf, color, (cx, cy), r // 3, 1)

    else:
        # Generic dot
        pygame.draw.circle(surf, color, (cx, cy), r, 2)


# ── Upgrade Stat Icons ────────────────────────────────────────────────────────

def draw_stat_icon(surf: pygame.Surface, cx: int, cy: int, size: int,
                   stat: str, color: tuple) -> None:
    """Draw a geometric icon for a stat type using pygame primitives."""
    r = size // 2
    dc = dim(color, 0.7)  # dimmer variant for accents

    if stat == "speed":
        # Lightning bolt
        points = [
            (cx - r // 3, cy - r),
            (cx + r // 2, cy - r),
            (cx + r // 6, cy - r // 6),
            (cx + r // 2, cy - r // 6),
            (cx - r // 4, cy + r),
            (cx, cy + r // 6),
            (cx - r // 2, cy + r // 6),
        ]
        pygame.draw.polygon(surf, color, points, 0)
        pygame.draw.polygon(surf, brighten(color), points, 2)

    elif stat == "max_hp":
        # Heart shape
        s = r * 2 // 3
        pygame.draw.circle(surf, color, (cx - s // 2, cy - s // 3), s // 2)
        pygame.draw.circle(surf, color, (cx + s // 2, cy - s // 3), s // 2)
        points = [
            (cx - r + 2, cy - r // 6),
            (cx, cy + r - 2),
            (cx + r - 2, cy - r // 6),
        ]
        pygame.draw.polygon(surf, color, points, 0)
        # Highlight
        pygame.draw.circle(surf, brighten(color), (cx - s // 2 - 1, cy - s // 3 - 2), s // 4)

    elif stat == "max_stamina":
        # Diamond / gem
        points = [
            (cx, cy - r + 2),
            (cx + r - 2, cy),
            (cx, cy + r - 2),
            (cx - r + 2, cy),
        ]
        pygame.draw.polygon(surf, color, points, 0)
        pygame.draw.polygon(surf, brighten(color), points, 2)
        # Inner facet
        pygame.draw.line(surf, dc, (cx, cy - r + 2), (cx + r // 3, cy), 1)
        pygame.draw.line(surf, dc, (cx, cy - r + 2), (cx - r // 3, cy), 1)

    elif stat == "damage":
        # Crossed swords / X slash
        lw = max(2, r // 4)
        pygame.draw.line(surf, color,
                         (cx - r + 3, cy - r + 3), (cx + r - 3, cy + r - 3), lw)
        pygame.draw.line(surf, color,
                         (cx + r - 3, cy - r + 3), (cx - r + 3, cy + r - 3), lw)
        # Guard / center diamond
        gr = r // 3
        guard_pts = [(cx, cy - gr), (cx + gr, cy), (cx, cy + gr), (cx - gr, cy)]
        pygame.draw.polygon(surf, brighten(color), guard_pts, 0)
        pygame.draw.polygon(surf, color, guard_pts, 1)

    elif stat == "cooldown":
        # Clock / circular arrow
        pygame.draw.circle(surf, color, (cx, cy), r - 2, 2)
        # Clock hands
        pygame.draw.line(surf, brighten(color), (cx, cy), (cx, cy - r + 6), 2)
        pygame.draw.line(surf, brighten(color), (cx, cy), (cx + r // 2, cy), 2)
        # Center dot
        pygame.draw.circle(surf, brighten(color), (cx, cy), 3)
        # Arrow tip at 12 o'clock
        pygame.draw.polygon(surf, color, [
            (cx + r - 2, cy - 3), (cx + r + 3, cy), (cx + r - 2, cy + 3)
        ])

    elif stat == "dash":
        # Double chevron >>
        lw = max(2, r // 3)
        off = r // 2
        pygame.draw.lines(surf, color, False, [
            (cx - off - r // 3, cy - r + 4),
            (cx - off + r // 3, cy),
            (cx - off - r // 3, cy + r - 4),
        ], lw)
        pygame.draw.lines(surf, brighten(color), False, [
            (cx + off - r // 3, cy - r + 4),
            (cx + off + r // 3, cy),
            (cx + off - r // 3, cy + r - 4),
        ], lw)

    elif stat == "stam_regen":
        # Circular arrow (recycling)
        pygame.draw.arc(surf, color,
                        (cx - r + 2, cy - r + 2, (r - 2) * 2, (r - 2) * 2),
                        0.3, math.pi * 1.7, 2)
        # Arrow head
        angle = 0.3
        ax = cx + int((r - 2) * math.cos(angle))
        ay = cy - int((r - 2) * math.sin(angle))
        pygame.draw.polygon(surf, color, [
            (ax, ay - 4), (ax + 6, ay + 2), (ax - 2, ay + 2)
        ])
        # Center dot
        pygame.draw.circle(surf, dc, (cx, cy), 3)

    elif stat == "proj_speed":
        # Right arrow
        lw = max(2, r // 3)
        # Shaft
        pygame.draw.line(surf, color, (cx - r + 4, cy), (cx + r // 3, cy), lw)
        # Arrow head
        pygame.draw.polygon(surf, brighten(color), [
            (cx + r - 3, cy),
            (cx + r // 4, cy - r // 2),
            (cx + r // 4, cy + r // 2),
        ])

    else:
        # Generic circle
        pygame.draw.circle(surf, color, (cx, cy), r - 2, 2)
        pygame.draw.circle(surf, brighten(color), (cx, cy), r // 3)

# Keep the old dict name for backward compat but it won't be used for rendering
STAT_ICONS = {
    "speed": "speed", "max_hp": "max_hp", "max_stamina": "max_stamina",
    "damage": "damage", "cooldown": "cooldown", "dash": "dash",
    "stam_regen": "stam_regen", "proj_speed": "proj_speed",
}

STAT_COLORS = {
    "speed":       (255, 220, 80),
    "max_hp":      (255, 80, 80),
    "max_stamina": (80, 160, 255),
    "damage":      (255, 140, 60),
    "cooldown":    (120, 220, 255),
    "dash":        (180, 255, 180),
    "stam_regen":  (100, 180, 255),
    "proj_speed":  (255, 200, 100),
}

