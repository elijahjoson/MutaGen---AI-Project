"""Intermission screen — renders the Evolutionary Ledger for the player."""
import pygame
from src.ai.chromosome import Archetype
from src.core.constants import SCREEN_W, SCREEN_H

INTERMISSION_AUTO_ADVANCE_SEC = 15.0 

COLOR_INCREASE = (127, 255, 179)
COLOR_DECREASE = (255, 127, 127)
COLOR_STABLE   = (140, 140, 140)

def draw_ledger(
    screen: pygame.Surface, ledger: dict, wave_finished: int,
    sa_temperature: float, elapsed_in_intermission: float,
    title_font: pygame.font.Font, header_font: pygame.font.Font, body_font: pygame.font.Font,
) -> None:
    screen.fill((10, 14, 26))
    
    sub = title_font.render("INTERMISSION", True, (127, 179, 255))
    screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 80)))
    
    big = title_font.render(f"WAVE {wave_finished} -> WAVE {wave_finished + 1}", True, (255, 255, 255))
    screen.blit(big, big.get_rect(center=(SCREEN_W // 2, 130)))

    col_y = 200
    archetypes = list(Archetype)
    colors = [(127, 179, 255), (255, 127, 179), (127, 255, 179), (200, 150, 255)]
    spacing = SCREEN_W // 4
    
    for i, archetype in enumerate(archetypes):
        x = 40 + (i * spacing)
        header = header_font.render(f"{archetype.value.upper()}", True, colors[i])
        screen.blit(header, (x, col_y))
        
        entries = ledger.get(archetype, [])
        if not entries:
            stable = body_font.render("- No significant change", True, COLOR_STABLE)
            screen.blit(stable, (x, col_y + 40))
        else:
            for j, (gene, pct) in enumerate(entries):
                color = COLOR_INCREASE if pct > 0 else COLOR_DECREASE
                text = f"{gene} {'+' if pct > 0 else ''}{pct:.0f}%"
                screen.blit(body_font.render(text, True, color), (x, col_y + 40 + j * 28))

    remaining = max(0.0, INTERMISSION_AUTO_ADVANCE_SEC - elapsed_in_intermission)
    prompt = body_font.render(f"Press SPACE to continue  ·  auto-advance in {remaining:.0f}s", True, (200, 200, 200))
    screen.blit(prompt, prompt.get_rect(center=(SCREEN_W // 2, SCREEN_H - 60)))