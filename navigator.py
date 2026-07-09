"""
navigator.py
============
Thin shim that keeps drone.py's import statement simple.

drone.py does:   from navigator import Navigator
Navigator(src, dst) calls the factory in navigation/__init__.py which
reads config.NAVIGATOR and returns the correct strategy object.

To switch navigation strategy: change NAVIGATOR in config.py only.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from navigation import get_navigator


def Navigator(src: tuple, dst: tuple):
    """
    Return a navigator instance for the given src/dst pair.
    The concrete type is determined by config.NAVIGATOR.
    """
    return get_navigator(src, dst)
