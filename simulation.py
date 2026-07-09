"""
simulation.py
=============
Orchestrates the entire simulation loop.

Responsibilities
----------------
  - Build drones from configs (normalise, assign colors, stagger takeoffs).
  - Apply random pre-flight and in-flight cancellations.
  - Each frame: activate drones, advance nodes, detect collisions,
    spawn VFX particles, update heatmap, tick logger.
  - Expose reset() / new_paths() / reset_full() for the UI panel.
  - Provide stats() for the panel display.

Module-level constants
----------------------
  CANCEL_PREFLIGHT_PROB : probability a waiting drone is cancelled before takeoff
  CANCEL_INFLIGHT_PROB  : probability an active drone is cancelled each grid tick

Collision flow (each grid tick)
--------------------------------
  For every active pair (a, b):
    detector.detect(a, b) returns:
      "direct"    -> mark both crashed, log Critical, red particle burst
      "major"     -> mark both crashed, log Major,    blue particle burst
      "minor"     -> mark both crashed, log Minor,    blue particle burst
      "near_miss" -> log Near Miss only (drones keep flying)
      "none"      -> nothing
"""

import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config    import DRONE_COLORS, DRONE_FIELDS, SPEED_BASE, SPEED_SCALE
from drone     import Drone
from vfx       import Particle, HeatMap
from collision import get_collision_detector
from logger    import CollisionLogger

# ── Cancellation probabilities ────────────────────────────────────────────────
CANCEL_PREFLIGHT_PROB = 0.05    # 5%  chance before takeoff
CANCEL_INFLIGHT_PROB  = 0.008   # 0.8% chance per grid tick while flying


