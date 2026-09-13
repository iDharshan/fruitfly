"""
Observation Builder and Tensor Normalization for Fruitfly V2.
Constructs strictly bounded gymnasium.spaces.Dict observation packets.
"""

from typing import Dict, Any
import numpy as np

from biology.interfaces import CompassState, SensoryState, BiologyConfig
from painting.world import PaintingWorld


class ObservationBuilder:
    """
    Constructs normalized, mathematically sound observation dictionaries for RL.
    """

    def __init__(self, cfg: BiologyConfig):
        self.cfg = cfg

    def build_observation(
        self,
        compass_state: CompassState,
        sensory_state: SensoryState,
        world: PaintingWorld,
    ) -> Dict[str, np.ndarray]:
        """
        Builds the 6-component observation dictionary.
        """
        brush = world.brush

        # 1. Compass: [sin(theta), cos(theta), coherence, torque, pfl3_bias] (5,)
        compass_vec = np.array(
            [
                compass_state.sin_heading,
                compass_state.cos_heading,
                np.clip(compass_state.coherence, 0.0, 1.0),
                np.clip(compass_state.torque, -1.0, 1.0),
                np.clip(compass_state.pfl3_bias, -1.0, 1.0),
            ],
            dtype=np.float32,
        )

        # 2. Sensory: (8,) in [-1, 1]
        sensory_vec = sensory_state.to_sensory_vector()

        # 3. Odor: (4,) in [0, 1]
        odor_vec = sensory_state.to_odor_vector()

        # 4. Pigment Reservoir: (5,) in [0, 1]
        is_r = 1.0 if (brush.color_id == 0 and brush.pigment_volume > 0.0) else 0.0
        is_g = 1.0 if (brush.color_id == 1 and brush.pigment_volume > 0.0) else 0.0
        is_b = 1.0 if (brush.color_id == 2 and brush.pigment_volume > 0.0) else 0.0
        is_y = 1.0 if (brush.color_id == 3 and brush.pigment_volume > 0.0) else 0.0
        pigment_vec = np.array(
            [
                np.clip(brush.pigment_volume, 0.0, 1.0),
                is_r,
                is_g,
                is_b,
                is_y,
            ],
            dtype=np.float32,
        )

        # 5. Kinematics: (4,) in [-1, 1]
        v_norm = float(np.clip(world.fly_v / self.cfg.v_max * 2.0 - 1.0, -1.0, 1.0))
        pen_down_val = 1.0 if brush.is_down else -1.0
        pen_pressure_val = float(np.clip(brush.pressure * 2.0 - 1.0, -1.0, 1.0))
        alt_val = float(np.clip(brush.altitude / self.cfg.z_max * 2.0 - 1.0, -1.0, 1.0))
        kinematics_vec = np.array(
            [v_norm, pen_down_val, pen_pressure_val, alt_val],
            dtype=np.float32,
        )

        # 6. Task Discrepancy: (16, 16, 3) in [-1, 1]
        canvas_grid = world.canvas.get_policy_grid()
        task_diff = world.target.get_task_discrepancy(canvas_grid)

        return {
            "compass": compass_vec,
            "sensory": sensory_vec,
            "odor": odor_vec,
            "pigment": pigment_vec,
            "kinematics": kinematics_vec,
            "task": task_diff,
        }
