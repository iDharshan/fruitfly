"""
Action Translation and Steering Bias Modulation for Fruitfly V2.
Translates PPO continuous policy actions into descending premotor commands.
"""

import numpy as np

from biology.interfaces import BrainOutput, BiologyConfig
from biology.descending import DescendingBridge


class ActionTranslator:
    """
    Translates raw policy actions into descending motor commands.
    """

    def __init__(self, cfg: BiologyConfig):
        self.cfg = cfg
        self.bridge = DescendingBridge(cfg)

    def translate(
        self,
        action: np.ndarray,
        bio_steering_omega: float = 0.0,
        direct_torque: bool = False,
    ) -> BrainOutput:
        """
        Maps normalized 4D continuous action [-1, 1]^4 into BrainOutput.
        """
        return self.bridge.process_command(
            policy_action=action,
            bio_steering_omega=bio_steering_omega,
            direct_torque=direct_torque,
        )
