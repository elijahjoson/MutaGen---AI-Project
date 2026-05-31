"""
src.entities — Player and weapon entities.
Owner: Joson (Elijah)

Exposes:
  Player        — player movement, dash, stamina, loadout
  Weapon        — base weapon class
  create_weapon — factory: create_weapon("Pulse Rifle") → PulseRifle instance
"""

from src.entities.player import Player
from src.entities.weapon import Weapon, create_weapon

__all__ = ["Player", "Weapon", "create_weapon"]