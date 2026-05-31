import pygame
import os

class AssetManager:
    _images = {}  # The dictionary that stores loaded images in RAM

    @classmethod
    def get_image(cls, filepath: str, scale: float = 1.0) -> pygame.Surface | None:
        # Create a unique name for the dictionary (e.g., "assets/player.png_1.5")
        key = f"{filepath}_{scale}"

        # 1. If we already loaded it, return it instantly!
        if key in cls._images:
            return cls._images[key]

        # 2. If it is NOT in the dictionary, load it from the hard drive
        try:
            image = pygame.image.load(filepath).convert_alpha()
            if scale != 1.0:
                image = pygame.transform.scale_by(image, scale)
            
            # Save it to the dictionary so we never have to load it again
            cls._images[key] = image
            return image
            
        except Exception as e:
            print(f"[AssetManager] Failed to load {filepath}: {e}")
            return None