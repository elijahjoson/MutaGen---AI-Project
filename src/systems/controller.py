"""GameController — owns all subsystems and the 5-state machine.

States: TITLE · LOADOUT · COMBAT · PAUSED · INTERMISSION · UPGRADE · VICTORY · DEFEAT

"""
from enum import Enum
import pygame
import math

# ── Updated imports: was mutagen_arena.settings ──────────────────────────────
from src.core.constants import (
    SCREEN_W as WIDTH,
    SCREEN_H as HEIGHT,
    PURGE_DURATION as UPLOAD_DURATION_SEC,
    ENEMIES_PER_WAVE,
    PLAYER_HP as PLAYER_MAX_HP,
    GA_W1 as W_SURVIVAL,
    GA_W2 as W_DAMAGE,
)

from src.ai.chromosome import (
    Archetype, Chromosome, TANK_BASELINE, STRIKER_BASELINE, RANGED_BASELINE, SUPPORT_BASELINE, GENE_RANGES, GENES,
)
from src.ai.evolve import evolve_population
from src.ai.annealing import temperature, heuristic_value
from src.ai.genetic import fitness

from src.data.lethality_log import LethalityLog
from src.data.genotype_registry import GenotypeRegistry
from src.data.ledger_diff import compute_ledger

from src.systems.arena import Arena
from src.systems.intermission import Intermission

from src.entities.player import Player
from src.core.camera import Camera
from src.ui.ledger_panel import draw_ledger, reset_intermission_anim
from src.ui.hud import HUDState, draw_hud
from src.ui.pause_menu import PauseMenu
from src.ui import font_manager as fm
from src.ui.ui_helpers import (
    draw_panel, draw_scanlines, draw_vignette,
    draw_pill_bar, lerp_color, brighten, dim, with_alpha,
    render_glitch_text, ParticleSystem, draw_fade, pulse_color,
)

# ── Sentience threshold ───────────────────────────────────────────────────────
# If any enemy reaches this fraction of theoretical max fitness, player loses.
# Adjust during playtesting if needed.
SENTIENCE_THRESHOLD = 0.85


class State(Enum):
    TITLE        = "title"
    LOADOUT      = "loadout"      # ← NEW: loadout selection before run starts
    COMBAT       = "combat"
    PAUSED       = "paused"
    INTERMISSION = "intermission"
    UPGRADE      = "upgrade"
    VICTORY      = "victory"
    DEFEAT       = "defeat"


def _baseline_wave() -> list[Chromosome]:
    return (
        [Chromosome.from_genes(Archetype.TANK,    list(TANK_BASELINE.genes))    for _ in range(5)]
      + [Chromosome.from_genes(Archetype.STRIKER, list(STRIKER_BASELINE.genes)) for _ in range(5)]
      + [Chromosome.from_genes(Archetype.RANGED,  list(RANGED_BASELINE.genes))  for _ in range(5)]
      + [Chromosome.from_genes(Archetype.SUPPORT, list(SUPPORT_BASELINE.genes)) for _ in range(5)]
    )


def _theoretical_max_fitness() -> float:
    """Upper bound used for SENTIENCE_THRESHOLD check.

    Highest possible fitness an enemy could plausibly achieve in 30 seconds:
      W_SURVIVAL * 30  +  W_DAMAGE * PLAYER_MAX_HP
    """
    return W_SURVIVAL * 120.0 + W_DAMAGE * 1000.0


