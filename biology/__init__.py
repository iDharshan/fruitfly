"""
Biology module for Fruitfly V2 Hybrid Architecture.
Contains frozen CANN, sensory systems, and premotor interfaces.
"""

from .interfaces import CompassState, SensoryState, BrainOutput, BiologyConfig
from .cann import FrozenDualRingAttractor

__all__ = [
    "CompassState",
    "SensoryState",
    "BrainOutput",
    "BiologyConfig",
    "FrozenDualRingAttractor",
]
