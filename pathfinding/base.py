import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abc import ABC, abstractmethod


class BasePathfinder(ABC):
    """
    CONTRACT for every path-planning algorithm.
    To add a new algorithm:
      1. Create pathfinding/youralgo.py subclassing BasePathfinder
      2. Implement compute_paths() and path_cost()
      3. Register in pathfinding/__init__.py
      4. Set PATHFINDER = "youralgo" in config.py
    """

    @abstractmethod
    def compute_paths(self, src: tuple, dst: tuple, k: int = None) -> list:
        """
        Returns up to k ranked loopless paths from src to dst.
        path[0] is always the optimal (lowest cost) path.
        k=None reads from config.K_PATHS.
        k=0 means find every path the graph allows.
        """
        pass

    @abstractmethod
    def path_cost(self, path: list) -> float:
        """Return the total geometric cost of a path."""
        pass