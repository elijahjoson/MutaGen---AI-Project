"""
src.core — Shared configuration and camera system.
Owner: Dela Cruz (constants) + Joson (camera)

Exposes:
  Camera      — viewport system for 2560x1440 arena
  constants   — all game configuration values (import directly from src.core.constants)
"""

from src.core.camera import Camera

__all__ = ["Camera"]