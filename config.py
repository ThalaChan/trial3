"""
config.py
=========
Central configuration for the UTM Drone Traffic Simulator.

ALL tuneable parameters live here. No other file should contain
magic numbers — import from here instead.

Sections
--------
  Window          — screen and simulation area dimensions
  Grid            — airspace grid geometry
  Algorithms      — which pathfinder / collision model / navigator to use
  Drone speed     — default speed and slider-to-pixel curve
  Collision       — per-vehicle safety radii and severity thresholds
  Battery         — battery drain model
  Drone fields    — data-driven field definitions (auto-propagate to UI)
  Log columns     — data-driven Excel/CSV column definitions
  Colors          — all UI colors in one place
"""

import math

# ── Window ────────────────────────────────────────────────────────────────────
# Total window size and simulation area width.
# PANEL_W is derived automatically so panel + sim = full window.

WIDTH   = 960   # total window width  (px)
HEIGHT  = 740   # total window height (px)
SIM_W   = 700   # simulation canvas width (px); panel is to the right
PANEL_W = WIDTH - SIM_W   # right-side stats panel width (px)
FPS     = 60    # target frame rate

# ── Grid ──────────────────────────────────────────────────────────────────────
# The airspace is modelled as a 2-D grid.
# GRID_UNITS = total axis length in "air units"  (0 … 50)
# STEP       = distance between adjacent nodes   (5 air units)
# CELLS      = number of cells per axis          (50/5 = 10)
# CELL_PX    = pixel size of one cell
# PAD        = pixel margin around the grid on the canvas
# DIAG_COST  = cost of moving diagonally one step (Pythagorean)

GRID_UNITS = 50
STEP       = 5
CELLS      = GRID_UNITS // STEP           # = 10
CELL_PX    = (SIM_W - 80) // CELLS       # = 62 px per cell
PAD        = 40
DIAG_COST  = STEP * math.sqrt(2)         # ≈ 7.07

# ── Algorithm selection ───────────────────────────────────────────────────────
# Change these strings to switch implementations without touching any
# other file. Each factory (__init__.py) reads these at runtime.

PATHFINDER = "yen"        # "yen" | "dijkstra"
COLLISION  = "cell_based" # "cell_based"
NAVIGATOR  = "ranked"     # "ranked"
K_PATHS    = 10           # how many ranked paths Yen's algorithm computes

# ── Drone speed ───────────────────────────────────────────────────────────────
# DEFAULT_DRONE_SPEED is the per-drone multiplier used when no speed
# is specified in the import file or manual entry.
#
# The panel speed slider (1–10) maps to pixels-per-frame via:
#   spd_px = SPEED_BASE + slider_value × SPEED_SCALE
# At slider=1:   spd_px ≈ 1.2 px/frame  (very slow)
# At slider=10:  spd_px ≈ 9.3 px/frame  (very fast)

DEFAULT_DRONE_SPEED = 1.0   # neutral multiplier
SPEED_BASE          = 0.3   # minimum pixel speed (slider at 1)
SPEED_SCALE         = 0.9   # pixels added per slider unit

# ── Collision physics ─────────────────────────────────────────────────────────
# Per-vehicle safety bubble in grid units.
# The collision detector always uses the LARGER of the two colliding
# vehicles' radii — so a fixed_wing always gets 10-unit protection.
#
# Severity thresholds are fractions of the effective radius:
#   direct    → distance == 0                          (always Critical)
#   major     → distance <= radius × MAJOR_RATIO       (Major)
#   minor     → distance <= radius × MINOR_RATIO       (Minor)
#   near_miss → distance <= radius × NEARMISS_RATIO    (Near Miss, no crash)

VEHICLE_PROXIMITY_RADIUS = {
    "quad"      :  5.0,   # small rotor craft
    "hexa"      :  6.0,   # six-rotor, larger frame
    "octa"      :  7.0,   # eight-rotor, larger still
    "vtol"      :  8.0,   # needs space for hover→forward transition
    "fixed_wing": 10.0,   # wingspan is the danger
}

SEVERITY_MAJOR_RATIO    = 0.5   # critical proximity
SEVERITY_MINOR_RATIO    = 1.0   # within bubble
SEVERITY_NEARMISS_RATIO = 1.5   # warning zone, drones keep flying

