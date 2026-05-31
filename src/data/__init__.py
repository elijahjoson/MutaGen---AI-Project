"""
src.data — Data layer: telemetry, population storage, ledger computation.
Owner: Centeno

Exposes:
  LethalityLog, EnemyRecord  — per-enemy survival/damage telemetry
  GenotypeRegistry           — current-wave chromosome population store
  compute_ledger             — computes gene-mean deltas for the intermission screen
"""

from src.data.lethality_log import LethalityLog, EnemyRecord
from src.data.genotype_registry import GenotypeRegistry
from src.data.ledger_diff import compute_ledger

__all__ = [
    "LethalityLog",
    "EnemyRecord",
    "GenotypeRegistry",
    "compute_ledger",
]