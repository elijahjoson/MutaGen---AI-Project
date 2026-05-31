"""Simulated annealing for mutation acceptance.

Temperature is driven by player HP (per the design doc): hot when thriving,
cold when dying. SA does TWO things at once:
  1. Scales the gaussian sigma for mutation (in evolve.py).
  2. Gates accept/reject of regressions via Metropolis (this module).

"""
import math
import random
from src.ai.chromosome import Chromosome, GENES, GENE_RANGES


def temperature(player_hp: float, player_max_hp: float) -> float:
    """Player HP fraction, clamped to [0, 1]."""
    if player_max_hp <= 0:
        return 0.0
    return max(0.0, min(1.0, player_hp / player_max_hp))


def heuristic_value(c: Chromosome) -> float:
    """Cheap lethality estimate, normalized to [0, 1].

    Mean of normalized gene values. All five genes are positively correlated
    with lethality (more HP, more damage, more speed, etc.), so the mean is a
    defensible scalar 'how dangerous is this chromosome' proxy used by the SA
    accept/reject gate.
    """
    def norm(v: float, name: str) -> float:
        r = GENE_RANGES[name]
        return (v - r.lo) / r.span
    return sum(norm(getattr(c, g), g) for g in GENES) / len(GENES)


def accept(parent: Chromosome, candidate: Chromosome, T: float) -> Chromosome:
    """Metropolis acceptance criterion.

    Always accept improvements. Accept regressions with probability e^(delta/T):
      - high T → most regressions accepted (exploration)
      - low T  → most regressions rejected (exploitation)
      - T == 0 → only improvements accepted

    Returns the chromosome that should be kept in the next generation.
    """
    delta = heuristic_value(candidate) - heuristic_value(parent)
    if delta > 0:
        return candidate
    if T > 0.0 and random.random() < math.exp(delta / T):
        return candidate
    return parent
