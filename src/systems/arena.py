"""Combat phase: spawn queue, entity update, collisions, lethality recording."""
import random
import math
import pygame
from src.entities.player import Player
from src.systems.enemy import Enemy
from src.ai.chromosome import Chromosome
from src.data.lethality_log import LethalityLog, EnemyRecord
from src.core.constants import ARENA_W, ARENA_H, MIN_SPAWN_DISTANCE

SPAWN_BATCH_SIZE = 5
SPAWN_INTERVAL   = 8.0

class Arena:
    def __init__(self, player: Player, lethality_log: LethalityLog):
        self.player = player
        self.lethality = lethality_log
        self.enemies: list[Enemy] = []
        self.enemy_bullets = []
        self.spawn_queue: list[Chromosome] = []
        self.spawn_timer: float = 0.0
        self.wave_complete: bool = False
        
        self.bg_surface = pygame.Surface((ARENA_W, ARENA_H))
        self.bg_surface.fill((15, 20, 35))
        
        try:
            # Scale down to 2.0 so the tiles aren't massive
            floor_img = pygame.transform.scale_by(pygame.image.load("assets/environment/floor_tile.png").convert_alpha(), 0.5)
            
            # FIXED: Looking for "wall_down.png" to match your file!
            wall_top    = pygame.transform.scale_by(pygame.image.load("assets/environment/wall_top.png").convert_alpha(), 5.0)
            wall_bottom = pygame.transform.scale_by(pygame.image.load("assets/environment/wall_down.png").convert_alpha(), 5.0) 
            wall_left   = pygame.transform.scale_by(pygame.image.load("assets/environment/wall_left.png").convert_alpha(), 5.0)
            wall_right  = pygame.transform.scale_by(pygame.image.load("assets/environment/wall_right.png").convert_alpha(), 5.0)
            
            # 1. Fill the ENTIRE arena with floor tiles
            fw, fh = floor_img.get_width(), floor_img.get_height()
            for x in range(0, ARENA_W, fw):
                for y in range(0, ARENA_H, fh):
                    self.bg_surface.blit(floor_img, (x, y))
                    
            # 2. Draw the Top and Bottom walls
            wt, ht = wall_top.get_width(), wall_top.get_height()
            wb, hb = wall_bottom.get_width(), wall_bottom.get_height()
            for x in range(0, ARENA_W, wt):
                self.bg_surface.blit(wall_top, (x, 0))
            for x in range(0, ARENA_W, wb):
                self.bg_surface.blit(wall_bottom, (x, ARENA_H - hb))
                
            # 3. Draw the Left and Right walls
            wl, hl = wall_left.get_width(), wall_left.get_height()
            wr, hr = wall_right.get_width(), wall_right.get_height()
            for y in range(0, ARENA_H, hl):
                self.bg_surface.blit(wall_left, (0, y))
            for y in range(0, ARENA_H, hr):
                self.bg_surface.blit(wall_right, (ARENA_W - wr, y))
                
        except Exception as e:
            print(f"Arena background load failed: {e}")

    def begin_wave(self, chromosomes: list[Chromosome], is_boss: bool = False, 
        boss_chrom: Chromosome | None = None, 
        boss_img_path: str | None = None) -> None:
        self.enemies.clear()
        self.enemy_bullets.clear()
        self.lethality.clear()
        self.spawn_queue = list(chromosomes)
        self.spawn_timer = 0.0
        self.wave_complete = False

        if is_boss and boss_chrom and boss_img_path:
            # Put the boss directly in the center of the arena while the rest of the wave queues up
            from src.core.constants import ARENA_W, ARENA_H
            spawn_x = ARENA_W / 2
            spawn_y = ARENA_H / 2 
            
            # Note: Make sure 'Enemy' is imported at the top of your arena.py file!
            boss_enemy = Enemy(boss_chrom, (spawn_x, spawn_y), is_boss=True, boss_img_path=boss_img_path)
            self.enemies.append(boss_enemy)

    def get_safe_spawn_point(self, player_x: float, player_y: float) -> tuple[float, float]:
        """Ensures enemies do not spawn directly on top of the player."""
        for _ in range(100):  # max 100 attempts to prevent infinite loop
            spawn_x = random.uniform(50, ARENA_W - 50)
            spawn_y = random.uniform(50, ARENA_H - 50)
            if math.hypot(spawn_x - player_x, spawn_y - player_y) >= MIN_SPAWN_DISTANCE:
                return spawn_x, spawn_y
        return 50.0, 50.0 # Fallback

    def update(self, dt: float) -> None:
        # 1. Staggered Spawning
        if self.spawn_queue:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                batch = [self.spawn_queue.pop(0) for _ in range(min(SPAWN_BATCH_SIZE, len(self.spawn_queue)))]
                for chrom in batch:
                    safe_pos = self.get_safe_spawn_point(self.player.x, self.player.y)
                    self.enemies.append(Enemy(chrom, safe_pos))
                self.spawn_timer = SPAWN_INTERVAL

        # 2. Update Enemies & Enemy Bullets
        for e in self.enemies:
            e.update(dt, self.player, self.enemies, self.enemy_bullets)
            
        for b in self.enemy_bullets:
            b.update(dt)
            if b.alive and math.hypot(b.x - self.player.x, b.y - self.player.y) < self.player.radius + b.radius:
                self.player.take_damage(b.damage)
                b.alive = False

        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]

        # 3. Collision: Member 3's Weapons vs Enemies
        for weapon in self.player.loadout:
            for proj in weapon.projectiles:
                if not proj.alive: continue
                for e in self.enemies:
                    if e.alive and math.hypot(proj.x - e.x, proj.y - e.y) < e.radius + proj.radius:
                        e.take_damage(proj.damage)
                        proj.alive = False
                        break

            for swing in weapon.swing_hitboxes:
                if not swing.alive: continue
                for e in self.enemies:
                    if e.alive and id(e) not in swing.already_hit:
                        if math.hypot(swing.x - e.x, swing.y - e.y) < swing.radius + e.radius:
                            e.take_damage(swing.damage)
                            swing.already_hit.add(id(e))

            for trap in weapon.traps:
                if not trap.alive or trap.triggered: continue
                for e in self.enemies:
                    if e.alive and math.hypot(trap.x - e.x, trap.y - e.y) < trap.radius + e.radius:
                        trap.trigger()
                        e.take_damage(trap.damage)

        # 4. Reap dead enemies and record data
        for e in self.enemies:
            if not e.alive and e.chrom.id not in self.lethality.all():
                self.lethality.record(EnemyRecord(
                    chromosome_id=e.chrom.id,
                    archetype=e.chrom.archetype,
                    survival_sec=e.survival_sec,
                    damage_dealt=e.damage_dealt,
                ))
        self.enemies = [e for e in self.enemies if e.alive]

        # 5. Check Wave Complete
        if not self.spawn_queue and not self.enemies:
            self.wave_complete = True

    def finalize_survivors(self) -> None:
        for e in self.enemies:
            if e.chrom.id not in self.lethality.all():
                self.lethality.record(EnemyRecord(
                    chromosome_id=e.chrom.id,
                    archetype=e.chrom.archetype,
                    survival_sec=e.survival_sec,
                    damage_dealt=e.damage_dealt,
                ))

    def draw(self, screen: pygame.Surface, camera) -> None:
        # --- NEW ENVIRONMENT DRAWING CODE ---
        screen_x, screen_y = camera.world_to_screen(0, 0)
        screen.blit(self.bg_surface, (int(screen_x), int(screen_y)))

        for b in self.enemy_bullets:
            b.draw(screen, camera)
        for e in self.enemies:
            e.draw(screen, camera)

    def enemies_remaining(self) -> int:
        return len(self.spawn_queue) + len(self.enemies)