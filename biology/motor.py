"""
Biological Ventral Nerve Cord (VNC) Premotor Circuits & Flight Primitives for Fruitfly V2.
Translates high-level descending drives into smooth aerodynamic flight and brush actuation.
"""

from typing import Tuple, Optional
import numpy as np

from .interfaces import BrainOutput, BiologyConfig


class MotorPrimitives:
    """
    VNC premotor execution layer.
    Executes stable flight primitives: cruise, yaw modulation, altitude management, and pen contact.
    """

    def __init__(self, cfg: Optional[BiologyConfig] = None):
        self.cfg = cfg or BiologyConfig()

        # Kinematic limits
        self.v_min = self.cfg.v_min
        self.v_max = self.cfg.v_max
        self.omega_max = self.cfg.omega_max
        self.omega_bias_max = self.cfg.omega_bias_max
        self.z_max = self.cfg.z_max
        self.z_cruise = self.cfg.z_cruise
        self.z_contact = self.cfg.z_contact

    def translate_actions_to_brain_output(
        self,
        action: np.ndarray,
        bio_omega: float = 0.0,
        direct_torque_mode: bool = False,
    ) -> BrainOutput:
        """
        Translates normalized 4D continuous action [-1, 1]^4 into BrainOutput.

        action[0]: Heading bias (a_0 in [-1, 1])
        action[1]: Forward throttle (a_1 in [-1, 1])
        action[2]: Altitude command (a_2 in [-1, 1])
        action[3]: Brush actuation (a_3 in [-1, 1])
        """
        a0 = float(np.clip(action[0], -1.0, 1.0))
        a1 = float(np.clip(action[1], -1.0, 1.0))
        a2 = float(np.clip(action[2], -1.0, 1.0))
        a3 = float(np.clip(action[3], -1.0, 1.0))

        if direct_torque_mode:
            # Condition E: Raw motor torque without biological VNC primitives
            steer_omega = float(np.clip(a0 * self.omega_max, -self.omega_max, self.omega_max))
            forward_v = float(np.clip(((a1 + 1.0) / 2.0) * self.v_max, 0.0, self.v_max))
            target_z = float(np.clip(((a2 + 1.0) / 2.0) * self.z_max, 0.0, self.z_max))
            pen_down = bool(a3 > 0.0)
            pressure = float(np.clip(a3, 0.0, 1.0)) if pen_down else 0.0
            return BrainOutput(
                steering_omega=steer_omega,
                forward_velocity=forward_v,
                altitude_command=target_z,
                pen_pressure=pressure,
                pen_down=pen_down,
            )

        # Standard Hybrid Mode:
        # 1. Yaw steering: biological comparator + learned residual bias
        steer_omega = float(np.clip(
            bio_omega + a0 * self.omega_bias_max,
            -self.omega_max,
            self.omega_max,
        ))

        # 2. Forward Throttle mapped to [v_min, v_max]
        throttle_norm = (a1 + 1.0) / 2.0
        forward_v = float(self.v_min + throttle_norm * (self.v_max - self.v_min))

        # 3. Altitude command: a2 > 0 -> cruising, a2 <= 0 -> descent to ground
        if a2 > 0.0:
            target_z = float(self.z_contact + a2 * (self.z_max - self.z_contact))
        else:
            target_z = 0.0

        # 4. Brush actuation: a3 > 0 -> pen down with pressure a3, a3 <= 0 -> pen up
        pen_down = bool(a3 > 0.0)
        pressure = float(np.clip(a3, 0.0, 1.0)) if pen_down else 0.0

        return BrainOutput(
            steering_omega=steer_omega,
            forward_velocity=forward_v,
            altitude_command=target_z,
            pen_pressure=pressure,
            pen_down=pen_down,
        )
