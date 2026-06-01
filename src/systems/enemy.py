"""enemy.py - Handles all enemy archetypes and their unique behaviors."""
import pygame
import math
from src.ai.chromosome import Chromosome, Archetype
from src.core.constants import ARCHETYPES, SPEED_SCALE, ARENA_H, ARENA_W
from src.systems.bullet import EnemyBullet
from src.entities.weapon import Projectile


class Enemy:
    def __init__(self, chrom: Chromosome, pos: tuple[float, float], is_boss: bool = False, boss_img_path: str = None):
        self.chrom = chrom
        self.x, self.y = pos
        self.hp = float(chrom.hp)
        self.max_hp = float(chrom.hp)
        self.attack_cd = 0.0
        self.survival_sec = 0.0
        self.damage_dealt = 0.0
        self.alive = True
        self.dying = False
        self.death_timer = 0.5

        cfg = ARCHETYPES[chrom.archetype.value]
        self.color = cfg["color"]
        self.radius = cfg["radius"]
        self.attack_range = cfg.get("attack_range", 0)
        self.aoe_range = cfg.get("aoe_range", 0)

        if is_boss:
            self.hp = float(chrom.hp) * 10.0      # Boss has 10x HP
            self.max_hp = float(chrom.hp) * 10.0
            self.chrom.damage *= 2.5              # Boss hits 2.5x harder
            self.chrom.speed *= 0.8               # Boss moves slightly slower (optional)
            self.radius *= 5.0
        else:
            self.hp = float(chrom.hp)
            self.max_hp = float(chrom.hp)

        # --- NEW: VISUAL ASSET LOADING ---
        if is_boss and boss_img_path:
            raw_img = pygame.image.load(boss_img_path).convert_alpha()
            size = int(self.radius * 5) # Boss is 3x bigger than a normal slime
        else:
            arch_name = chrom.archetype.name.lower()
            if arch_name == "tank":
                raw_img = pygame.image.load("assets/sprites/enemies/tank.png").convert_alpha()
            elif arch_name == "striker":
                raw_img = pygame.image.load("assets/sprites/enemies/striker.png").convert_alpha()
            elif arch_name == "ranged":
                raw_img = pygame.image.load("assets/sprites/enemies/ranger.png").convert_alpha()
            elif arch_name == "support":
                raw_img = pygame.image.load("assets/sprites/enemies/support.png").convert_alpha()
            else:
                raw_img = pygame.Surface((64, 64), pygame.SRCALPHA)
                raw_img.fill((255, 0, 0))

        # Dynamically scale the slime to perfectly fit your archetype's radius
        size = int(self.radius * 2)
        self.image = pygame.transform.smoothscale(raw_img, (size, size))
        self.rect = self.image.get_rect(center=(self.x, self.y))

        self.hit_timer = 0.0
        # Pygame trick: Trace the image and create a solid white silhouette perfectly matched to the slime
        mask = pygame.mask.from_surface(self.image)
        self.flash_image = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))

    def take_damage(self, amount: float):
        if self.dying:
            return
        actual_damage = amount * (1.0 - self.chrom.resistance)
        self.hp -= actual_damage
        self.hit_timer = 0.05
        if self.hp <= 0:
            self.dying = True

    def update(self, dt: float, player, all_enemies: list, enemy_bullets: list) -> None:
        if not self.alive:
            return
        if self.dying:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.alive = False # Finally remove it from the game
            return

        self.survival_sec += dt
        self.attack_cd = max(0.0, self.attack_cd - dt)

        if self.hit_timer > 0:
            self.hit_timer -= dt

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
        
        # 1. Get the screen coordinates from the camera
        sx, sy = camera.world_to_screen(self.x, self.y)
        
        if self.dying:
            # Calculate a ratio from 1.0 down to 0.0
            ratio = max(0, self.death_timer / 0.5)
            
            # Shrink the size
            current_size = int((self.radius * 2) * ratio)
            
            if current_size > 0:
                # Scale the image down and stamp it
                melt_img = pygame.transform.smoothscale(self.image, (current_size, current_size))
                
                # Optional: Make it fade away (become transparent)
                melt_img.set_alpha(int(255 * ratio))
                
                melt_rect = melt_img.get_rect(center=(int(sx), int(sy)))
                screen.blit(melt_img, melt_rect)
            
            return

        # 2. Draw the support aura ring (if applicable) BEFORE the slime so it sits underneath
        if self.chrom.archetype.name == "SUPPORT" and self.attack_cd <= 0:
            # math.sin() creates a wave between -1 and 1 based on the clock.
            pulse = math.sin(pygame.time.get_ticks() * 0.005)
            # The radius expands and shrinks by 5 pixels smoothly
            pulsing_radius = self.aoe_range + (pulse * 5)
            
            # Draw it with a thickness of 2 so it looks like a real energy ring
            pygame.draw.circle(screen, (100, 255, 100), (int(sx), int(sy)), int(pulsing_radius), 2)

        # 3. Draw the Slime image!
        # We create a temporary rect centered on the camera coordinates to stamp the image perfectly
        img_rect = self.image.get_rect(center=(int(sx), int(sy)))
        
        if self.hit_timer > 0:
            # Stamp the pure white silhouette 
            screen.blit(self.flash_image, img_rect)
        else:
            # Stamp the normal colored slime
            screen.blit(self.image, img_rect)

        # 4. Draw the health bars on top
        hp_ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(screen, (255, 0, 0),
                         (sx - 15, sy - self.radius - 10, 30, 4))
        pygame.draw.rect(screen, (0, 255, 0),
                         (sx - 15, sy - self.radius - 10, int(30 * hp_ratio), 4))

        # 4. Draw the health bars on top
        hp_ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(screen, (255, 0, 0),
                         (sx - 15, sy - self.radius - 10, 30, 4))
        pygame.draw.rect(screen, (0, 255, 0),
                         (sx - 15, sy - self.radius - 10, int(30 * hp_ratio), 4))