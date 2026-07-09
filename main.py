"""
main.py
=======
Application entry point for the UTM Drone Traffic Simulator.

Responsibilities
----------------
  - Initialise pygame and create the window.
  - Own the application state machine: "setup" -> "sim".
  - Route pygame events to the correct handler (SetupScreen or SimPanel).
  - Call simulation.update() and draw everything in the correct order.
  - Handle keyboard shortcuts (SPACE, R, N, P).

Application modes
-----------------
  "setup"  SetupScreen is visible. User enters drone configs.
           Transitions to "sim" when SetupScreen.done() returns True.

  "sim"    Simulation is running. SimPanel is visible on the right.
           Can return to "setup" via the New Drone Setup button or N key.

Draw order in "sim" mode (layers, bottom to top)
-------------------------------------------------
  1. Background fill (BG color)
  2. Grid lines and node dots         (draw_grid)
  3. Heatmap blobs                    (sim.heatmap.draw)
  4. Safety bubbles (if enabled)      (drone.draw_bubble)
  5. Planned path lines (active only) (drone.draw_path_lines)
  6. All drones except battery-dead   (drone.draw)
  7. Battery-dead drones              (drone.draw)  <- on top so rings visible
  8. Explosion particles              (particle.draw)
  9. Side panel                       (panel.draw)
 10. Pause overlay (if paused)

Keyboard shortcuts (sim mode)
------------------------------
  SPACE  pause / resume
  R      restart current path (same nodes, same ranks)
  N      return to drone setup screen
  P      cycle all drones to next ranked path
"""

import pygame
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config           import WIDTH, HEIGHT, SIM_W, PANEL_W, FPS, BG, TEXT
from simulation       import Simulation
from ui.setup         import SetupScreen
from ui.panel         import SimPanel
from ui.grid_renderer import draw_grid


class App:
    """
    Top-level application controller.

    Owns the pygame window, clock, fonts, and the active mode.
    Delegates all domain logic to Simulation, SetupScreen, and SimPanel.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("UTM Drone Traffic Simulator")
        self.clock  = pygame.time.Clock()

        # Three font sizes used across the UI
        # fonts[0] = large bold (titles, paused overlay)
        # fonts[1] = medium (panel stats, setup prompts)
        # fonts[2] = small  (labels, hints, legend)
        self.fonts = (
            pygame.font.SysFont("consolas", 15, bold=True),
            pygame.font.SysFont("consolas", 13),
            pygame.font.SysFont("consolas", 11),
        )
        # Tiny font for drone ID labels on the canvas
        self.ftiny = pygame.font.SysFont("consolas", 9)

        # Start on the setup screen; sim is created when setup is done
        self.mode   = "setup"
        self.setup  = SetupScreen(self.fonts)
        self.sim    = None
        self.panel  = None
        self.paused = False

    # ── Mode transitions ──────────────────────────────────────────────────────

    def goto_setup(self):
        """
        Transition from sim back to setup.
        Fully resets the simulation (clears the collision logger).
        """
        if self.sim is not None:
            self.sim.reset_full()
        self.mode   = "setup"
        self.setup  = SetupScreen(self.fonts)
        self.paused = False

    def start_sim(self):
        """
        Transition from setup to sim.
        Creates the Simulation from the configs collected by SetupScreen.
        """
        self.sim    = Simulation(self.setup.configs)
        self.panel  = SimPanel(SIM_W, PANEL_W, HEIGHT)
        self.mode   = "sim"
        self.paused = False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        """Game loop — runs until the window is closed."""
        while True:
            # ── Event handling ────────────────────────────────────────────
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if self.mode == "setup":
                    # Forward all events to setup; start sim when ready
                    self.setup.handle(ev)
                    if self.setup.done():
                        self.start_sim()

                else:
                    # Panel handles slider drag, button clicks, and file naming
                    self.panel.handle(ev, self.sim, self)

                    # Keyboard shortcuts (skip when naming an export file)
                    if (ev.type == pygame.KEYDOWN
                            and not self.panel.is_naming()):
                        if ev.key == pygame.K_SPACE:
                            self.paused = not self.paused
                        if ev.key == pygame.K_r:
                            self.sim.reset()
                        if ev.key == pygame.K_n:
                            self.goto_setup()
                        if ev.key == pygame.K_p:
                            self.sim.new_paths()

            # ── Rendering ─────────────────────────────────────────────────
            if self.mode == "setup":
                self.setup.draw(self.screen, WIDTH, HEIGHT)

            else:
                # Advance simulation when not paused
                if not self.paused:
                    self.sim.update(self.panel.speed)

                # Layer 1: background
                self.screen.fill(BG)
                # Layer 2: grid
                draw_grid(self.screen, self.fonts)
                # Layer 3: heatmap (persistent crash hotspots)
                self.sim.heatmap.draw(self.screen)

                # Layer 4: safety bubbles (optional)
                if self.panel.show_bubbles:
                    for d in self.sim.drones:
                        d.draw_bubble(self.screen)

                # Layer 5: planned path lines (active drones only)
                for d in self.sim.drones:
                    if d.status == "active":
                        d.draw_path_lines(self.screen)

                # Layer 6: all drones except battery-dead (so they appear below)
                for d in self.sim.drones:
                    if d.status != "incomplete_battery":
                        d.draw(self.screen, self.ftiny, self.sim.drones)

                # Layer 7: battery-dead drones on top so their rings are visible
                for d in self.sim.drones:
                    if d.status == "incomplete_battery":
                        d.draw(self.screen, self.ftiny, self.sim.drones)

                # Layer 8: explosion / cancel particles
                for p in self.sim.particles:
                    p.draw(self.screen)

                # Layer 9: side panel
                self.panel.draw(self.screen, self.sim, self.fonts)

                # Layer 10: pause overlay
                if self.paused:
                    ov = pygame.Surface((SIM_W, HEIGHT), pygame.SRCALPHA)
                    ov.fill((0, 0, 0, 85))
                    self.screen.blit(ov, (0, 0))
                    lb = self.fonts[0].render(
                        "PAUSED — SPACE to resume", True, TEXT)
                    self.screen.blit(
                        lb, (SIM_W//2 - lb.get_width()//2, HEIGHT//2))

                pygame.display.flip()

            self.clock.tick(FPS)


if __name__ == "__main__":
    App().run()
