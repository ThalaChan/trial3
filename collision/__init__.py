"""
collision/__init__.py
=====================
Factory — returns the configured collision detector instance.

To add a new collision detection model
----------------------------------------
  1. Create collision/yourmodel.py subclassing BaseCollisionDetector.
  2. Implement detect(drone_a, drone_b) -> str.
  3. Add an elif branch in get_collision_detector() below.
  4. Set COLLISION = "yourmodel" in config.py.
  Nothing else in the project needs to change.

Available implementations
--------------------------
  "cell_based" -> CellBasedDetector
      Proximity bubble model with four severity levels.
      Uses per-vehicle radii from config.VEHICLE_PROXIMITY_RADIUS.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_collision_detector():
    """Return the configured collision detector instance."""
    from config import COLLISION

    print(f"[Collision] Loading: {COLLISION}")

    if COLLISION == "cell_based":
        from collision.cell_based import CellBasedDetector
        return CellBasedDetector()
    else:
        raise ValueError(
            f"Unknown COLLISION '{COLLISION}'. "
            f"Available: 'cell_based'"
        )