class GameController:
    def __init__(self):
        self.running   = True
        self.state     = State.TITLE
        self.wave_n    = 0
        self.upload_pct = 0.0
        self.sa_temperature = 1.0
        self.previous_population: list[Chromosome] = []
        self.lethality_log = LethalityLog()
        self.registry      = GenotypeRegistry()
        self.camera        = Camera()
        self.player: Player | None = None
        self.arena:  Arena  | None = None
        self.intermission  = Intermission()
        self.debug_overlay = False
        self._fonts_ready  = False

        # UI state
        self._pause_menu = PauseMenu()
        self._title_particles = ParticleSystem(count=40, bounds=(WIDTH, HEIGHT),
                                                color=(60, 180, 120))
        self._end_particles: ParticleSystem | None = None
        self._title_time = 0.0
        self._end_time = 0.0
        self._end_fade_in = 255

        # Combat frame snapshot for pause overlay
        self._combat_snapshot: pygame.Surface | None = None

    # ── Font init (lazy, after pygame.init in main) ────────────────────────────

    def _ensure_fonts(self) -> None:
        if self._fonts_ready:
            return
        fm.init()
        self.font_title  = fm.title()
        self.font_header = fm.header()
        self.font_body   = fm.body()
        self.font_small  = fm.small()
        self._fonts_ready = True

    # ── State transitions ──────────────────────────────────────────────────────

    def _go_loadout(self) -> None:
        """TITLE → LOADOUT — show loadout selection screen."""
        self.state = State.LOADOUT

    def _start_run(self, loadout_names: list[str]) -> None:
        """LOADOUT → COMBAT — initialize a fresh run with chosen loadout.

        loadout_names: list of 2 weapon name strings from the loadout screen
           e.g. ["Pulse Rifle", "Shock Blade"]
           This replaces the original Player(pos=(...)) call.
        """
        self.wave_n     = 1
        self.upload_pct = 0.0
        self.lethality_log.clear()

        self.player = Player(loadout_names=loadout_names)
        self.arena  = Arena(self.player, self.lethality_log)

        baseline = _baseline_wave()
        self.registry.set_population(baseline)
        self.previous_population = list(baseline)
        self.arena.begin_wave(baseline)
        self.state = State.COMBAT

    def _enter_intermission(self) -> None:
        """COMBAT → INTERMISSION — run evolve and compute ledger."""
        old_pop = self.previous_population
        T = temperature(self.player.hp, self.player.max_hp)
        self.sa_temperature = T

        new_pop = evolve_population(
            prev_pop=self.registry.current(),
            lethality_log=self.lethality_log.all(),
            player_hp_frac=T,
        )
        ledger = compute_ledger(old_pop, new_pop)
        self.registry.set_population(new_pop)
        self.previous_population = list(new_pop)

        # HP regen at wave end — Member 3's player has regen_hp_wave() built in
        self.player.regen_hp_wave()

        self.intermission.begin(
            ledger=ledger,
            wave_finished=self.wave_n,
            sa_temperature=T,
        )

        # Reset intermission animations
        reset_intermission_anim()

        self.state = State.INTERMISSION

    def _start_next_wave(self) -> None:
        """INTERMISSION → COMBAT."""
        self.wave_n += 1
        self.lethality_log.clear()
        self.arena.begin_wave(self.registry.current())
        self.state = State.COMBAT

    def _go_victory(self) -> None:
        self.state = State.VICTORY
        self._end_time = 0.0
        self._end_fade_in = 255
        self._end_particles = ParticleSystem(count=50, bounds=(WIDTH, HEIGHT),
                                              color=(60, 220, 140))

    def _go_defeat(self) -> None:
        if self.arena is not None:
            self.arena.finalize_survivors()
        self.state = State.DEFEAT
        self._end_time = 0.0
        self._end_fade_in = 255
        self._end_particles = ParticleSystem(count=50, bounds=(WIDTH, HEIGHT),
                                              color=(200, 60, 60))

    def _reset_to_title(self) -> None:
        self.state      = State.TITLE
        self.wave_n     = 0
        self.upload_pct = 0.0
        self.player     = None
        self.arena      = None
        self._title_time = 0.0

    # ── Event handling ─────────────────────────────────────────────────────────

    def handle_events(self, events: list) -> None:
        for ev in events:
            if ev.type == pygame.QUIT:
                self.running = False

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F3:
                    self.debug_overlay = not self.debug_overlay

                if self.state is State.TITLE and ev.key == pygame.K_SPACE:
                    self._go_loadout()

                elif self.state is State.COMBAT and ev.key == pygame.K_ESCAPE:
                    # Capture combat frame for pause background
                    self._combat_snapshot = pygame.display.get_surface().copy()
                    self.state = State.PAUSED

                elif self.state is State.PAUSED:
                    action = self._pause_menu.handle_event(ev)
                    if action == "resume":
                        self.state = State.COMBAT
                        self._combat_snapshot = None
                    elif action == "restart":
                        self._reset_to_title()
                        self._combat_snapshot = None
                    elif action == "quit":
                        self._reset_to_title()
                        self._combat_snapshot = None

                elif self.state is State.INTERMISSION:
                    self.intermission.handle_event(ev)

                elif self.state in (State.VICTORY, State.DEFEAT) and ev.key == pygame.K_RETURN:
                    self._reset_to_title()

            # Also handle pause menu mouse clicks
            if self.state is State.PAUSED:
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    action = self._pause_menu.handle_event(ev)
                    if action == "resume":
                        self.state = State.COMBAT
                        self._combat_snapshot = None
                    elif action == "restart":
                        self._reset_to_title()
                        self._combat_snapshot = None
                    elif action == "quit":
                        self._reset_to_title()
                        self._combat_snapshot = None

    # ── Per-frame update ───────────────────────────────────────────────────────

    def update(self, dt: float, events: list, screen=None, clock=None) -> None:
        if self.state is State.LOADOUT:
            from src.ui.loadout_screen import LoadoutScreen
            result = LoadoutScreen(screen, clock).run()
            if result is None: self.running = False
            else: self._start_run(result)

        elif self.state is State.COMBAT:
            mouse_screen = pygame.mouse.get_pos()
            mouse_world  = self.camera.screen_to_world(*mouse_screen)
            self.player.update(dt, mouse_world, events)

            # Camera follows player
            self.camera.follow(self.player.x, self.player.y)

            self.arena.update(dt)

            # Upload progress (real-time)
            self.upload_pct = min(
                100.0,
                self.upload_pct + (100.0 / UPLOAD_DURATION_SEC) * dt
            )

            # Defeat by HP
            if not self.player.alive:
                self._go_defeat()
                return

            # Victory: upload full AND wave clear
            if self.upload_pct >= 100.0 and self.arena.wave_complete:
                self._go_victory()
                return

            # Wave-end transition
            if self.arena.wave_complete:
                # Sentience check
                log_dict = self.lethality_log.all()
                fits = [
                    fitness(self.lethality_log.get(c.id))
                    for c in self.previous_population
                    if c.id in self.lethality_log.all()
                ]
                if fits:
                    max_fit = max(fits)
                    if max_fit >= SENTIENCE_THRESHOLD * _theoretical_max_fitness():
                        self._go_defeat()
                        return
                self._enter_intermission()

        elif self.state is State.PAUSED:
            self._pause_menu.update(dt)

        elif self.state is State.INTERMISSION:
            self.intermission.update(dt)
            if self.intermission.advance_requested:
                self.state = State.UPGRADE # Go to upgrade screen before next wave!

        elif self.state is State.UPGRADE:
            from src.ui.upgrade_screen import UpgradeScreen
            chosen_upgrade = UpgradeScreen(screen, clock).run()
            if chosen_upgrade:
                self.player.apply_upgrade(chosen_upgrade) # Apply the stats!
                self._start_next_wave()
            else:
                self.running = False

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render(self, screen: pygame.Surface) -> None:
        self._ensure_fonts()

        if self.state is State.TITLE:
            self._render_title(screen)

        elif self.state is State.COMBAT:
            self._render_combat(screen)

        elif self.state is State.PAUSED:
            # Draw frozen combat frame underneath
            if self._combat_snapshot:
                screen.blit(self._combat_snapshot, (0, 0))
            self._pause_menu.draw(screen)

        elif self.state is State.INTERMISSION:
            draw_ledger(
                screen,
                ledger=self.intermission.ledger,
                wave_finished=self.intermission.wave_finished,
                sa_temperature=self.intermission.sa_temperature,
                elapsed_in_intermission=self.intermission.elapsed,
                title_font=self.font_title,
                header_font=self.font_header,
                body_font=self.font_body,
            )
        elif self.state is State.UPGRADE:
            pass

        elif self.state is State.VICTORY:
            self._render_victory(screen)

        elif self.state is State.DEFEAT:
            self._render_defeat(screen)

    def _render_title(self, screen: pygame.Surface) -> None:
        dt = 1 / 60
        self._title_time += dt
        self._title_particles.update(dt)

        # Background gradient
        for y_band in range(0, HEIGHT, 4):
            frac = y_band / HEIGHT
            r = int(6 + 6 * frac)
            g = int(10 + 8 * frac)
            b = int(20 + 12 * frac)
            pygame.draw.rect(screen, (r, g, b), (0, y_band, WIDTH, 4))

        # Grid
        step = 80
        grid_alpha = int(12 + 6 * math.sin(self._title_time * 0.3))
        for gx in range(0, WIDTH + step, step):
            gs = pygame.Surface((1, HEIGHT), pygame.SRCALPHA)
            gs.fill((40, 80, 60, grid_alpha))
            screen.blit(gs, (gx, 0))
        for gy in range(0, HEIGHT + step, step):
            gs = pygame.Surface((WIDTH, 1), pygame.SRCALPHA)
            gs.fill((40, 80, 60, grid_alpha))
            screen.blit(gs, (0, gy))

        # Particles
        self._title_particles.draw(screen)

        # Scanlines + vignette
        draw_scanlines(screen, alpha=5)
        draw_vignette(screen, intensity=70)

        # Title — "MUTAGEN ARENA" with glow
        pulse = 0.6 + 0.4 * math.sin(self._title_time * 1.5)
        title_color = pulse_color((100, 240, 180), pulse)

        # Glow behind title
        glow_surf = pygame.Surface((500, 60), pygame.SRCALPHA)
        glow_alpha = int(30 * pulse)
        pygame.draw.ellipse(glow_surf, (*title_color[:3], glow_alpha),
                            pygame.Rect(0, 0, 500, 60))
        screen.blit(glow_surf, (WIDTH // 2 - 250, HEIGHT // 2 - 70))

        title_surf = fm.mega().render("MUTAGEN ARENA", True, title_color)
        screen.blit(title_surf,
                    title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 44)))

        # Subtitle — typewriter reveal
        full_sub = "Project Sentinel — survive while the Purge Code uploads"
        chars_shown = min(len(full_sub), int(self._title_time * 25))
        revealed = full_sub[:chars_shown]
        sub_surf = fm.body().render(revealed, True, (160, 170, 180))
        screen.blit(sub_surf,
                    sub_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10)))

        # Blinking cursor
        if chars_shown < len(full_sub) and int(self._title_time * 4) % 2 == 0:
            cursor_x = WIDTH // 2 + sub_surf.get_width() // 2 + 2
            cursor_surf = fm.body().render("_", True, (160, 170, 180))
            screen.blit(cursor_surf, (cursor_x, HEIGHT // 2 + 2))

        # Decorative divider
        div_y = HEIGHT // 2 + 35
        div_w = 300
        div_x = WIDTH // 2 - div_w // 2
        div_surf = pygame.Surface((div_w, 1), pygame.SRCALPHA)
        div_surf.fill((*title_color, int(40 * pulse)))
        screen.blit(div_surf, (div_x, div_y))

        # "Press SPACE" prompt — pulsing
        if self._title_time > 2.5:
            prompt_pulse = 0.5 + 0.5 * math.sin(self._title_time * 2.5)
            prompt_color = tuple(max(0, min(255, int(c * prompt_pulse))) for c in (180, 220, 200))
            prompt = fm.body().render("Press SPACE to select loadout", True,
                                     prompt_color)
            screen.blit(prompt,
                        prompt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 70)))

        # Version / credits
        ver = fm.tiny().render("v1.0  —  Mutagen Arena: Project Sentinel", True,
                               (40, 50, 60))
        screen.blit(ver, ver.get_rect(center=(WIDTH // 2, HEIGHT - 20)))

    def _render_combat(self, screen: pygame.Surface) -> None:
        # Arena draws world (background, enemies, projectiles)
        self.arena.draw(screen, self.camera)

        # Player draws itself and weapon effects
        self.player.draw(screen, self.camera)

        self.player.draw_hud(screen)

        h_state = HUDState(self.player.hp, self.player.max_hp, self.upload_pct, self.wave_n, self.arena.enemies_remaining(), self.sa_temperature)
        draw_hud(screen, h_state, self.font_body)

        if self.debug_overlay:
            self._render_debug_overlay(screen)

    def _render_victory(self, screen: pygame.Surface) -> None:
        dt = 1 / 60
        self._end_time += dt

        if self._end_particles:
            self._end_particles.update(dt)

        # Fade in
        if self._end_fade_in > 0:
            self._end_fade_in = max(0, self._end_fade_in - int(300 * dt))

        # Background gradient — dark green/cyan
        for y_band in range(0, HEIGHT, 4):
            frac = y_band / HEIGHT
            r = int(4 + 6 * frac)
            g = int(12 + 10 * frac)
            b = int(16 + 14 * frac)
            pygame.draw.rect(screen, (r, g, b), (0, y_band, WIDTH, 4))

        # Particles
        if self._end_particles:
            self._end_particles.draw(screen)

        draw_scanlines(screen, alpha=5)
        draw_vignette(screen, intensity=60)

        # Triumphant glow expansion
        pulse = 0.5 + 0.5 * math.sin(self._end_time * 2.0)
        glow_r = int(200 + 50 * pulse)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        glow_color = (60, 220, 140, int(15 * pulse))
        pygame.draw.circle(glow_surf, glow_color, (glow_r, glow_r), glow_r)
        screen.blit(glow_surf, (WIDTH // 2 - glow_r, HEIGHT // 2 - glow_r - 40))

        # Title
        title_color = pulse_color((100, 255, 140), 0.7 + 0.3 * pulse)
        title = fm.mega().render("PURGE COMPLETE", True, title_color)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))

        # Decorative divider
        div_y = HEIGHT // 2 + 5
        div_w = 400
        div_surf = pygame.Surface((div_w, 1), pygame.SRCALPHA)
        div_surf.fill((*title_color, int(50 * pulse)))
        screen.blit(div_surf, (WIDTH // 2 - div_w // 2, div_y))

        # Stats panel
        stats_y = HEIGHT // 2 + 25
        panel_rect = pygame.Rect(WIDTH // 2 - 200, stats_y, 400, 100)
        draw_panel(screen, panel_rect,
                   border_color=(50, 120, 80),
                   bg_color=(6, 14, 10, 200),
                   border_radius=8)

        stat_font = fm.body()
        wave_text = stat_font.render(f"Waves Survived: {self.wave_n}", True,
                                     (180, 255, 200))
        screen.blit(wave_text, (panel_rect.x + 20, stats_y + 15))

        upload_text = stat_font.render(f"Purge Code: 100% COMPLETE", True,
                                       (120, 255, 160))
        screen.blit(upload_text, (panel_rect.x + 20, stats_y + 42))

        if self.player:
            hp_text = stat_font.render(
                f"Final HP: {int(self.player.hp)}/{int(self.player.max_hp)}",
                True, (180, 220, 200)
            )
            screen.blit(hp_text, (panel_rect.x + 20, stats_y + 69))

        # Prompt
        if self._end_time > 1.5:
            prompt_pulse = 0.5 + 0.5 * math.sin(self._end_time * 2.5)
            prompt_color = tuple(max(0, min(255, int(c * prompt_pulse))) for c in (160, 200, 180))
            prompt = fm.body().render("Press ENTER to return to title", True,
                                     prompt_color)
            screen.blit(prompt,
                        prompt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 160)))

        # Fade in
        if self._end_fade_in > 0:
            draw_fade(screen, self._end_fade_in)

    def _render_defeat(self, screen: pygame.Surface) -> None:
        dt = 1 / 60
        self._end_time += dt

        if self._end_particles:
            self._end_particles.update(dt)

        # Fade in
        if self._end_fade_in > 0:
            self._end_fade_in = max(0, self._end_fade_in - int(200 * dt))

        # Background gradient — dark red
        for y_band in range(0, HEIGHT, 4):
            frac = y_band / HEIGHT
            r = int(14 + 10 * frac)
            g = int(6 + 4 * frac)
            b = int(8 + 6 * frac)
            pygame.draw.rect(screen, (r, g, b), (0, y_band, WIDTH, 4))

        # Particles
        if self._end_particles:
            self._end_particles.draw(screen)

        draw_scanlines(screen, alpha=6)
        draw_vignette(screen, intensity=100)

        # Red vignette pulse
        pulse = 0.5 + 0.5 * math.sin(self._end_time * 1.5)
        red_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        red_overlay.fill((120, 0, 0, max(0, min(255, int(15 * pulse)))))
        screen.blit(red_overlay, (0, 0))

        # Glitch title
        glitch_intensity = 0.15 * abs(math.sin(self._end_time * 5.0))
        title_color = pulse_color((255, 80, 80), 0.6 + 0.4 * pulse)
        title = render_glitch_text(fm.mega(), "CONTAINMENT BREACH",
                                    title_color, glitch_intensity)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))

        # Horizontal glitch lines (brief random offset)
        if glitch_intensity > 0.05:
            import random
            for _ in range(2):
                gy = random.randint(0, HEIGHT)
                gh = random.randint(1, 3)
                gx_off = random.randint(-8, 8)
                line_rect = pygame.Rect(0, gy, WIDTH, gh)
                glitch_surf = pygame.Surface((WIDTH, gh), pygame.SRCALPHA)
                glitch_surf.fill((255, 40, 40, 30))
                screen.blit(glitch_surf, (gx_off, gy))

        # Decorative divider
        div_y = HEIGHT // 2 + 5
        div_w = 400
        div_surf = pygame.Surface((div_w, 1), pygame.SRCALPHA)
        div_surf.fill((*title_color, int(40 * pulse)))
        screen.blit(div_surf, (WIDTH // 2 - div_w // 2, div_y))

        # Stats panel
        stats_y = HEIGHT // 2 + 25
        panel_rect = pygame.Rect(WIDTH // 2 - 200, stats_y, 400, 100)
        draw_panel(screen, panel_rect,
                   border_color=(100, 40, 40),
                   bg_color=(14, 6, 8, 200),
                   border_radius=8)

        stat_font = fm.body()
        wave_text = stat_font.render(f"Waves Survived: {self.wave_n}", True,
                                     (255, 180, 180))
        screen.blit(wave_text, (panel_rect.x + 20, stats_y + 15))

        upload_text = stat_font.render(
            f"Purge Code: {self.upload_pct:.0f}%", True, (255, 160, 140)
        )
        screen.blit(upload_text, (panel_rect.x + 20, stats_y + 42))

        if self.player:
            dmg_text = stat_font.render(
                f"Damage Taken: {int(self.player.total_damage_taken)}",
                True, (255, 140, 140)
            )
            screen.blit(dmg_text, (panel_rect.x + 20, stats_y + 69))

        # Prompt
        if self._end_time > 2.0:
            prompt_pulse = 0.5 + 0.5 * math.sin(self._end_time * 2.5)
            prompt_color = tuple(max(0, min(255, int(c * prompt_pulse))) for c in (200, 160, 160))
            prompt = fm.body().render("Press ENTER to return to title", True,
                                     prompt_color)
            screen.blit(prompt,
                        prompt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 160)))

        # Fade in
        if self._end_fade_in > 0:
            draw_fade(screen, self._end_fade_in)

    def _render_debug_overlay(self, screen: pygame.Surface) -> None:
        """F3 overlay — SA temperature, gene means per archetype, top fitness."""
        from statistics import mean as _mean
        lines = [f"T = {self.sa_temperature:.3f}  |  Wave {self.wave_n}  |  Upload {self.upload_pct:.1f}%"]

        for archetype in list(Archetype):
            sub = [c for c in self.previous_population if c.archetype is archetype]
            if sub:
                means = "  ".join(
                    f"{g}={_mean(getattr(c, g) for c in sub):.1f}" for g in GENES
                )
                lines.append(f"{archetype.value.upper():<8} {means}")

        log = self.lethality_log.all()
        if log:
            records = sorted(
                log.values(),
                key=lambda r: -(r.survival_sec + 2 * r.damage_dealt)
            )[:3]
            for i, r in enumerate(records):
                lines.append(
                    f"  top{i+1}  {r.archetype.value:<8}"
                    f"  surv={r.survival_sec:5.1f}  dmg={r.damage_dealt:5.1f}"
                )

        y = 80
        for line in lines:
            surf = self.font_small.render(line, True, (255, 255, 127))
            screen.blit(surf, (24, y))
            y += 18
