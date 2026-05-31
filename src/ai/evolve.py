"""Combined GA + SA evolution between waves.

Population is partitioned by archetype; each archetype evolves independently
so the 50/50 wave mix is preserved across generations.

NOTE: Requires GA_BASE_SIGMA to be added to src/core/constants.py:
    GA_BASE_SIGMA = 0.15
"""

# ── Updated imports: was mutagen_arena.ai / mutagen_arena.data / mutagen_arena.settings ──
from src.ai.chromosome import Chromosome, Archetype
from src.ai.genetic import fitness, select_parent, crossover, mutate
from src.ai.annealing import accept
from src.data.lethality_log import EnemyRecord
from src.core.constants import GA_BASE_SIGMA as BASE_SIGMA


def evolve_population(
    prev_pop: list[Chromosome],
    lethality_log: dict[int, EnemyRecord],
    player_hp_frac: float,
) -> list[Chromosome]:
    """Produce next-wave chromosomes from previous wave + per-enemy telemetry.

    Steps per archetype subgroup:
      1. Compute fitness from lethality log.
      2. Roulette-select two parents.
      3. Single-point crossover → child.
      4. Mutate child with sigma scaled by T (SA: bigger when healthy).
      5. Metropolis accept/reject vs the unmutated child (SA: explore at high T).
    """
    T = player_hp_frac
    sigma_frac = BASE_SIGMA * (0.3 + 0.7 * T)  # never zero; heavily damped at T=0

    new_pop: list[Chromosome] = []
    for archetype in list(Archetype):
        sub = [c for c in prev_pop if c.archetype is archetype]
        if not sub:
            continue

        # Defensive: if a chromosome is missing from the log (e.g. wave ended
        # abnormally), treat its fitness as zero rather than KeyError.
        _zero = lambda c: EnemyRecord(c.id, c.archetype, 0.0, 0.0)
        fits = [fitness(lethality_log.get(c.id, _zero(c))) for c in sub]

        # Safety: if every enemy of this archetype had zero fitness, fall back to uniform.
        if sum(fits) == 0:
            fits = [1.0] * len(sub)

        for _ in range(len(sub)):
            p1        = select_parent(sub, fits)
            p2        = select_parent(sub, fits)
            child     = crossover(p1, p2)
            candidate = mutate(child, sigma_frac)
            final     = accept(child, candidate, T)
            new_pop.append(final)

    return new_pop
