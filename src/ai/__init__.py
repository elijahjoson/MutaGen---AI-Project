"""
src.ai — Genetic Algorithm and Simulated Annealing subsystem.

Exposes:
  Chromosome, Archetype, GENES, GENE_RANGES  — genotype data
  fitness, select_parent, crossover, mutate  — GA primitives
  temperature, accept, heuristic_value       — SA functions
  evolve_population                          — combined GA+SA per wave
"""

from src.ai.chromosome import (
    Chromosome,
    Archetype,
    GENES,
    GENE_RANGES,
    TANK_BASELINE,
    STRIKER_BASELINE,
    RANGED_BASELINE,
    SUPPORT_BASELINE,
)
from src.ai.genetic import fitness, select_parent, crossover, mutate
from src.ai.annealing import temperature, accept, heuristic_value
from src.ai.evolve import evolve_population

__all__ = [
    "Chromosome", "Archetype", "GENES", "GENE_RANGES",
    "TANK_BASELINE", "STRIKER_BASELINE", "RANGED_BASELINE", "SUPPORT_BASELINE",
    "fitness", "select_parent", "crossover", "mutate",
    "temperature", "accept", "heuristic_value",
    "evolve_population",
]