"""
vfx.py
======
Visual effects: explosion particles and the persistent heatmap.

Classes
-------
  Particle
      Short-lived colored dot that flies outward from a collision or
      cancellation point. Fades over 18–45 frames.

      kind values
      -----------
        "direct"  -> red/orange burst  (node-to-node collision)
        "prox"    -> blue burst         (proximity collision)
        "cancel"  -> yellow/grey burst  (mid-flight cancellation)

  HeatMap
      Persistent colored blobs drawn on a transparent surface.
      Accumulates over the simulation; never fades (tick() is a no-op).
      Red = direct collisions, Blue = proximity collisions.
      Drawn between the grid and the drones so drones always appear on top.
"""

import random
import math
import pygame
from config import SIM_W


class Particle:
    """
    One short-lived explosion particle.

    Parameters
    ----------
    x, y : pixel spawn position
    kind : "direct" | "prox" | "cancel"
    """

    def __init__(self, x: float, y: float, kind: str = "direct"):
        self.x        = x
        self.y        = y
        self.kind     = kind
        # Random outward velocity
        angle         = random.uniform(0, 2 * math.pi)
        speed         = random.uniform(0.5, 3.5)
        self.vx       = math.cos(angle) * speed
        self.vy       = math.sin(angle) * speed
        # Lifetime in frames
        self.life     = random.randint(18, 45)
        self.max_life = self.life
        self.size     = random.randint(2, 5)

    def update(self):
        """Advance position and decay lifetime."""
        self.x    += self.vx
        self.y    += self.vy
        self.vx   *= 0.92   # drag
        self.vy   *= 0.92
        self.life -= 1

    def draw(self, surf):
        """Render as a fading colored dot."""
        if self.life <= 0:
            return
        alpha = self.life / self.max_life   # 1.0 (fresh) -> 0.0 (dead)

        if self.kind == "direct":
            r = int(255 * alpha)
            g = int(80  * alpha)
            b = int(30  * alpha)
        elif self.kind == "prox":
            r = int(60  * alpha)
            g = int(140 * alpha)
            b = int(255 * alpha)
        elif self.kind == "cancel":
            r = int(220 * alpha)
            g = int(200 * alpha)
            b = int(60  * alpha)
        else:
            r = g = b = int(200 * alpha)

        color = (max(0, min(255, r)),
                 max(0, min(255, g)),
                 max(0, min(255, b)))
        size  = max(1, int(self.size * alpha))
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), size)


class HeatMap:
    """
    Persistent overlay showing collision hotspots.

    Drawn as semi-transparent colored circles on a dedicated SRCALPHA
    surface that is blit onto the main canvas every frame.
    Blobs accumulate and never fade — they represent the full history
    of collisions in the current run.
    """

    def __init__(self):
        from config import SIM_W, HEIGHT
        # Separate transparent surface so heatmap doesn't overwrite grid
        self._surf = pygame.Surface((SIM_W, HEIGHT), pygame.SRCALPHA)
        self._surf.fill((0, 0, 0, 0))

    def add(self, gx: float, gy: float, kind: str, intensity: float = 6.0):
        """
        Add a heatmap blob at grid position (gx, gy).

        Parameters
        ----------
        gx, gy    : grid coordinates of the collision
        kind      : "direct" (red) | "prox" (blue)
        intensity : controls blob radius (radius = intensity * 8)
        """
        from grid import to_px
        px, py = to_px((gx, gy))
        r      = int(intensity * 8)
        color  = (255, 60, 60, 40) if kind == "direct" else (60, 140, 255, 30)
        pygame.draw.circle(self._surf, color, (px, py), r)

    def tick(self):
        """Called each frame. No-op — heatmap is intentionally persistent."""
        pass

    def draw(self, surf):
        """Blit the heatmap surface onto the main canvas."""
        surf.blit(self._surf, (0, 0))