# ── Battery ───────────────────────────────────────────────────────────────────
# Linear proportional model:
#   battery_current = battery_start × (1 – actual_distance / planned_distance)
#
# Example: drone planned 60 units, flew 30 units with battery_start = 80%
#   → battery_current = 80% × (1 – 30/60) = 40%
#
# When battery_current reaches 0 the drone stops immediately
# with status "incomplete_battery".

DEFAULT_BATTERY = 100.0   # % used when battery column is blank

# ── Drone fields ──────────────────────────────────────────────────────────────
# Data-driven field definitions. Adding a new field here automatically
# propagates to: file_loader (import), simulation (construction),
# drone (attribute), and ui/setup (manual entry).
#
# Keys per entry:
#   name        → column header in import files (lowercase)
#   default     → fallback value when blank
#   parse       → validation + type conversion function (returns None on fail)
#   drone_attr  → attribute name set on the Drone object
#   log         → whether to include in Excel export
#   display     → help text shown in the setup screen and import template

def _parse_speed(v):
    """Accept 0.1–5.0; reject everything else."""
    try:
        f = float(str(v).strip())
        return f if 0.1 <= f <= 5.0 else None
    except Exception:
        return None

def _parse_battery(v):
    """Accept 0–100; reject everything else."""
    try:
        f = float(str(v).strip())
        return f if 0.0 <= f <= 100.0 else None
    except Exception:
        return None

def _parse_vehicle(v):
    """Accept known vehicle type strings; reject everything else."""
    valid = {"quad", "hexa", "octa", "vtol", "fixed_wing"}
    if v is None:
        return None
    s = str(v).strip().lower()
    return s if s in valid else None

DRONE_FIELDS = [
    {
        "name"      : "speed",
        "default"   : DEFAULT_DRONE_SPEED,
        "parse"     : _parse_speed,
        "drone_attr": "speed_mult",
        "log"       : True,
        "display"   : "Speed multiplier (0.1–5.0, default=1.0)",
    },
    {
        "name"      : "vehicle_type",
        "default"   : "quad",
        "parse"     : _parse_vehicle,
        "drone_attr": "vehicle_type",
        "log"       : True,
        "display"   : "Vehicle: quad/hexa/octa/vtol/fixed_wing",
    },
    {
        "name"      : "battery_start",
        "default"   : DEFAULT_BATTERY,
        "parse"     : _parse_battery,
        "drone_attr": "battery_start",
        "log"       : True,
        "display"   : "Battery start % (0–100, default=100)",
    },
]

# ── Log columns ───────────────────────────────────────────────────────────────
# One dict = one column in the Excel Collision Log sheet.
# The logger handles these six internally (value lambda is ignored):
#   Event ID, Path Run, Path Label, Timestamp, Type, Severity
# All other columns call value(grid_tick, drone_a, drone_b).

