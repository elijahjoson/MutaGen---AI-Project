"""Intermission phase state — holds the ledger result and auto-advance timer."""
import pygame
from src.ai.chromosome import Archetype

# Auto-advance timer (in seconds)
INTERMISSION_AUTO_ADVANCE_SEC = 15.0 

class Intermission:
    def __init__(self):
        self.ledger: dict[Archetype, list[tuple[str, float]]] = {}
        self.wave_finished: int = 0
        self.sa_temperature: float = 0.0
        self.elapsed: float = 0.0
        self.advance_requested: bool = False

    def begin(self,
              ledger: dict,
              wave_finished: int,
              sa_temperature: float) -> None:
        self.ledger = ledger
        self.wave_finished = wave_finished
        self.sa_temperature = sa_temperature
        self.elapsed = 0.0
        self.advance_requested = False

    def update(self, dt: float) -> None:
        self.elapsed += dt
        if self.elapsed >= INTERMISSION_AUTO_ADVANCE_SEC:
            self.advance_requested = True

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.advance_requested = True