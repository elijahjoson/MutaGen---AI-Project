"""GameController — owns all subsystems and the 5-state machine.

States: TITLE · COMBAT · INTERMISSION · VICTORY · DEFEAT

"""
from enum import Enum
import pygame

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
from src.ui.ledger_panel import draw_ledger
from src.ui.hud import HUDState, draw_hud

# ── Sentience threshold ───────────────────────────────────────────────────────
# If any enemy reaches this fraction of theoretical max fitness, player loses.
# Adjust during playtesting if needed.
SENTIENCE_THRESHOLD = 0.85


class State(Enum):
    TITLE        = "title"
    LOADOUT      = "loadout"      # ← NEW: loadout selection before run starts
    COMBAT       = "combat"
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

    # ── Font init (lazy, after pygame.init in main) ────────────────────────────

    def _ensure_fonts(self) -> None:
        if self._fonts_ready:
            return
        self.font_title  = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_header = pygame.font.SysFont("consolas", 18, bold=True)
        self.font_body   = pygame.font.SysFont("consolas", 16)
        self.font_small  = pygame.font.SysFont("consolas", 14)
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
        self.state = State.INTERMISSION

    def _start_next_wave(self) -> None:
        """INTERMISSION → COMBAT."""
        self.wave_n += 1
        self.lethality_log.clear()
        self.arena.begin_wave(self.registry.current())
        self.state = State.COMBAT

    def _go_victory(self) -> None:
        self.state = State.VICTORY

    def _go_defeat(self) -> None:
        if self.arena is not None:
            self.arena.finalize_survivors()
        self.state = State.DEFEAT

    def _reset_to_title(self) -> None:
        self.state      = State.TITLE
        self.wave_n     = 0
        self.upload_pct = 0.0
        self.player     = None
        self.arena      = None

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

                elif self.state is State.INTERMISSION:
                    self.intermission.handle_event(ev)

                elif self.state in (State.VICTORY, State.DEFEAT) and ev.key == pygame.K_RETURN:
                    self._reset_to_title()

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
            self._render_end_screen(screen, "PURGE COMPLETE", (127, 255, 127))

        elif self.state is State.DEFEAT:
            self._render_end_screen(screen, "CONTAINMENT BREACH", (255, 127, 127))

    def _render_title(self, screen: pygame.Surface) -> None:
        screen.fill((10, 14, 26))
        title    = self.font_title.render("MUTAGEN ARENA", True, (255, 255, 255))
        subtitle = self.font_body.render(
            "Project Sentinel — survive while the Purge Code uploads",
            True, (180, 180, 180)
        )
        prompt = self.font_body.render(
            "Press SPACE to select loadout", True, (200, 200, 200)
        )
        screen.blit(title,    title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 8)))
        screen.blit(prompt,   prompt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60)))

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

    def _render_end_screen(self, screen: pygame.Surface, text: str, color) -> None:
        screen.fill((10, 14, 26))
        msg    = self.font_title.render(text, True, color)
        prompt = self.font_body.render("Press ENTER to return to title", True, (200, 200, 200))
        screen.blit(msg,    msg.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        screen.blit(prompt, prompt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50)))

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


# ── main.py integration note ──────────────────────────────────────────────────
"""
In main.py, the game loop should look roughly like this:

    import pygame
    from src.systems.controller import GameController, State
    from src.ui.loadout_screen import LoadoutScreen
    from src.core.constants import SCREEN_W, SCREEN_H, FPS, TITLE

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    clock  = pygame.time.Clock()

    controller = GameController()

    while controller.running:
        dt     = clock.tick(FPS) / 1000.0
        events = pygame.event.get()

        # Handle loadout screen as a blocking call when state is LOADOUT
        if controller.state is State.LOADOUT:
            result = LoadoutScreen(screen, clock).run()
            if result is None:
                controller.running = False   # player quit
            else:
                controller._start_run(result)
        else:
            controller.handle_events(events)
            controller.update(dt, events)
            controller.render(screen)
            pygame.display.flip()

    pygame.quit()
"""
