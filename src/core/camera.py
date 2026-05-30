"""
camera.py - Viewport / camera system.

The arena (2560×1440) is larger than the screen (1280×720).
The camera follows the player and all entities draw using world coords
converted to screen coords via camera.world_to_screen().

TEAMMATES: import Camera from here and pass the camera instance into
every entity's draw() call, and use camera.screen_to_world(mouse_pos)
to convert mouse input to world space.
"""

from src.core.constants import SCREEN_W, SCREEN_H, ARENA_W, ARENA_H


class Camera:
    def __init__(self):
        self.x = 0.0   # world X of the top-left corner of the viewport
        self.y = 0.0

    def follow(self, target_x: float, target_y: float):
        """Center viewport on target, clamped to arena bounds."""
        self.x = target_x - SCREEN_W / 2
        self.y = target_y - SCREEN_H / 2
        # Clamp so we never show outside the arena
        self.x = max(0.0, min(self.x, ARENA_W - SCREEN_W))
        self.y = max(0.0, min(self.y, ARENA_H - SCREEN_H))

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """Convert world coordinates → screen coordinates for drawing."""
        return wx - self.x, wy - self.y

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert screen coordinates → world coordinates (e.g. mouse pos)."""
        return sx + self.x, sy + self.y

    def is_visible(self, wx: float, wy: float, margin: float = 60.0) -> bool:
        """Returns True if the world point is within the visible viewport."""
        sx, sy = self.world_to_screen(wx, wy)
        return (-margin <= sx <= SCREEN_W + margin and
                -margin <= sy <= SCREEN_H + margin)

    def rect_visible(self, wx, wy, w, h) -> bool:
        """Returns True if a world-space rect overlaps the viewport."""
        sx, sy = self.world_to_screen(wx, wy)
        return (sx + w >= 0 and sx <= SCREEN_W and
                sy + h >= 0 and sy <= SCREEN_H)