"""
drone.py
========
Drone entity: state, movement, battery, and rendering.

Responsibilities
----------------
  - Own all per-drone state (position, path, battery, status, timing).
  - Drive pixel-level interpolation between grid nodes every frame.
  - Expose mark_* methods so simulation.py can change drone status
    without knowing anything about drawing or physics.
  - Draw itself (body, trail, rings, label) on the canvas.

Drone status values
-------------------
  "waiting"            -- queued, takeoff tick not reached yet
  "active"             -- flying along its path
  "arrived"            -- reached destination successfully
  "crashed_direct"     -- collided at the exact same node as another drone
  "crashed_prox"       -- collided within proximity bubble of another drone
  "incomplete_battery" -- ran out of battery mid-flight
  "cancelled"          -- mission cancelled (pre-flight or in-flight)

Battery model
-------------
  battery_current = battery_start * (1 - actual_distance / planned_distance)
  Checked every frame in update(). Drone stops when it reaches 0.

Drawing order (enforced by main.py)
------------------------------------
  1. All non-battery drones
  2. Incomplete-battery drones on top (so their large ring is visible)
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from collections import deque
from datetime    import datetime

from config    import (CELL_PX, STEP, DIAG_COST,
                       RED, BLUE, WHITE, DRONE_FIELDS)
from grid      import to_px, px_to_cell
from navigator import Navigator


class Drone:
    """
    One drone in the simulation.

    Parameters
    ----------
    did          : 1-based integer drone ID
    src          : (x, y) source grid node
    dst          : (x, y) destination grid node
    color        : (R, G, B) display color
    takeoff      : grid tick at which the drone activates
    **field_values : per-drone config values (speed_mult, vehicle_type,
                     battery_start) — driven by DRONE_FIELDS in config.py
    """

    def __init__(self, did, src, dst, color, takeoff=0, **field_values):
        self.did     = did
        self.src     = src
        self.dst     = dst
        self.color   = color
        self.takeoff = takeoff

        # Navigator computes and stores all K ranked paths
        self.nav = Navigator(src, dst)

        # Set per-drone attributes from DRONE_FIELDS (speed_mult, etc.)
        for field in DRONE_FIELDS:
            attr    = field["drone_attr"]
            default = field["default"]
            val     = field_values.get(attr, default)
            setattr(self, attr, val)

        # Apply the first (optimal) path to initialise all movement state
        self._apply_path(self.nav.current_path())

    # ── Path application ──────────────────────────────────────────────────────

    def _apply_path(self, path_list: list):
        """
        Initialise all movement and status state for a new path.
        Called on construction and on every reset.
        """
        self.path      = deque(path_list)      # remaining nodes to visit
        self.grid_pos  = list(self.src)        # current logical grid position
        sp             = to_px(self.src)
        self.px        = float(sp[0])          # current pixel x
        self.py        = float(sp[1])          # current pixel y
        self.seg_ex    = float(sp[0])          # target pixel x for this segment
        self.seg_ey    = float(sp[1])          # target pixel y for this segment
        self.status    = "waiting"
        self.trail     = []                    # list of recent (px, py) for trail
        self.TRAIL_MAX = 35                    # max trail points kept
        self.crash_px  = None                  # pixel x where crash occurred
        self.crash_py  = None                  # pixel y where crash occurred

        # Distance tracking
        self.planned_distance   = 0.0   # total path cost (set on takeoff)
        self.completed_distance = 0.0   # distance of fully-completed segments
        self.actual_distance    = 0.0   # distance at time of terminal event
        self.seg_grid_len       = 0.0   # grid length of the current segment
        self.seg_start_px       = self.px
        self.seg_start_py       = self.py

        # Battery (proportional model — see docstring above)
        self.battery_current = getattr(self, "battery_start", 100.0)

        # Timing and display
        self.start_time    = "—"
        self.end_time      = "—"
        self.flight_status = "Waiting"
        self.cancel_reason = None       # "pre_flight" | "in_flight" | None

    def reset_same_path(self):
        """
        Restart on the current ranked path (same rank, same nodes).
        Called by simulation.reset() — re-runs Same Paths button.
        """
        self._apply_path(self.nav.current_path())

    def reset_new_path(self):
        """
        Advance to the next ranked path and restart from src.
        Called by simulation.new_paths() — Next Ranked Path button.
        """
        self.nav.advance_rank()
        self._apply_path(self.nav.current_path())

    # ── Segment geometry ──────────────────────────────────────────────────────

    def _segment_grid_length(self, node_a: tuple, node_b: tuple) -> float:
        """Return the grid-unit cost of moving from node_a to node_b."""
        dx = abs(node_a[0] - node_b[0])
        dy = abs(node_a[1] - node_b[1])
        return DIAG_COST if (dx > 0 and dy > 0) else float(STEP)

    def _partial_distance(self) -> float:
        """
        How far (in grid units) the drone has traveled along the
        current segment so far. Proportional to pixel progress.
        """
        px_moved = math.hypot(
            self.px - self.seg_start_px,
            self.py - self.seg_start_py)
        px_total = math.hypot(
            self.seg_ex - self.seg_start_px,
            self.seg_ey - self.seg_start_py)
        if px_total < 0.001:
            return 0.0
        return min(px_moved / px_total, 1.0) * self.seg_grid_len

    def _live_actual(self) -> float:
        """Total distance traveled so far (completed segments + partial)."""
        return self.completed_distance + self._partial_distance()

    def _update_battery(self):
        """
        Recalculate battery_current using the proportional model.
        Called every frame while active and on every terminal event.
        """
        planned = self.planned_distance
        if planned <= 0:
            return
        fraction_used     = min(self._live_actual() / planned, 1.0)
        self.battery_current = max(
            0.0,
            getattr(self, "battery_start", 100.0) * (1.0 - fraction_used))

    # ── Activation ────────────────────────────────────────────────────────────

    def mark_active(self):
        """
        Called by simulation.update() when the drone's takeoff tick arrives.
        Records start time and planned path cost.
        """
        self.start_time       = self._now()
        self.flight_status    = "Active"
        self.planned_distance = self.nav.path_cost()

        # Initialise segment length for the first hop
        path_list = list(self.path)
        if len(path_list) >= 2:
            self.seg_grid_len = self._segment_grid_length(
                tuple(path_list[0]), tuple(path_list[1]))
            self.seg_start_px = self.px
            self.seg_start_py = self.py

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # ── Terminal state setters ────────────────────────────────────────────────
    # All mark_* methods freeze actual distance and battery, then set status.

    def _mark_terminal_mid_segment(self, status_key: str, label: str):
        """Shared logic for any terminal event that happens mid-flight."""
        self.actual_distance = self._live_actual()
        self._update_battery()
        self.status        = status_key
        self.flight_status = label
        self.end_time      = self._now()

    def _mark_arrived(self):
        """Drone reached destination — complete success."""
        self.actual_distance = self.completed_distance
        self._update_battery()
        self.status        = "arrived"
        self.flight_status = "Complete"
        self.end_time      = self._now()

    def mark_crash_direct(self):
        """Two drones occupied the exact same node at the same tick."""
        px, py = to_px(tuple(self.grid_pos))
        self.crash_px = float(px)
        self.crash_py = float(py)
        self._mark_terminal_mid_segment(
            "crashed_direct", "Collision — Node to Node")

    def mark_crash_prox(self):
        """Two drones were within each other's proximity bubble."""
        self.crash_px = self.px
        self.crash_py = self.py
        self._mark_terminal_mid_segment(
            "crashed_prox", "Collision — Proximity")

    def mark_incomplete_battery(self):
        """Drone ran out of battery before reaching its destination."""
        self.crash_px = self.px
        self.crash_py = self.py
        self._mark_terminal_mid_segment(
            "incomplete_battery", "Incomplete — Battery")

    def mark_cancelled_preflight(self):
        """Mission cancelled before the drone ever took off."""
        self.cancel_reason    = "pre_flight"
        self.actual_distance  = 0.0
        self.planned_distance = self.nav.path_cost()
        self.battery_current  = getattr(self, "battery_start", 100.0)
        sp = to_px(self.src)
        self.crash_px      = float(sp[0])
        self.crash_py      = float(sp[1])
        self.status        = "cancelled"
        self.flight_status = "Cancelled — Pre-flight"
        self.end_time      = self._now()

    def mark_cancelled_inflight(self):
        """Mission cancelled after the drone was already flying."""
        self.cancel_reason = "in_flight"
        self.crash_px      = self.px
        self.crash_py      = self.py
        self._mark_terminal_mid_segment(
            "cancelled", "Cancelled — In-flight")

    # ── Movement ──────────────────────────────────────────────────────────────

    def start_next_segment(self):
        """
        Advance the drone to the next node in its path.
        Called by simulation.update() each grid tick when at_node() is True.
        If the path has no more nodes the drone is marked as arrived.
        """
        path_list = list(self.path)
        if len(path_list) > 1:
            self.completed_distance += self.seg_grid_len
            prev_node = tuple(self.grid_pos)
            self.path.popleft()
            nxt           = self.path[0]
            self.grid_pos = list(nxt)
            ex, ey        = to_px(nxt)
            self.seg_start_px = self.px
            self.seg_start_py = self.py
            self.seg_ex       = float(ex)
            self.seg_ey       = float(ey)
            self.seg_grid_len = self._segment_grid_length(
                prev_node, tuple(nxt))
        else:
            # Last node reached — mission complete
            self.completed_distance += self.seg_grid_len
            self._mark_arrived()

    def at_node(self) -> bool:
        """True when the drone has reached the end of its current segment."""
        return (self.px == self.seg_ex and self.py == self.seg_ey)

    def update(self, base_spd_px: float):
        """
        Move the drone toward its current segment endpoint by one frame.

        Parameters
        ----------
        base_spd_px : pixels per frame from the panel speed slider
                      (multiplied by the drone's own speed_mult)
        """
        if self.status != "active":
            return

        spd  = base_spd_px * getattr(self, "speed_mult", 1.0)
        dx   = self.seg_ex - self.px
        dy   = self.seg_ey - self.py
        dist = math.hypot(dx, dy)

        if dist <= spd:
            # Snap to target so at_node() returns True next tick
            self.px = self.seg_ex
            self.py = self.seg_ey
        else:
            self.px += dx / dist * spd
            self.py += dy / dist * spd

        self._update_battery()

        if self.battery_current <= 0.0:
            self.mark_incomplete_battery()
            return

        # Append to trail (used for the fading tail visual)
        self.trail.append((self.px, self.py))
        if len(self.trail) > self.TRAIL_MAX:
            self.trail.pop(0)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self, surf, ftiny, all_drones=None):
        """
        Render this drone onto surf.

        Visual encoding
        ---------------
          active           → colored dot + speed ring + battery ring + trail
          crashed_direct   → red dot with light-red ring
          crashed_prox     → blue dot with light-blue ring
          incomplete_batt  → bright purple, three rings (stands out over bubbles)
          cancelled PRE    → grey dot + yellow ring   label: Dx CNCL-P
          cancelled IN     → orange dot + orange ring  label: Dx CNCL-I
          waiting/arrived  → invisible

        Parameters
        ----------
        surf       : pygame surface to draw on
        ftiny      : tiny font for ID labels
        all_drones : full list of drones (for partner lookup in crash labels)
        """
        if self.status in ("waiting", "arrived"):
            return

        # Draw position: crash position if stopped, else live pixel position
        ipx = int(self.crash_px if self.crash_px is not None else self.px)
        ipy = int(self.crash_py if self.crash_py is not None else self.py)

        # ── Fading trail ──────────────────────────────────────────────────
        if self.status == "active" and len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                t     = i / len(self.trail)
                r,g,b = self.color
                col   = (int(r*t*0.7), int(g*t*0.7), int(b*t*0.7))
                pygame.draw.line(surf, col,
                    (int(self.trail[i-1][0]), int(self.trail[i-1][1])),
                    (int(self.trail[i][0]),   int(self.trail[i][1])),
                    max(1, int(t*3)))

        # ── Body (color depends on status) ────────────────────────────────
        if self.status == "crashed_direct":
            pygame.draw.circle(surf, RED,           (ipx,ipy), 7)
            pygame.draw.circle(surf, (255,180,180), (ipx,ipy), 7, 2)

        elif self.status == "crashed_prox":
            pygame.draw.circle(surf, BLUE,          (ipx,ipy), 7)
            pygame.draw.circle(surf, (160,220,255), (ipx,ipy), 7, 2)

        elif self.status == "incomplete_battery":
            # Three concentric rings — must be visible even under bubbles
            pygame.draw.circle(surf, (180, 60, 255), (ipx,ipy), 9)
            pygame.draw.circle(surf, (220,160,255),  (ipx,ipy), 9, 2)
            pygame.draw.circle(surf, (200,100,255),  (ipx,ipy), 14, 2)
            pygame.draw.circle(surf, (180, 60, 255), (ipx,ipy), 19, 1)

        elif self.status == "cancelled":
            if self.cancel_reason == "pre_flight":
                # Grey — never flew
                pygame.draw.circle(surf, (160,160,160), (ipx,ipy), 7)
                pygame.draw.circle(surf, (210,210,210), (ipx,ipy), 7, 2)
                pygame.draw.circle(surf, (220,220,80),  (ipx,ipy), 11, 1)
            else:
                # Orange — flew then cancelled
                pygame.draw.circle(surf, (220,130,20), (ipx,ipy), 7)
                pygame.draw.circle(surf, (255,185,70), (ipx,ipy), 7, 2)
                pygame.draw.circle(surf, (255,200,50), (ipx,ipy), 11, 1)

        else:
            # Active drone
            pygame.draw.circle(surf, self.color, (ipx,ipy), 5)
            pygame.draw.circle(surf, WHITE,      (ipx,ipy), 5, 1)

        # ── Active rings (speed + battery) ────────────────────────────────
        if self.status == "active":
            spd = getattr(self, "speed_mult", 1.0)
            # Speed ring: green=slow, yellow=normal, red=fast
            speed_color = (
                (80,220,130)  if spd < 0.8
                else (255,210,50) if spd <= 1.2
                else (255,100,80))
            pygame.draw.circle(surf, speed_color, (ipx,ipy), 8, 1)
            # Battery ring: green=high, yellow=medium, red=critical
            bat = self.battery_current / 100.0
            bat_color = (
                (60,220,110)  if bat > 0.5
                else (255,210,50) if bat > 0.2
                else (255,55,55))
            pygame.draw.circle(surf, bat_color, (ipx,ipy), 11, 1)

        # ── ID label ──────────────────────────────────────────────────────
        if self.status == "crashed_direct":
            # Show "D1+D2" centered above crash point for colliding pair
            partners = [
                d for d in (all_drones or [])
                if d is not self
                and d.status == "crashed_direct"
                and d.crash_px is not None
                and abs(d.crash_px - self.crash_px) < 3
                and abs(d.crash_py - self.crash_py) < 3
            ]
            if partners and self.did < partners[0].did:
                lbl = ftiny.render(
                    f"D{self.did}+D{partners[0].did}",
                    True, (255,200,200))
                surf.blit(lbl, (ipx - lbl.get_width()//2, ipy-18))
            elif not partners:
                lbl = ftiny.render(f"D{self.did}", True, RED)
                surf.blit(lbl, (ipx+8, ipy-8))

        elif self.status == "crashed_prox":
            lbl = ftiny.render(f"D{self.did} PROX", True, (160,220,255))
            surf.blit(lbl, (ipx+8, ipy-8))

        elif self.status == "incomplete_battery":
            lbl = ftiny.render(f"D{self.did} BAT⚡", True, (220,160,255))
            surf.blit(lbl, (ipx+10, ipy-10))

        elif self.status == "cancelled":
            tag = "CNCL-P" if self.cancel_reason == "pre_flight" else "CNCL-I"
            col = (210,210,100) if self.cancel_reason == "pre_flight" \
                  else (255,185,70)
            lbl = ftiny.render(f"D{self.did} {tag}", True, col)
            surf.blit(lbl, (ipx+8, ipy-8))

        else:
            # Active: show ID, speed multiplier, battery %
            spd = getattr(self, "speed_mult", 1.0)
            bat = self.battery_current
            lbl = ftiny.render(
                f"D{self.did} ×{spd:.1f} B{bat:.0f}%", True, WHITE)
            surf.blit(lbl, (ipx+6, ipy-6))

    def draw_path_lines(self, surf):
        """
        Draw faint lines along the drone's remaining planned path.
        Only called for active drones so players can see where each
        drone is headed.
        """
        nodes = list(self.path)
        if len(nodes) < 2:
            return
        r, g, b = self.color
        for i in range(1, len(nodes)):
            ax, ay = to_px(nodes[i-1])
            bx, by = to_px(nodes[i])
            pygame.draw.line(surf, (r//6, g//6, b//6),
                             (ax,ay), (bx,by), 1)

    def draw_bubble(self, surf, alpha: int = 35):
        """
        Draw the safety bubble (proximity radius) around an active drone.
        Visualises the collision detection zone. Toggled by the Bubbles
        button in the side panel.
        """
        if self.status != "active":
            return
        half    = int(CELL_PX * 0.48)
        ipx,ipy = int(self.px), int(self.py)
        r,g,b   = self.color
        s = pygame.Surface((half*2, half*2), pygame.SRCALPHA)
        s.fill((r//3, g//3, b//3, alpha))
        pygame.draw.rect(s, (r,g,b,80), (0,0,half*2,half*2), 1)
        surf.blit(s, (ipx-half, ipy-half))
