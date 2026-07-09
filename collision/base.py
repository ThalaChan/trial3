import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abc import ABC, abstractmethod


class BaseCollisionDetector(ABC):
    """
    CONTRACT for every collision detection model.
    To add a new model:
      1. Create collision/yourmodel.py subclassing BaseCollisionDetector
      2. Implement detect()
      3. Register in collision/__init__.py
      4. Set COLLISION = "yourmodel" in config.py
    """

    @abstractmethod
    def detect(self, drone_a, drone_b) -> str:
        """
        Returns one of:
          "direct"    — both drones on the exact same grid node
          "proximity" — both drones inside the same grid square
          "none"      — no collision
        """
        pass