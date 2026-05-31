"""Genetic algorithm primitives — fitness, selection, crossover, mutation.

PURE FUNCTIONS over Chromosome and EnemyRecord. No pygame imports.

"""
import random

# ── Updated imports: was mutagen_arena.ai / mutagen_arena.data / mutagen_arena.settings ──
from src.ai.chromosome import Chromosome, GENES, GENE_RANGES
from src.data.lethality_log import EnemyRecord
from src.core.constants import GA_W1 as W_SURVIVAL, GA_W2 as W_DAMAGE


def fitness(record: EnemyRecord) -> float:
    """Fitness(e) = w1 * survival + w2 * damage. Always non-negative."""
    if not record: 
        return 1.0
    return W_SURVIVAL * record.survival_sec + W_DAMAGE * record.damage_dealt


def select_parent(pop: list[Chromosome], fitnesses: list[float]) -> Chromosome:
    """Roulette wheel: probability proportional to fitness.

    Matches the case study's RANDOM-SELECTION weighted by fitness_fn.
    Fitness values must be non-negative (guaranteed by fitness() above).
    """
    return random.choices(pop, weights=fitnesses, k=1)[0]


def crossover(x: Chromosome, y: Chromosome) -> Chromosome:
    """Single-point crossover on the GENES tuple.

    Archetype label inherits from the first parent — we never cross archetypes
    (selection only pairs within an archetype; see evolve.py).
    """
    c = random.randint(1, len(GENES) - 1)
    genes = list(x.genes[:c]) + list(y.genes[c:])
    return Chromosome.from_genes(x.archetype, genes)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def mutate(c: Chromosome, sigma_frac: float) -> Chromosome:
    """Per-gene gaussian noise scaled by sigma_frac * gene_range.span, clamped.

    sigma_frac is the SA-controlled magnitude (see annealing.py). Values
    outside the gene range are clamped, never wrapped.
    """
    new_values = []
    for value, name in zip(c.genes, GENES):
        r = GENE_RANGES[name]
        noise = random.gauss(0.0, sigma_frac * r.span)
        new_values.append(_clamp(value + noise, r.lo, r.hi))
    return Chromosome.from_genes(c.archetype, new_values)
