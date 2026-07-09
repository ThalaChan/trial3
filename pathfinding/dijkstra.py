import heapq
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config          import GRID_UNITS, STEP, DIAG_COST
from pathfinding.base import BasePathfinder


ALL_MOVES = [
    ( STEP,  0,    float(STEP)),
    (-STEP,  0,    float(STEP)),
    ( 0,  STEP,    float(STEP)),
    ( 0, -STEP,    float(STEP)),
    ( STEP,  STEP, DIAG_COST),
    ( STEP, -STEP, DIAG_COST),
    (-STEP,  STEP, DIAG_COST),
    (-STEP, -STEP, DIAG_COST),
]


def _build_graph():
    graph = {}
    for x in range(0, GRID_UNITS + 1, STEP):
        for y in range(0, GRID_UNITS + 1, STEP):
            nbrs = []
            for mx, my, cost in ALL_MOVES:
                nx, ny = x + mx, y + my
                if 0 <= nx <= GRID_UNITS and 0 <= ny <= GRID_UNITS:
                    nbrs.append(((nx, ny), cost))
            graph[(x, y)] = nbrs
    return graph


GRAPH = _build_graph()


def run_dijkstra(src, dst, blocked_nodes=None, blocked_edges=None):
    """
    Core Dijkstra on GRAPH.
    blocked_nodes : set of (x,y) nodes to skip
    blocked_edges : set of ((x1,y1),(x2,y2)) directed pairs to skip
    Returns (cost, path) or (inf, None) if unreachable.
    """
    blocked_nodes = blocked_nodes or set()
    blocked_edges = blocked_edges or set()

    if src in blocked_nodes or dst in blocked_nodes:
        return float('inf'), None

    dist = {src: 0.0}
    prev = {src: None}
    heap = [(0.0, src)]

    while heap:
        cost, node = heapq.heappop(heap)
        if cost > dist.get(node, float('inf')):
            continue
        if node == dst:
            break
        for nbr, ec in GRAPH.get(node, []):
            if nbr in blocked_nodes:
                continue
            if (node, nbr) in blocked_edges:
                continue
            nc = cost + ec
            if nc < dist.get(nbr, float('inf')):
                dist[nbr] = nc
                prev[nbr] = node
                heapq.heappush(heap, (nc, nbr))

    if dst not in dist:
        return float('inf'), None

    path = []
    cur  = dst
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()

    if not path or path[0] != src:
        return float('inf'), None

    return dist[dst], path


class DijkstraPathfinder(BasePathfinder):
    """
    Single shortest path using Dijkstra.
    Returns only one path (the optimal).
    Use YenPathfinder if you need ranked alternatives.
    """

    def compute_paths(self, src, dst, k=None):
        src, dst = tuple(src), tuple(dst)
        _, path  = run_dijkstra(src, dst)
        if path is None:
            path = self._fallback(src, dst)
        return [path]

    def path_cost(self, path):
        total = 0.0
        for i in range(1, len(path)):
            dx = abs(path[i][0] - path[i-1][0])
            dy = abs(path[i][1] - path[i-1][1])
            total += DIAG_COST if (dx and dy) else float(STEP)
        return total

    def _fallback(self, src, dst):
        """Direct Manhattan+diagonal tail used only if graph fails."""
        path = [src]
        cx, cy = src
        tx, ty = dst
        while cx != tx or cy != ty:
            mx = 0 if cx == tx else (STEP if cx < tx else -STEP)
            my = 0 if cy == ty else (STEP if cy < ty else -STEP)
            cx += mx
            cy += my
            path.append((cx, cy))
        return path