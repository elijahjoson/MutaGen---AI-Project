"""
font_manager.py — Centralized font loading for MutaGen Arena.

Uses the bundled "Public Pixel" TTF (CC0, by GGBotNet) for a crisp
retro sci-fi look. Falls back to system Consolas/default if the
asset file is missing.

All UI modules should import fonts from here instead of calling
pygame.font.SysFont directly.
"""
import pygame
import os

# ── Font cache ────────────────────────────────────────────────────────────────
_fonts: dict[str, pygame.font.Font] = {}
_initialized = False

# Path to bundled font (relative to project root)
_FONT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "assets", "fonts",
)
_BUNDLED_FONT = os.path.normpath(os.path.join(_FONT_DIR, "PublicPixel.ttf"))

# Font size presets — pixel font looks best at multiples of 8
# but we tweak for readability at different roles
SIZES = {
    "mega":     32,   # Title screen hero text
    "title":    24,   # Screen titles
    "header":   16,   # Section headers, archetype names
    "hud_big":  16,   # Large HUD elements
    "body":     12,   # Body text, prompts
    "hud":      10,   # HUD labels
    "small":    10,   # Small labels, descriptions
    "tiny":      8,   # Micro labels, key hints
}

# Preferred system fonts as fallback (sci-fi / monospace feel)
_PREFERRED = ["Consolas", "Courier New", "Lucida Console", "monospace"]


def _load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Try bundled TTF first, then system fonts, then pygame default."""
    # Try bundled font
    if os.path.exists(_BUNDLED_FONT):
        try:
            f = pygame.font.Font(_BUNDLED_FONT, size)
            # Public Pixel doesn't have bold variant; we just use normal
            return f
        except Exception:
            pass

    # Fallback to system fonts
    for name in _PREFERRED:
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f:
                return f
        except Exception:
            continue
    return pygame.font.Font(None, size)


def init() -> None:
    """Initialize the font manager. Call after pygame.font.init()."""
    global _initialized
    if _initialized:
        return

    if not pygame.font.get_init():
        pygame.font.init()

    # Log which font we're using
    using_bundled = os.path.exists(_BUNDLED_FONT)
    if using_bundled:
        print(f"[font_manager] Using bundled font: {_BUNDLED_FONT}")
    else:
        print(f"[font_manager] Bundled font not found, using system fallback")

    # Build all named fonts
    for key, size in SIZES.items():
        bold = key in ("title", "header", "hud_big", "mega")
        _fonts[key] = _load_font(size, bold=bold)
        _fonts[f"{key}_bold"] = _load_font(size, bold=True)

    _initialized = True


def get(name: str) -> pygame.font.Font:
    """Get a font by preset name. Auto-initializes if needed."""
    if not _initialized:
        init()
    return _fonts.get(name, _fonts.get("body", pygame.font.Font(None, 18)))


# ── Convenience accessors ─────────────────────────────────────────────────────
def title()    -> pygame.font.Font: return get("title")
def header()   -> pygame.font.Font: return get("header")
def body()     -> pygame.font.Font: return get("body")
def small()    -> pygame.font.Font: return get("small")
def hud()      -> pygame.font.Font: return get("hud")
def hud_big()  -> pygame.font.Font: return get("hud_big")
def tiny()     -> pygame.font.Font: return get("tiny")
def mega()     -> pygame.font.Font: return get("mega")
