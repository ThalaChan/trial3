"""
grid.py
=======
Coordinate helpers for the 2-D airspace grid.

Responsibilities
----------------
  - Convert between grid coordinates and screen pixel positions.
  - All grid <-> pixel math lives here so nothing else needs to know
    about PAD, CELL_PX, or the Y-axis flip.

Grid coordinate system
----------------------
  Origin (0, 0) is at the BOTTOM-LEFT of the airspace.
  X increases to the right. Y increases upward.
  Screen pixels have Y increasing downward, so gy() flips the axis.

Used by
-------
  drone.py             -- to_px() for segment endpoints and crash positions
  collision/           -- px_to_cell() for same-cell membership test
  ui/grid_renderer.py  -- gx(), gy() to draw grid lines and axis labels
  vfx.py               -- to_px() to place heatmap blobs at grid nodes
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PAD, STEP, CELL_PX, SIM_W


def gx(v: int) -> int:
    """Grid X coordinate -> canvas pixel X."""
    return PAD + int((v / STEP) * CELL_PX)


def gy(v: int) -> int:
    """
    Grid Y coordinate -> canvas pixel Y.
    Y-axis is flipped: grid Y=0 appears at the bottom of the canvas.
    """
    return (SIM_W - PAD) - int((v / STEP) * CELL_PX)


def to_px(node: tuple) -> tuple:
    """(grid_x, grid_y) -> (pixel_x, pixel_y)."""
    return (gx(node[0]), gy(node[1]))


def px_to_cell(px: float, py: float) -> tuple:
    """
    Pixel position -> grid cell index (col, row).

    Used by collision detection to test same-cell membership.
    Clamps to valid cell range so out-of-bounds pixels map to
    the nearest border cell rather than raising an error.
    """
    from config import CELLS
    col = int((px - PAD) / CELL_PX)
    row = int((SIM_W - PAD - py) / CELL_PX)
    col = max(0, min(CELLS - 1, col))
    row = max(0, min(CELLS - 1, row))
    return (col, row)
