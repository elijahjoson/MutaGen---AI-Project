"""Per-enemy survival/damage telemetry, used as input to GA fitness.

"""
from dataclasses import dataclass
from src.ai.chromosome import Archetype


@dataclass
class EnemyRecord:
    chromosome_id: int
    archetype:     Archetype
    survival_sec:  float
    damage_dealt:  float


class LethalityLog:
    """Append-only record store, cleared between waves by the controller."""

    def __init__(self) -> None:
        self._records: dict[int, EnemyRecord] = {}

    def record(self, rec: EnemyRecord) -> None:
        self._records[rec.chromosome_id] = rec

    def get(self, chromosome_id: int, default=None) -> EnemyRecord | None:
        return self._records.get(chromosome_id, default)

    def all(self) -> dict[int, EnemyRecord]:
        return dict(self._records)

    def clear(self) -> None:
        self._records.clear()
