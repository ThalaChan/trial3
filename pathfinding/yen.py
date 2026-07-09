import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathfinding.base     import BasePathfinder
from pathfinding.dijkstra import run_dijkstra, DijkstraPathfinder
from config               import STEP, DIAG_COST


class YenPathfinder(BasePathfinder):
    """
    Yen's K-Shortest Loopless Paths.

    Path #1  →  plain Dijkstra, no restrictions.
    Path #k  →  for each spur node at index i in path #(k-1):
                  • Block edges that confirmed paths used leaving
                    this spur node (deterministic, not random).
                  • Block root nodes to prevent loops.
                  • Re-run Dijkstra from spur to dst.
                  • Splice root + spur result = candidate.
                Cheapest candidate becomes path #k.

    Self-terminates when candidate heap empties (graph exhausted).
    k=0 means find every path the graph allows.
    """

    def __init__(self):
        self._base = DijkstraPathfinder()

    def compute_paths(self, src: tuple, dst: tuple, k: int = None) -> list:
        # Read K from config at call time — never use a hardcoded default
        if k is None:
            from config import K_PATHS
            k = K_PATHS

        src         = tuple(src)
        dst         = tuple(dst)
        effective_k = k if k > 0 else 10_000

        if src == dst:
            return [[src]]

        # Path #1 — plain Dijkstra
        _, p0 = run_dijkstra(src, dst)
        if p0 is None:
            return [self._base._fallback(src, dst)]

        confirmed  = [p0]
        candidates = []

        # Paths #2 … effective_k
        for _ in range(1, effective_k):
            prev = confirmed[-1]

            for spur_idx in range(len(prev) - 1):
                spur_node = prev[spur_idx]
                root_path = prev[: spur_idx + 1]

                blocked_edges = set()
                blocked_nodes = set()

                # Block the exact edge each confirmed path used
                # leaving this spur node — deterministic, not random
                for conf in confirmed:
                    if (len(conf) > spur_idx
                            and conf[: spur_idx + 1] == root_path):
                        blocked_edges.add(
                            (conf[spur_idx], conf[spur_idx + 1]))

                # Prevent loops back through the root
                for node in root_path[:-1]:
                    blocked_nodes.add(node)

                _, spur_path = run_dijkstra(
                    spur_node, dst,
                    blocked_nodes=blocked_nodes,
                    blocked_edges=blocked_edges,
                )

                if spur_path is None:
                    continue

                candidate = root_path[:-1] + spur_path

                if not any(self._paths_equal(candidate, cp)
                           for _, cp in candidates):
                    candidates.append(
                        (self.path_cost(candidate), candidate))

            # Graph exhausted — no more distinct paths exist
            if not candidates:
                break

            candidates.sort(key=lambda x: x[0])
            _, next_path = candidates.pop(0)
            confirmed.append(next_path)

        valid = [p for p in confirmed if self._validate(p)]
        return valid if valid else [self._base._fallback(src, dst)]

    def path_cost(self, path: list) -> float:
        total = 0.0
        for i in range(1, len(path)):
            dx = abs(path[i][0] - path[i-1][0])
            dy = abs(path[i][1] - path[i-1][1])
            total += DIAG_COST if (dx and dy) else float(STEP)
        return total

    def _validate(self, path: list) -> bool:
        for i in range(1, len(path)):
            ddx = abs(path[i][0] - path[i-1][0])
            ddy = abs(path[i][1] - path[i-1][1])
            if not (ddx <= STEP and ddy <= STEP and (ddx + ddy) > 0):
                return False
        return True

    @staticmethod
    def _paths_equal(a: list, b: list) -> bool:
        return len(a) == len(b) and all(x == y for x, y in zip(a, b))