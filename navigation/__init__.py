"""
navigation/__init__.py
======================
Factory — returns the configured navigator instance for a src/dst pair.

To add a new navigation strategy
----------------------------------
  1. Create navigation/yourstrategy.py subclassing BaseNavigator.
  2. Implement all abstract methods.
  3. Add an elif branch in get_navigator() below.
  4. Set NAVIGATOR = "yourstrategy" in config.py.
  Nothing else in the project needs to change.

Available implementations
--------------------------
  "ranked" -> RankedNavigator  (cycles through Yen's K ranked paths)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_navigator(src: tuple, dst: tuple):
    """
    Return a navigator instance for the given src/dst pair.
    The concrete type is determined by config.NAVIGATOR.
    """
    from config import NAVIGATOR

    if NAVIGATOR == "ranked":
        from navigation.ranked import RankedNavigator
        return RankedNavigator(src, dst)
    else:
        raise ValueError(
            f"Unknown NAVIGATOR '{NAVIGATOR}'. "
            f"Available: 'ranked'"
        )
