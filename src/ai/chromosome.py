"""Chromosome data structure and gene definitions.

5 numeric genes, archetype label (NOT a gene — Tanks stay Tanks).
Constructor positional order MUST match GENES tuple order so from_genes() works.

"""
from dataclasses import dataclass, field
from enum import Enum
import itertools


class Archetype(Enum):
    TANK    = "Tank"
    STRIKER = "Striker"
    RANGED  = "Ranged"
    SUPPORT = "Support"

GENES = ("hp", "speed", "damage", "attack_cd", "resistance")

@dataclass(frozen=True)
class GeneRange:
    lo: float
    hi: float

    @property
    def span(self) -> float:
        return self.hi - self.lo


GENE_RANGES: dict[str, GeneRange] = {
    "hp":         GeneRange(10.0, 1000.0),
    "speed":      GeneRange(1.0,  12.0),
    "damage":     GeneRange(2.0,  80.0),
    "attack_cd":  GeneRange(0.2,  5.0),
    "resistance": GeneRange(0.0,  0.9),
}

_id_seq = itertools.count()

@dataclass
class Chromosome:
    archetype:    Archetype
    hp:           float
    speed:        float
    damage:       float
    attack_cd:    float
    resistance:   float
    id: int = field(default_factory=lambda: next(_id_seq))

    @property
    def genes(self) -> tuple:
        return tuple(getattr(self, g) for g in GENES)

    @classmethod
    def from_genes(cls, archetype: Archetype, gene_values: list[float]) -> "Chromosome":
        # Constructor positional order matches GENES tuple order exactly
        return cls(archetype, *gene_values)


# Wave-1 baselines — used by controller.py to seed the genotype registry.
#TANK_BASELINE    = Chromosome(Archetype.TANK,    hp=300, speed=2.0, damage=10, attack_cd=1.0, resistance=0.4)
#STRIKER_BASELINE = Chromosome(Archetype.STRIKER, hp=100, speed=5.0, damage=20, attack_cd=0.5, resistance=0.1)
#RANGED_BASELINE  = Chromosome(Archetype.RANGED,  hp=150, speed=3.0, damage=25, attack_cd=1.2, resistance=0.1)
#SUPPORT_BASELINE = Chromosome(Archetype.SUPPORT, hp=200, speed=2.5, damage=5,  attack_cd=2.0, resistance=0.2)

# Wave-1 baselines (NERFED FOR PLAYTESTING)
# Tank: Slower (1.5), hits less often (every 2.0s), less damage (10)
TANK_BASELINE    = Chromosome(Archetype.TANK,    hp=300, speed=1.5, damage=10, attack_cd=2.0, resistance=0.4)

# Striker: Much slower (2.8 down from 5.0), hits less often (every 1.5s down from 0.5s)
STRIKER_BASELINE = Chromosome(Archetype.STRIKER, hp=100, speed=2.8, damage=15, attack_cd=1.5, resistance=0.1)

# Ranged: Slower to allow dodging
RANGED_BASELINE  = Chromosome(Archetype.RANGED,  hp=150, speed=1.8, damage=15, attack_cd=2.0, resistance=0.1)

# Support: Stays back
SUPPORT_BASELINE = Chromosome(Archetype.SUPPORT, hp=200, speed=1.5, damage=5,  attack_cd=2.0, resistance=0.2)