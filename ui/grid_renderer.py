import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from config import CELLS, STEP, SIM_W, PAD, GRID_L, NODE_C, MUTED
from grid   import gx, gy


def draw_grid(surf, fonts):
    """
    Draws background grid lines, node dots and axis labels.
    Separated so the grid style can be changed without
    touching simulation or UI logic.
    """
    for i in range(CELLS + 1):
        x = gx(i*STEP);  y = gy(i*STEP)
        pygame.draw.line(surf, GRID_L, (x, PAD),      (x, SIM_W-PAD), 1)
        pygame.draw.line(surf, GRID_L, (PAD, y), (SIM_W-PAD, y),      1)
    for i in range(CELLS + 1):
        for j in range(CELLS + 1):
            pygame.draw.circle(surf, NODE_C, (gx(i*STEP), gy(j*STEP)), 2)
    f = fonts[2]
    for i in range(0, CELLS+1, 2):
        v = i*STEP
        l = f.render(str(v), True, MUTED)
        surf.blit(l, (gx(v)-7, SIM_W-PAD+5))
        surf.blit(l, (4, gy(v)-6))