class Simulation:
    """
    Runs the UTM drone simulation.

    Parameters
    ----------
    configs : list of drone config dicts produced by SetupScreen or file_loader
    """

    def __init__(self, configs: list):
        self.configs  = self._normalise(configs)
        self.detector = get_collision_detector()
        self.logger   = CollisionLogger()
        self._build_drones()
        self.logger.next_run(label=self._current_run_label())
        self._reset_state()

    # ── Setup helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _normalise(configs: list) -> list:
        """
        Accept configs as dicts or (src, dst) tuples.
        Fills in defaults for any missing fields.
        """
        from config import DEFAULT_DRONE_SPEED, DEFAULT_BATTERY
        out = []
        for c in configs:
            if isinstance(c, dict):
                out.append(c)
            else:
                src, dst = c
                out.append({
                    "src"          : src,
                    "dst"          : dst,
                    "speed_mult"   : DEFAULT_DRONE_SPEED,
                    "vehicle_type" : "quad",
                    "battery_start": DEFAULT_BATTERY,
                })
        return out

    def _build_drones(self):
        """
        Construct all Drone objects, stagger takeoff ticks, apply
        pre-flight cancellations.
        """
        # Stagger takeoffs over ~25% of the fleet size in grid ticks
        spread = max(1, len(self.configs) // 4)
        self.drones = []

        for i, cfg in enumerate(self.configs):
            col     = DRONE_COLORS[i % len(DRONE_COLORS)]
            takeoff = random.randint(0, spread)

            # Build kwargs from DRONE_FIELDS (speed_mult, vehicle_type, etc.)
            field_kwargs = {}
            for field in DRONE_FIELDS:
                attr = field["drone_attr"]
                field_kwargs[attr] = cfg.get(attr, field["default"])

            self.drones.append(
                Drone(i + 1, cfg["src"], cfg["dst"], col,
                      takeoff=takeoff, **field_kwargs))

        # Apply pre-flight cancellations at build time
        for d in self.drones:
            if random.random() < CANCEL_PREFLIGHT_PROB:
                d.mark_cancelled_preflight()

    def _apply_preflight_cancellations(self):
        """Re-apply pre-flight cancellations after a reset (waiting drones only)."""
        for d in self.drones:
            if (d.status == "waiting"
                    and random.random() < CANCEL_PREFLIGHT_PROB):
                d.mark_cancelled_preflight()

    def _reset_state(self):
        """Reset all simulation-level counters and VFX."""
        self.particles      = []
        self.heatmap        = HeatMap()
        self.frame          = 0
        self.grid_tick      = 0
        self.direct_count   = 0
        self.prox_count     = 0
        self.nearmiss_count = 0
        self.cancel_count   = 0

    # ── Public reset methods (called by UI panel buttons) ─────────────────────

    def reset(self):
        """
        Replay the current ranked path from the beginning for all drones.
        Triggered by the "Same Paths" button or R key.
        """
        for d in self.drones:
            d.reset_same_path()
        self.logger.next_run(label=self._current_run_label())
        self._reset_state()
        self._apply_preflight_cancellations()

    def new_paths(self):
        """
        Advance all drones to their next ranked alternative path.
        Triggered by the "Next Ranked Path" button or P key.
        """
        for d in self.drones:
            d.reset_new_path()
        self.logger.next_run(label=self._current_run_label())
        self._reset_state()
        self._apply_preflight_cancellations()

    def reset_full(self):
        """
        Complete teardown: same as reset() but also wipes the logger.
        Called when returning to the Setup screen.
        """
        for d in self.drones:
            d.reset_same_path()
        self.logger.reset()
        self.logger.next_run(label=self._current_run_label())
        self._reset_state()
        self._apply_preflight_cancellations()

    def save_log(self, custom_name: str = "") -> str:
        """Export the collision log to Excel (or CSV). Returns the file path."""
        return self.logger.save(custom_name=custom_name, drones=self.drones)

    def _current_run_label(self) -> str:
        """Human-readable label for the current path rank (e.g. '#1 optimal')."""
        return self.drones[0].nav.rank_label() if self.drones else "run"

    # ── Main update (called every frame by main.py) ───────────────────────────

    def update(self, speed: int):
        """
        Advance the simulation by one frame.

        Parameters
        ----------
        speed : panel slider value (1-10) controlling simulation speed
        """
        self.frame += 1
        # Convert slider value to pixels per frame
        spd_px    = SPEED_BASE + speed * SPEED_SCALE
        # Grid ticks advance more slowly at higher frame rates
        adv_every = max(1, 22 - speed * 2)

        if self.frame % adv_every == 0:
            self.grid_tick += 1

            # ── Activate drones whose takeoff tick has arrived ────────────
            for d in self.drones:
                if (d.status == "waiting"
                        and self.grid_tick >= d.takeoff):
                    d.status = "active"
                    d.mark_active()

            # ── Random in-flight cancellations ────────────────────────────
            # Only cancel drones that have moved at least one segment
            for d in self.drones:
                if (d.status == "active"
                        and d.completed_distance > 0
                        and random.random() < CANCEL_INFLIGHT_PROB):
                    d.mark_cancelled_inflight()
                    self.cancel_count += 1
                    self._burst_cancel((d.crash_px, d.crash_py))

            # ── Advance nodes ─────────────────────────────────────────────
            for d in self.drones:
                if d.status == "active" and d.at_node():
                    d.start_next_segment()

            # ── Collision detection ───────────────────────────────────────
            active = [d for d in self.drones if d.status == "active"]
            for i in range(len(active)):
                for j in range(i + 1, len(active)):
                    a, b   = active[i], active[j]
                    result = self.detector.detect(a, b)

                    if result == "direct":
                        if a.status == b.status == "active":
                            self.direct_count += 1
                            a.mark_crash_direct()
                            b.mark_crash_direct()
                            self.logger.log(
                                self.grid_tick, "direct", "Critical", a, b)
                            self._burst((a.crash_px, a.crash_py), "direct", 45)
                            self.heatmap.add(a.grid_pos[0], a.grid_pos[1],
                                             "direct", 8.0)

                    elif result in ("major", "minor"):
                        if a.status == b.status == "active":
                            self.prox_count += 1
                            sev = "Major" if result == "major" else "Minor"
                            a.mark_crash_prox()
                            b.mark_crash_prox()
                            self.logger.log(
                                self.grid_tick, "proximity", sev, a, b)
                            self._burst((a.crash_px, a.crash_py), "prox", 20)
                            self._burst((b.crash_px, b.crash_py), "prox", 20)
                            self.heatmap.add(a.grid_pos[0], a.grid_pos[1],
                                             "prox", 6.0)
                            self.heatmap.add(b.grid_pos[0], b.grid_pos[1],
                                             "prox", 6.0)

                    elif result == "near_miss":
                        self.nearmiss_count += 1
                        self.logger.log(
                            self.grid_tick, "near_miss", "Near Miss", a, b)

        # ── Pixel movement every frame ────────────────────────────────────
        for d in self.drones:
            d.update(spd_px)

        # ── VFX tick ──────────────────────────────────────────────────────
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        self.heatmap.tick()

    # ── VFX helpers ───────────────────────────────────────────────────────────

    def _burst(self, pos: tuple, kind: str, n: int):
        """Spawn n explosion particles at pos."""
        for _ in range(n):
            self.particles.append(Particle(pos[0], pos[1], kind))

    def _burst_cancel(self, pos: tuple):
        """Spawn yellow cancel particles at pos."""
        for _ in range(25):
            self.particles.append(Particle(pos[0], pos[1], "cancel"))

    # ── Stats (read by panel.py) ──────────────────────────────────────────────

    def stats(self) -> tuple:
        """Return (active, waiting, arrived, crashed, direct_count, prox_count)."""
        active  = sum(1 for d in self.drones if d.status == "active")
        waiting = sum(1 for d in self.drones if d.status == "waiting")
        arrived = sum(1 for d in self.drones if d.status == "arrived")
        crashed = sum(1 for d in self.drones
                      if "crashed" in d.status or d.status == "incomplete_battery")
        return (active, waiting, arrived, crashed,
                self.direct_count, self.prox_count)
