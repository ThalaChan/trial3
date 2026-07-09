import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from navigation.base import BaseNavigator
from pathfinding     import get_pathfinder


class RankedNavigator(BaseNavigator):
    """
    Yen K-shortest ranked paths.
    Cycles: #1 optimal → #2 alt → #3 alt → wraps.
    """

    def __init__(self, src, dst):
        from config import K_PATHS
        self._pf    = get_pathfinder()
        self._src   = src
        self._dst   = dst
        self._index = 0
        self._paths = self._pf.compute_paths(src, dst, k=K_PATHS)
        print(f"  Drone {src}→{dst}: {len(self._paths)} ranked paths "
              f"(K_PATHS={K_PATHS})")

    def current_path(self) -> list:
        return list(self._paths[self._index])

    def advance_rank(self):
        self._index = (self._index + 1) % len(self._paths)

    def rank_label(self) -> str:
        if self._index == 0: return "#1 optimal"
        if self._index == 1: return "#2 alt"
        return f"#{self._index + 1} alt"

    def rank_index(self) -> int:
        return self._index

    def path_cost(self) -> float:
        return round(self._pf.path_cost(self._paths[self._index]), 1)

    def total_ranks(self) -> int:
        return len(self._paths)