"""
Biological Descending Neuron (DN) Integration Bridge for Fruitfly V2.
Integrates Central Complex steering drives with high-level behavioral policy biases.
"""

from typing import Optional
import numpy as np

from .interfaces import BrainOutput, BiologyConfig
from .motor import MotorPrimitives


class DescendingBridge:
    """
    Biological bridge mapping central brain commands (PFL3 comparator + policy)
    to VNC premotor flight primitives.
    """

    def __init__(self, cfg: Optional[BiologyConfig] = None):
        self.cfg = cfg or BiologyConfig()
        self.motor = MotorPrimitives(self.cfg)

    def process_command(
        self,
        policy_action: np.ndarray,
        bio_steering_omega: float = 0.0,
        direct_torque: bool = False,
    ) -> BrainOutput:
        """
        Synthesizes descending signals into motor command primitives.
        """
        return self.motor.translate_actions_to_brain_output(
            action=policy_action,
            bio_omega=bio_steering_omega,
            direct_torque_mode=direct_torque,
        )
