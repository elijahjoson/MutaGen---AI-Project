"""Holds the current-wave chromosome list. Mutated only at wave transitions.

"""

from src.ai.chromosome import Chromosome


class GenotypeRegistry:
    def __init__(self) -> None:
        self._pop: list[Chromosome] = []

    def set_population(self, pop: list[Chromosome]) -> None:
        self._pop = list(pop)

    def current(self) -> list[Chromosome]:
        return list(self._pop)

    def __len__(self) -> int:
        return len(self._pop)
