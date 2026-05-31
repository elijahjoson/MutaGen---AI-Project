"""bullet.py - Enemy projectiles."""
import pygame
import math
from src.core.constants import SPEED_SCALE, ARENA_W, ARENA_H

class EnemyBullet:
    def __init__(self, x: float, y: float, target_x: float, target_y: float, damage: int, speed: float):
        self.x = x
        self.y = y
        self.damage = damage
        self.radius = 6
        self.speed = speed * SPEED_SCALE
        self.alive = True
        
        # Calculate direction
        angle = math.atan2(target_y - y, target_x - x)
        self.dx = math.cos(angle)
        self.dy = math.sin(angle)

    def update(self, dt: float):
        if not self.alive:
            return
            
        self.x += self.dx * self.speed * dt
        self.y += self.dy * self.speed * dt
        
        # Kill bullet if it leaves the arena boundaries
        if not (0 <= self.x <= ARENA_W and 0 <= self.y <= ARENA_H):
            self.alive = False

    def draw(self, surf: pygame.Surface, camera):
        if not self.alive:
            return
        sx, sy = camera.world_to_screen(self.x, self.y)
        pygame.draw.circle(surf, (255, 100, 100), (int(sx), int(sy)), self.radius)