"""
Gymnasium Reinforcement Learning Environment for Fruitfly V2.
Encapsulates frozen biological CANN, continuous multi-channel sensory fields,
and 2D physical painting world.
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:
    import gym
    from gym import spaces

from biology.interfaces import BiologyConfig, CompassState, SensoryState, BrainOutput
from biology.cann import FrozenDualRingAttractor
from biology.olfactory import OlfactorySystem, OdorReading
from biology.visual import VisualSystem
from painting.world import PaintingWorld
from painting.target import PaintingTarget
from .observations import ObservationBuilder
from .actions import ActionTranslator
from .reward import PotentialRewardCalculator


class FruitFlyPaintEnv(gym.Env):
    """
    Gymnasium environment exposing Fruitfly V2 Hybrid biological painting agent.
    """

    metadata = {"render_modes": ["rgb_array", "human"], "render_fps": 10}

    def __init__(
        self,
        bio_cfg: Optional[BiologyConfig] = None,
        target: Optional[PaintingTarget] = None,
        max_episode_steps: int = 1000,
        substeps: int = 12,
        direct_torque_mode: bool = False,
        scramble_cann: bool = False,
        no_cann: bool = False,
        render_mode: Optional[str] = None,
    ):
        super().__init__()
        self.bio_cfg = bio_cfg or BiologyConfig()
        self.max_episode_steps = max_episode_steps
        self.substeps = substeps
        self.dt_macro = 0.1  # 10 Hz macro policy rate
        self.dt_sub = self.dt_macro / float(self.substeps)  # ~120 Hz internal physics rate
        self.direct_torque_mode = direct_torque_mode
        self.scramble_cann = scramble_cann
        self.no_cann = no_cann
        self.render_mode = render_mode

        # Instantiate Domain Subsystems
        self.target = target or PaintingTarget.create_solid_square()
        self.world = PaintingWorld(
            arena_width=self.bio_cfg.arena_width,
            arena_height=self.bio_cfg.arena_height,
            target=self.target,
        )

        self.cann = FrozenDualRingAttractor(
            cfg=self.bio_cfg,
            scramble_weights=self.scramble_cann,
        )

        self.olfactory = OlfactorySystem(
            pot_manager=self.world.pot_manager,
            sigma_odor=self.bio_cfg.sigma_odor,
            beta_odor=self.bio_cfg.beta_odor,
            arena_width=self.bio_cfg.arena_width,
            arena_height=self.bio_cfg.arena_height,
        )

        self.visual = VisualSystem(
            canvas=self.world.canvas,
            pot_manager=self.world.pot_manager,
            olfactory=self.olfactory,
            cfg=self.bio_cfg,
        )

        self.obs_builder = ObservationBuilder(self.bio_cfg)
        self.action_translator = ActionTranslator(self.bio_cfg)
        self.reward_calculator = PotentialRewardCalculator(v_max=self.bio_cfg.v_max)

        # Declare Gymnasium Action Space: Box [-1.0, 1.0]^4
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(4,),
            dtype=np.float32,
        )

        # Declare Gymnasium Observation Space: Dict matching section 3.1
        self.observation_space = spaces.Dict({
            "compass": spaces.Box(
                low=np.array([-1.0, -1.0, 0.0, -1.0, -1.0], dtype=np.float32),
                high=np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32),
                dtype=np.float32,
            ),
            "sensory": spaces.Box(
                low=-1.0,
                high=1.0,
                shape=(8,),
                dtype=np.float32,
            ),
            "odor": spaces.Box(
                low=0.0,
                high=1.0,
                shape=(4,),
                dtype=np.float32,
            ),
            "pigment": spaces.Box(
                low=0.0,
                high=1.0,
                shape=(5,),
                dtype=np.float32,
            ),
            "kinematics": spaces.Box(
                low=-1.0,
                high=1.0,
                shape=(4,),
                dtype=np.float32,
            ),
            "task": spaces.Box(
                low=-1.0,
                high=1.0,
                shape=(16, 16, 3),
                dtype=np.float32,
            ),
        })

        self.current_step = 0
        self.current_target_pot_id = 0

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """Resets the environment for a new episode."""
        super().reset(seed=seed)
        self.current_step = 0

        # Optional custom target from options
        if options and "target" in options:
            self.target = options["target"]
            self.world.set_target(self.target)

        # Determine start position: default or random within arena
        start_pos = None
        start_heading = None
        if options and "random_spawn" in options and options["random_spawn"]:
            rng = self.np_random
            start_pos = (
                float(rng.uniform(100.0, self.bio_cfg.arena_width - 100.0)),
                float(rng.uniform(100.0, self.bio_cfg.arena_height - 100.0)),
            )
            start_heading = float(rng.uniform(-np.pi, np.pi))

        self.world.reset(start_pos=start_pos, start_heading=start_heading)
        self.cann.reset(initial_heading=self.world.fly_theta)

        obs = self._get_obs()
        info = {
            "similarity": self.world.current_similarity,
            "reloads": self.world.reloads_count,
            "deposited_pigment": self.world.total_pigment_deposited,
        }
        return obs, info

    def _get_obs(self) -> Dict[str, np.ndarray]:
        """Constructs current observation packet."""
        compass_state = self.cann.get_state()
        sensory_state = self.visual.compute_sensory_state(
            fly_x=self.world.fly_x,
            fly_y=self.world.fly_y,
            fly_heading=self.world.fly_theta,
            fly_altitude=self.world.brush.altitude,
        )

        if self.no_cann:
            # Condition B: Pure RL baseline (Zero out biological compass)
            compass_state = CompassState(
                heading=0.0,
                sin_heading=0.0,
                cos_heading=0.0,
                coherence=0.0,
                amplitude=0.0,
                torque=0.0,
                epg_activity=np.zeros(48, dtype=np.float32),
                pen_left_mean=0.0,
                pen_right_mean=0.0,
                pfl3_bias=0.0,
            )

        return self.obs_builder.build_observation(
            compass_state=compass_state,
            sensory_state=sensory_state,
            world=self.world,
        )

    def step(
        self,
        action: np.ndarray,
    ) -> Tuple[Dict[str, np.ndarray], float, bool, bool, Dict[str, Any]]:
        """
        Executes one macro RL policy step (comprising self.substeps internal physics steps).
        """
        self.current_step += 1
        action = np.asarray(action, dtype=np.float32)

        prev_sim = self.world.current_similarity
        spill_occurred_in_macro = False

        # Execute high-frequency internal physics/CANN substeps
        for _ in range(self.substeps):
            # 1. Biological sensory odor reading for PFL3 steering
            odor_reading = self.olfactory.get_odor_reading(
                world_x=self.world.fly_x,
                world_y=self.world.fly_y,
                fly_heading=self.world.fly_theta,
                target_pot_id=self.current_target_pot_id,
            )

            # 2. Integrate biological PFL3 comparator
            omega_bio, v_auto, _, _ = self.cann.step_pfl3(
                odor_reading=odor_reading,
                dt=self.dt_sub,
                v_base=self.bio_cfg.v_cruise,
            )

            if self.no_cann or self.direct_torque_mode:
                omega_bio = 0.0

            # 3. Descending Premotor Bridge: combine biological drive with policy biases
            brain_out: BrainOutput = self.action_translator.translate(
                action=action,
                bio_steering_omega=omega_bio,
                direct_torque=self.direct_torque_mode,
            )

            # 4. Step CANN heading ring with physical turning rate
            self.cann.step(
                dt=self.dt_sub,
                omega=brain_out.steering_omega,
            )

            # 5. Step physical world kinematics, brush, and canvas deposition
            step_info = self.world.step(
                dt=self.dt_sub,
                target_v=brain_out.forward_velocity,
                steer_omega=brain_out.steering_omega,
                target_z=brain_out.altitude_command,
                pen_down=brain_out.pen_down,
                pen_pressure=brain_out.pen_pressure,
            )

            if step_info["is_spill"]:
                spill_occurred_in_macro = True

        # Calculate reward and diagnostics
        curr_sim = self.world.current_similarity
        reward, reward_info = self.reward_calculator.compute_reward(
            prev_similarity=prev_sim,
            current_similarity=curr_sim,
            spill_occurred=spill_occurred_in_macro,
            fly_velocity=self.world.fly_v,
            dt_macro=self.dt_macro,
        )

        # Check termination & truncation
        terminated = bool(curr_sim >= self.reward_calculator.target_similarity_threshold)
        truncated = bool(self.current_step >= self.max_episode_steps)

        obs = self._get_obs()
        info = {
            **reward_info,
            "similarity": curr_sim,
            "distance_flown": self.world.total_distance,
            "reloads_count": self.world.reloads_count,
            "pigment_deposited": self.world.total_pigment_deposited,
            "pigment_volume": self.world.brush.pigment_volume,
            "spills_count": self.world.total_spills,
            "step": self.current_step,
        }

        return obs, reward, terminated, truncated, info

    def render(self):
        """Renders current canvas buffer as RGB array."""
        if self.render_mode == "rgb_array":
            # Return canvas 256x256 as uint8 image (0-255)
            return (self.world.canvas.buffer * 255.0).astype(np.uint8)
        return None
