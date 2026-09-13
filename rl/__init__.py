"""
Reinforcement Learning package for Fruitfly V2 Hybrid Architecture.
Provides Gymnasium environment, potential-based reward engine, observation extractors,
and Stable-Baselines3 training/evaluation harness.
"""

from .env import FruitFlyPaintEnv
from .reward import PotentialRewardCalculator
from .observations import ObservationBuilder
from .actions import ActionTranslator

__all__ = [
    "FruitFlyPaintEnv",
    "PotentialRewardCalculator",
    "ObservationBuilder",
    "ActionTranslator",
]
