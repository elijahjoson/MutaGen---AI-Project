"""enemy.py - Handles all enemy archetypes and their unique behaviors."""
import pygame
import math
from src.ai.chromosome import Chromosome, Archetype
from src.core.constants import ARCHETYPES, SPEED_SCALE, ARENA_H, ARENA_W
from src.systems.bullet import EnemyBullet
from src.entities.weapon import Projectile


class Enemy:
    def __init__(self, chrom: Chromosome, pos: tuple[float, float]):
        self.chrom = chrom
        self.x, self.y = pos
        self.hp = float(chrom.hp)
        self.max_hp = float(chrom.hp)
        self.attack_cd = 0.0
        self.survival_sec = 0.0
        self.damage_dealt = 0.0
        self.alive = True

        cfg = ARCHETYPES[chrom.archetype.value]
        self.color = cfg["color"]
        self.radius = cfg["radius"]
        self.attack_range = cfg.get("attack_range", 0)
        self.aoe_range = cfg.get("aoe_range", 0)

    def take_damage(self, amount: float):
        actual_damage = amount * (1.0 - self.chrom.resistance)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.alive = False

    def update(self, dt: float, player, all_enemies: list, enemy_bullets: list) -> None:
        if not self.alive:
            return

        self.survival_sec += dt
        self.attack_cd = max(0.0, self.attack_cd - dt)

        if self.chrom.archetype in (Archetype.TANK, Archetype.STRIKER):
            self._steer_towards(player.x, player.y, dt)
            if (math.hypot(player.x - self.x, player.y - self.y) < self.attack_range + player.radius
                    and self.attack_cd <= 0):
                player.take_damage(self.chrom.damage)
                self.damage_dealt += self.chrom.damage
                self.attack_cd = self.chrom.attack_cd

        elif self.chrom.archetype == Archetype.RANGED:
            dist = math.hypot(player.x - self.x, player.y - self.y)
            if dist > self.attack_range:
                self._steer_towards(player.x, player.y, dt)
            elif self.attack_cd <= 0:
                # 1. Calculate direction
                dx = (player.x - self.x) / dist
                dy = (player.y - self.y) / dist
                
                # 2. Spawn the universal Projectile (uses the asset path!)
                enemy_bullets.append(Projectile(
                    self.x, self.y, dx, dy,
                    speed_units=ARCHETYPES["Ranged"]["projectile_speed"],
                    damage=self.chrom.damage,
                    radius=5, # Or your preferred size
                    color=(255, 0, 0),
                    max_range=500,
                    lifespan=2.0,
                    image_path="assets/sprites/enemies/bullet_enemy.png" # Updated path
                ))
                
                self.damage_dealt += self.chrom.damage
                self.attack_cd = self.chrom.attack_cd

        elif self.chrom.archetype == Archetype.SUPPORT:
            weakest_ally = min(
                [e for e in all_enemies if e.alive and e != self],
                key=lambda e: e.hp / e.max_hp,
                default=None
            )
            if weakest_ally and (weakest_ally.hp / weakest_ally.max_hp) < 1.0:
                self._steer_towards(weakest_ally.x, weakest_ally.y, dt)
                if (math.hypot(weakest_ally.x - self.x, weakest_ally.y - self.y) <= self.aoe_range
                        and self.attack_cd <= 0):
                    heal_amount = min(weakest_ally.max_hp - weakest_ally.hp, self.chrom.damage)
                    weakest_ally.hp += heal_amount
                    self.damage_dealt += heal_amount
                    self.attack_cd = self.chrom.attack_cd
            else:
                self._steer_towards(player.x, player.y, dt)

    def _steer_towards(self, target_x: float, target_y: float, dt: float):
        angle = math.atan2(target_y - self.y, target_x - self.x)
        self.x += math.cos(angle) * self.chrom.speed * SPEED_SCALE * dt
        self.y += math.sin(angle) * self.chrom.speed * SPEED_SCALE * dt
        self._clamp_to_arena()

    def _steer_away(self, target_x: float, target_y: float, dt: float):
        angle = math.atan2(target_y - self.y, target_x - self.x)
        self.x -= math.cos(angle) * self.chrom.speed * SPEED_SCALE * dt
        self.y -= math.sin(angle) * self.chrom.speed * SPEED_SCALE * dt
        self._clamp_to_arena()

    def _clamp_to_arena(self):
        THICK_TOP    = 100
        THICK_BOTTOM = 40
        THICK_LEFT   = 16
        THICK_RIGHT  = 16
        
        # Calculate the safe inner bounds using the custom thicknesses
        min_x = THICK_LEFT + self.radius
        max_x = ARENA_W - THICK_RIGHT - self.radius
        min_y = THICK_TOP + self.radius
        max_y = ARENA_H - THICK_BOTTOM - self.radius

        self.x = max(float(min_x), min(float(max_x), self.x))
        self.y = max(float(min_y), min(float(max_y), self.y))

    def draw(self, screen: pygame.Surface, camera) -> None:
        if not self.alive:
            return
        sx, sy = camera.world_to_screen(self.x, self.y)
        if self.chrom.archetype == Archetype.SUPPORT and self.attack_cd <= 0:
            pygame.draw.circle(screen, (100, 255, 100),
                               (int(sx), int(sy)), self.aoe_range, 1)
        pygame.draw.circle(screen, self.color, (int(sx), int(sy)), self.radius)
        hp_ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(screen, (255, 0, 0),
                         (sx - 15, sy - self.radius - 10, 30, 4))
        pygame.draw.rect(screen, (0, 255, 0),
                         (sx - 15, sy - self.radius - 10, int(30 * hp_ratio), 4))