LOG_COLUMNS = [
    {"header": "Event ID",   "value": lambda t,a,b: None},
    {"header": "Path Run",   "value": lambda t,a,b: None},
    {"header": "Path Label", "value": lambda t,a,b: None},
    {"header": "Timestamp",  "value": lambda t,a,b: None},
    {"header": "Grid Tick",  "value": lambda t,a,b: t},
    {"header": "Type",       "value": lambda t,a,b: None},
    {"header": "Severity",   "value": lambda t,a,b: None},

    {"header": "Drone A ID",      "value": lambda t,a,b: a.did},
    {"header": "Drone B ID",      "value": lambda t,a,b: b.did},
    {"header": "Drone A Vehicle", "value": lambda t,a,b: getattr(a, "vehicle_type", "quad")},
    {"header": "Drone B Vehicle", "value": lambda t,a,b: getattr(b, "vehicle_type", "quad")},
    {"header": "Drone A Speed",   "value": lambda t,a,b: f"{a.speed_mult:.2f}×"},
    {"header": "Drone B Speed",   "value": lambda t,a,b: f"{b.speed_mult:.2f}×"},
    {"header": "Drone A Source",  "value": lambda t,a,b: str(a.src)},
    {"header": "Drone A Destination", "value": lambda t,a,b: str(a.dst)},
    {"header": "Drone B Source",  "value": lambda t,a,b: str(b.src)},
    {"header": "Drone B Destination", "value": lambda t,a,b: str(b.dst)},
    {"header": "Drone A Coord X", "value": lambda t,a,b: int(a.grid_pos[0])},
    {"header": "Drone A Coord Y", "value": lambda t,a,b: int(a.grid_pos[1])},
    {"header": "Drone B Coord X", "value": lambda t,a,b: int(b.grid_pos[0])},
    {"header": "Drone B Coord Y", "value": lambda t,a,b: int(b.grid_pos[1])},
    {"header": "Drone A Path Rank",      "value": lambda t,a,b: a.nav.rank_label()},
    {"header": "Drone B Path Rank",      "value": lambda t,a,b: b.nav.rank_label()},
    {"header": "Drone A Battery Start",  "value": lambda t,a,b: f"{getattr(a,'battery_start',100):.1f}%"},
    {"header": "Drone B Battery Start",  "value": lambda t,a,b: f"{getattr(b,'battery_start',100):.1f}%"},
    {"header": "Drone A Battery End",    "value": lambda t,a,b: f"{getattr(a,'battery_current',100):.1f}%"},
    {"header": "Drone B Battery End",    "value": lambda t,a,b: f"{getattr(b,'battery_current',100):.1f}%"},
    {"header": "Drone A Battery Consumed",
     "value": lambda t,a,b: f"{getattr(a,'battery_start',100)-getattr(a,'battery_current',100):.1f}%"},
    {"header": "Drone B Battery Consumed",
     "value": lambda t,a,b: f"{getattr(b,'battery_start',100)-getattr(b,'battery_current',100):.1f}%"},
    {"header": "Drone A Distance Planned",
     "value": lambda t,a,b: round(getattr(a,"planned_distance", a.nav.path_cost()), 2)},
    {"header": "Drone B Distance Planned",
     "value": lambda t,a,b: round(getattr(b,"planned_distance", b.nav.path_cost()), 2)},
    {"header": "Drone A Distance Actual",
     "value": lambda t,a,b: round(getattr(a,"actual_distance", 0.0), 2)},
    {"header": "Drone B Distance Actual",
     "value": lambda t,a,b: round(getattr(b,"actual_distance", 0.0), 2)},
    {"header": "Drone A Start Time", "value": lambda t,a,b: getattr(a,"start_time","—")},
    {"header": "Drone B Start Time", "value": lambda t,a,b: getattr(b,"start_time","—")},
    {"header": "Drone A End Time",   "value": lambda t,a,b: getattr(a,"end_time","—")},
    {"header": "Drone B End Time",   "value": lambda t,a,b: getattr(b,"end_time","—")},
]

# ── Colors ────────────────────────────────────────────────────────────────────
# All UI colors live here. Drone-specific colors use DRONE_COLORS list
# which cycles when there are more drones than colors.

BG       = (8,   12,  28)    # simulation canvas background (dark navy)
GRID_L   = (28,  36,  62)    # grid line color
NODE_C   = (45,  58,  95)    # grid node dot color
PANEL_BG = (12,  17,  36)    # right panel background
TEXT     = (210, 220, 240)   # primary text
MUTED    = (90,  105, 140)   # secondary / hint text
WHITE    = (255, 255, 255)
RED      = (255,  55,  55)   # direct collision
ORANGE   = (255, 140,  40)   # in-flight cancellation
YELLOW   = (255, 210,  50)   # pre-flight cancellation ring
CYAN     = (60,  200, 255)   # active drones
GREEN    = (60,  220, 110)   # arrived / success
BLUE     = (50,  160, 255)   # proximity collision

# 12 distinct drone colors that cycle if more than 12 drones are used
DRONE_COLORS = [
    (100, 200, 255), (255, 160,  80), (120, 255, 160), (255,  80, 180),
    (200, 130, 255), ( 80, 230, 200), (255, 220,  80), (255, 120, 120),
    (160, 255, 100), (255, 200, 140), (140, 180, 255), (255, 170, 120),
]
