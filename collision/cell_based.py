import math
import sys
import os
sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from collision.base import BaseCollisionDetector


class CellBasedDetector(BaseCollisionDetector):
    """
    Severity applies to ALL vehicle type combinations.
    The radius used is always max(radius_a, radius_b).

    Return values:
      "direct"    → Critical   (same node)
      "major"     → Major      (dist <= radius × 0.5)
      "minor"     → Minor      (dist <= radius × 1.0)
      "near_miss" → Near Miss  (dist <= radius × 1.5, no crash)
      "none"      → Safe

    Convergence check prevents false positives on diverging drones.
    Pure grid_pos only — no pixel positions.
    """

    def __init__(self):
        from config import (VEHICLE_PROXIMITY_RADIUS,
                            SEVERITY_MAJOR_RATIO,
                            SEVERITY_MINOR_RATIO,
                            SEVERITY_NEARMISS_RATIO)
        self._vpr     = VEHICLE_PROXIMITY_RADIUS
        self._r_major = SEVERITY_MAJOR_RATIO
        self._r_minor = SEVERITY_MINOR_RATIO
        self._r_nm    = SEVERITY_NEARMISS_RATIO
        print(f"[Collision] CellBasedDetector ready")

    def _radius(self, a, b) -> float:
        """
        Effective safety radius for this pair.
        Always use the LARGER of the two vehicles' radii.
        This ensures bigger vehicles protect their larger airspace.
        """
        vt_a = getattr(a, "vehicle_type", "quad")
        vt_b = getattr(b, "vehicle_type", "quad")
        r_a  = self._vpr.get(vt_a, 5.0)
        r_b  = self._vpr.get(vt_b, 5.0)
        return max(r_a, r_b)

    def detect(self, a, b) -> str:
        ax, ay = int(a.grid_pos[0]), int(a.grid_pos[1])
        bx, by = int(b.grid_pos[0]), int(b.grid_pos[1])

        dist = math.hypot(ax - bx, ay - by)

        # Direct — same node, always Critical
        if dist == 0:
            return "direct"

        r = self._radius(a, b)

        # Only check proximity if within near-miss zone
        # AND drones are converging
        if dist <= r * self._r_nm:
            if not self._converging(ax, ay, bx, by, a, b):
                return "none"
            # Converging — classify severity
            if dist <= r * self._r_major:
                return "major"
            elif dist <= r * self._r_minor:
                return "minor"
            else:
                return "near_miss"

        return "none"

    def _converging(self, ax, ay, bx, by, a, b) -> bool:
        """
        True if drones are getting closer or staying same distance.
        Uses path queue next node — pure grid coords, no pixels.
        """
        current = math.hypot(ax - bx, ay - by)
        a_next  = self._peek(a, ax, ay)
        b_next  = self._peek(b, bx, by)
        nxt     = math.hypot(
            a_next[0] - b_next[0],
            a_next[1] - b_next[1])
        # +0.01 epsilon: parallel drones (same distance) are still risky
        return nxt <= current + 0.01

    def _peek(self, drone, cx, cy) -> tuple:
        """Next node from path queue. Returns current if at end."""
        pl = list(drone.path)
        if len(pl) >= 2:
            return (int(pl[1][0]), int(pl[1][1]))
        return (cx, cy)