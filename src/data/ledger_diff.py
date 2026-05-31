"""Computes per-archetype gene-mean deltas between two populations.

Used by the intermission screen to show the player what evolved.
Only changes above LEDGER_STABLE_THRESHOLD_PCT are reported.

NOTE: Requires these two constants added to src/core/constants.py:
    LEDGER_STABLE_THRESHOLD_PCT      = 5.0
    LEDGER_MAX_ENTRIES_PER_ARCHETYPE = 3
"""
from statistics import mean

# ── Updated imports: was mutagen_arena.ai.chromosome / mutagen_arena.settings ──
from src.ai.chromosome import Chromosome, Archetype, GENES
from src.core.constants import (
    LEDGER_STABLE_THRESHOLD_PCT,
    LEDGER_MAX_ENTRIES_PER_ARCHETYPE,
)


GENE_LABEL: dict[str, str] = {
    "hp":           "HP",
    "speed":        "Speed",
    "damage":       "Damage",
    "attack_rate":  "Attack cooldown",
    "resist_close": "Resistance",
}


def compute_ledger(
    old_pop: list[Chromosome],
    new_pop: list[Chromosome],
) -> dict[Archetype, list[tuple[str, float]]]:
    """Return {archetype: [(gene_name, pct_change), ...]} sorted by |pct| desc.

    Each archetype gets at most LEDGER_MAX_ENTRIES_PER_ARCHETYPE entries.
    Changes within ±LEDGER_STABLE_THRESHOLD_PCT are filtered out.
    """
    entries: list[tuple[Archetype, str, float]] = []
    for archetype in list(Archetype):
        old = [c for c in old_pop if c.archetype is archetype]
        new = [c for c in new_pop if c.archetype is archetype]
        if not old or not new:
            continue
        for gene in GENES:
            o   = mean(getattr(c, gene) for c in old)
            n   = mean(getattr(c, gene) for c in new)
            pct = (n - o) / o * 100 if o != 0 else 0.0
            if abs(pct) >= LEDGER_STABLE_THRESHOLD_PCT:
                entries.append((archetype, gene, pct))

    entries.sort(key=lambda e: -abs(e[2]))
    out: dict[Archetype, list[tuple[str, float]]] = {
        arch: [] for arch in list(Archetype)
    }
    for arch, gene, pct in entries:
        if len(out[arch]) < LEDGER_MAX_ENTRIES_PER_ARCHETYPE:
            out[arch].append((gene, pct))
    return out
