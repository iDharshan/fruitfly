"""
Painting domain module for Fruitfly V2.
Encapsulates canvas surface, altitude-aware brush, paint pots, target processing, and world state.
"""

from .canvas import Canvas
from .brush import Brush
from .paint_pot import PaintPot, PotManager
from .target import PaintingTarget
from .world import PaintingWorld
from .scripted_agent import ScriptedPaintingFly

__all__ = [
    "Canvas",
    "Brush",
    "PaintPot",
    "PotManager",
    "PaintingTarget",
    "PaintingWorld",
    "ScriptedPaintingFly",
]
