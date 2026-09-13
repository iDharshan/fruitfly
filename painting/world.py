"""
Canonical PaintingSimulation World State for Fruitfly V2.
Coordinates arena bounds, fly kinematics, canvas surface, paint pots, brush actuator, and task progress.
"""

from typing import Tuple, Optional, Dict, Any
import numpy as np

from .canvas import Canvas
from .brush import Brush
from .paint_pot import PotManager, PaintPot
from .target import PaintingTarget
from toy.circuit import wrap_angle, ang_dist


class PaintingWorld:
    """
    Authoritative 2D physics and painting simulation world.
    """

    def __init__(
        self,
        arena_width: float = 1000.0,
        arena_height: float = 1000.0,
        target: Optional[PaintingTarget] = None,
        canvas_center: Tuple[float, float] = (500.0, 500.0),
        canvas_size: int = 256,
        eval_size: int = 32,
    ):
        self.arena_width = arena_width
        self.arena_height = arena_height

        self.canvas = Canvas(
            center_x=canvas_center[0],
            center_y=canvas_center[1],
            size=canvas_size,
            eval_size=eval_size,
        )

        self.pot_manager = PotManager()
        self.brush = Brush(
            z_cruise=30.0,
            z_max=50.0,
            z_contact=2.0,
            flow_rate=0.40,
            sigma_brush=8.0,
        )

        self.target = target or PaintingTarget.create_solid_square()

        # Fly Kinematics
        self.fly_x = 500.0
        self.fly_y = 750.0
        self.fly_theta = -np.pi / 2.0  # Facing up towards canvas
        self.fly_v = 0.0
        self.fly_omega = 0.0

        # Telemetry & Statistics
        self.total_distance = 0.0
        self.total_pigment_used = 0.0
        self.total_pigment_deposited = 0.0
        self.total_spills = 0
        self.reloads_count = 0
        self.step_count = 0
        self.current_similarity = self.canvas.compute_similarity(self.target.eval_grid)

    def reset(
        self,
        start_pos: Optional[Tuple[float, float]] = None,
        start_heading: Optional[float] = None,
        target: Optional[PaintingTarget] = None,
    ):
        """Resets the world, canvas, brush, and agent position."""
        if target is not None:
            self.target = target

        self.canvas.reset()
        self.brush.reset()

        if start_pos is not None:
            self.fly_x, self.fly_y = float(start_pos[0]), float(start_pos[1])
        else:
            # Default start just below canvas
            self.fly_x = 500.0
            self.fly_y = 750.0

        if start_heading is not None:
            self.fly_theta = float(wrap_angle(start_heading))
        else:
            self.fly_theta = -np.pi / 2.0

        self.fly_v = 0.0
        self.fly_omega = 0.0

        self.total_distance = 0.0
        self.total_pigment_used = 0.0
        self.total_pigment_deposited = 0.0
        self.total_spills = 0
        self.reloads_count = 0
        self.step_count = 0
        self.current_similarity = self.canvas.compute_similarity(self.target.eval_grid)

    def set_target(self, target: PaintingTarget):
        """Updates target and re-evaluates initial similarity."""
        self.target = target
        self.current_similarity = self.canvas.compute_similarity(self.target.eval_grid)

    def step(
        self,
        dt: float,
        target_v: float,
        steer_omega: float,
        target_z: float,
        pen_down: bool,
        pen_pressure: float,
    ) -> Dict[str, Any]:
        """
        Integrates world physics over dt seconds.
        """
        self.step_count += 1
        self.fly_omega = float(np.clip(steer_omega, -5.0, 5.0))
        self.fly_v = float(np.clip(target_v, 0.0, 250.0))

        # Kinematic integration
        self.fly_theta = float(wrap_angle(self.fly_theta + self.fly_omega * dt))
        dx = self.fly_v * np.cos(self.fly_theta) * dt
        dy = self.fly_v * np.sin(self.fly_theta) * dt

        self.fly_x = float(np.clip(self.fly_x + dx, 20.0, self.arena_width - 20.0))
        self.fly_y = float(np.clip(self.fly_y + dy, 20.0, self.arena_height - 20.0))
        self.total_distance += float(np.hypot(dx, dy))

        # Check paint pot reload
        reloaded_pot = self.pot_manager.check_reload(
            world_x=self.fly_x,
            world_y=self.fly_y,
            altitude=self.brush.altitude,
            z_contact=self.brush.z_contact,
        )
        reloaded = False
        if reloaded_pot is not None:
            self.brush.reload(
                color_id=reloaded_pot.pot_id,
                color_rgb=reloaded_pot.color_rgb,
                volume=1.0,
            )
            self.reloads_count += 1
            reloaded = True

        # Step brush and deposit pigment
        dep_v, on_canvas, is_spill = self.brush.step(
            dt=dt,
            world_x=self.fly_x,
            world_y=self.fly_y,
            canvas=self.canvas,
            z_target=target_z,
            pen_down=pen_down,
            pressure=pen_pressure,
        )

        if on_canvas:
            self.total_pigment_deposited += dep_v
            self.total_pigment_used += dep_v
        if is_spill:
            self.total_pigment_used += dep_v
            self.total_spills += 1

        # Compute updated similarity
        prev_sim = self.current_similarity
        self.current_similarity = self.canvas.compute_similarity(self.target.eval_grid)
        delta_sim = self.current_similarity - prev_sim

        return {
            "delta_v": dep_v,
            "on_canvas": on_canvas,
            "is_spill": is_spill,
            "reloaded": reloaded,
            "reloaded_pot": reloaded_pot,
            "similarity": self.current_similarity,
            "delta_similarity": delta_sim,
        }
