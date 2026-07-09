import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abc import ABC, abstractmethod


class BaseNavigator(ABC):
    """
    CONTRACT for every navigation strategy.

    Navigator owns WHERE the drone goes.
    Drone owns HOW it moves (pixel interpolation).

    To add a new strategy (priority-based, fuel-aware, etc.):
      1. Create navigation/yourstrategy.py subclassing BaseNavigator
      2. Implement all abstract methods
      3. Register in navigation/__init__.py
      4. Set NAVIGATOR = "yourstrategy" in config.py
    """

    @abstractmethod
    def current_path(self) -> list:
        """Return the active path as a list of (x,y) nodes."""
        pass

    @abstractmethod
    def advance_rank(self):
        """Move to the next alternative path."""
        pass

    @abstractmethod
    def rank_label(self) -> str:
        """Human-readable label e.g. '#1 optimal', '#2 alt'."""
        pass

    @abstractmethod
    def rank_index(self) -> int:
        """Zero-based index of the current path."""
        pass

    @abstractmethod
    def path_cost(self) -> float:
        """Geometric cost of the current path."""
        pass

    @abstractmethod
    def total_ranks(self) -> int:
        """How many ranked paths are available."""
        pass