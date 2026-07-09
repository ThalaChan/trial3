"""
pathfinding/__init__.py
=======================
Factory — returns the configured pathfinder instance.

To add a new pathfinding algorithm
------------------------------------
  1. Create pathfinding/youralgo.py subclassing BasePathfinder.
  2. Implement compute_paths() and path_cost().
  3. Import it below and add an elif branch in get_pathfinder().
  4. Set PATHFINDER = "youralgo" in config.py.
  Nothing else in the project needs to change.

Available implementations
--------------------------
  "yen"      -> YenPathfinder      (Yen's K-Shortest Loopless Paths)
  "dijkstra" -> DijkstraPathfinder (single optimal path)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathfinding.yen      import YenPathfinder
from pathfinding.dijkstra import DijkstraPathfinder


def get_pathfinder():
    """Return the configured pathfinder instance (reads config at call time)."""
    from config import PATHFINDER

    if PATHFINDER == "yen":
        return YenPathfinder()
    elif PATHFINDER == "dijkstra":
        return DijkstraPathfinder()
    else:
        raise ValueError(
            f"Unknown PATHFINDER '{PATHFINDER}'. "
            f"Available: 'yen', 'dijkstra'"
        )
