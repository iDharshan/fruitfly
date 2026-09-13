"""
Deterministic Scripted Baseline Painting Agent for Fruitfly V2.
Implements a state machine controller that executes:
  IDLE -> SEEK_POT -> DIP_RELOAD -> SEEK_CANVAS -> EXECUTE_STROKE -> FINISH
Achieves S > 0.85 without any machine learning, validating world mechanics.
"""

from typing import Tuple, List, Optional
import numpy as np
from enum import Enum, auto

from .world import PaintingWorld
from .paint_pot import PaintPot
from toy.circuit import wrap_angle, ang_dist


class AgentState(Enum):
    IDLE = auto()
    SEEK_POT = auto()
    DIP_RELOAD = auto()
    SEEK_CANVAS = auto()
    EXECUTE_STROKE = auto()
    FINISH = auto()


class ScriptedPaintingFly:
    """
    Deterministic rule-based agent serving as Condition A baseline.
    """

    def __init__(
        self,
        world: PaintingWorld,
        target_color_id: int = 0,
        stroke_step_y: float = 12.0,
    ):
        self.world = world
        self.target_color_id = target_color_id
        self.state = AgentState.SEEK_POT
        self.stroke_step_y = stroke_step_y

        self.pot = self.world.pot_manager.get_pot_by_id(target_color_id)
        if self.pot is None:
            self.pot = self.world.pot_manager[0]

        # Generate stroke plan based on target bounds
        self.waypoints: List[Tuple[float, float]] = []
        self._generate_stroke_plan()
        self.current_wp_idx = 0
        self.reload_timer = 0.0

    def _generate_stroke_plan(self):
        """Generates a raster scan over the target non-white region on canvas."""
        c = self.world.canvas
        high_res = self.world.target.high_res
        # Non-white pixels: where any channel differs from white (1.0)
        diff_from_white = np.any(np.abs(high_res - 1.0) > 0.1, axis=-1)
        ys, xs = np.where(diff_from_white)

        if len(xs) == 0 or len(ys) == 0:
            # Fallback center box
            x_start = c.center_x - 50.0
            x_end = c.center_x + 50.0
            y_start = c.center_y - 50.0
            y_end = c.center_y + 50.0
        else:
            u_min, u_max = float(np.min(xs)), float(np.max(xs))
            v_min, v_max = float(np.min(ys)), float(np.max(ys))
            x_start = c.x_min + u_min + 4.0
            x_end = c.x_min + u_max - 4.0
            y_start = c.y_min + v_min + 4.0
            y_end = c.y_min + v_max - 4.0

        y = y_start
        direction = 1
        while y <= y_end + 1.0:
            if direction == 1:
                self.waypoints.append((x_start, y))
                self.waypoints.append((x_end, y))
            else:
                self.waypoints.append((x_end, y))
                self.waypoints.append((x_start, y))
            direction *= -1
            y += self.stroke_step_y

    def reset(self):
        """Resets the scripted state machine."""
        self.state = AgentState.SEEK_POT
        self.current_wp_idx = 0
        self.reload_timer = 0.0

    def step(self, dt: float) -> Tuple[float, float, float, bool, float]:
        """
        Computes control commands for the current state.
        Returns:
            (target_v, steer_omega, target_z, pen_down, pen_pressure)
        """
        fx, fy = self.world.fly_x, self.world.fly_y
        theta = self.world.fly_theta
        brush = self.world.brush

        # Proportional navigation helper
        def steer_toward(tx: float, ty: float) -> Tuple[float, float]:
            target_angle = np.arctan2(ty - fy, tx - fx)
            err = float(ang_dist(target_angle, theta))
            omega = float(np.clip(err * 4.0, -4.5, 4.5))
            dist = float(np.hypot(tx - fx, ty - fy))
            return omega, dist

        # State Machine Transitions
        if self.state == AgentState.SEEK_POT:
            target_z = 30.0  # Cruising altitude
            pen_down = False
            pressure = 0.0
            omega, dist = steer_toward(self.pot.x, self.pot.y)
            v = 150.0 if dist > 60.0 else 60.0

            if dist < self.pot.radius * 0.7:
                self.state = AgentState.DIP_RELOAD
                self.reload_timer = 0.0
            return v, omega, target_z, pen_down, pressure

        elif self.state == AgentState.DIP_RELOAD:
            target_z = 0.0  # Descend to ground contact
            pen_down = False
            pressure = 0.0
            omega, dist = steer_toward(self.pot.x, self.pot.y)
            v = 15.0  # Crawl inside pot basin

            if brush.pigment_volume > 0.9:
                # Reload complete!
                self.state = AgentState.SEEK_CANVAS
            return v, omega, target_z, pen_down, pressure

        elif self.state == AgentState.SEEK_CANVAS:
            if self.current_wp_idx >= len(self.waypoints):
                self.state = AgentState.FINISH
                return 0.0, 0.0, 30.0, False, 0.0

            tx, ty = self.waypoints[self.current_wp_idx]
            target_z = 30.0  # Cruise over to waypoint
            pen_down = False
            pressure = 0.0
            omega, dist = steer_toward(tx, ty)
            v = 140.0 if dist > 40.0 else 50.0

            if dist < 20.0:
                self.state = AgentState.EXECUTE_STROKE
            return v, omega, target_z, pen_down, pressure

        elif self.state == AgentState.EXECUTE_STROKE:
            if brush.pigment_volume <= 0.05:
                # Need reload!
                self.state = AgentState.SEEK_POT
                return 60.0, 0.0, 30.0, False, 0.0

            if self.current_wp_idx >= len(self.waypoints):
                self.state = AgentState.FINISH
                return 0.0, 0.0, 30.0, False, 0.0

            tx, ty = self.waypoints[self.current_wp_idx]
            target_z = 0.0  # Pen in physical contact
            pen_down = True
            pressure = 1.0
            omega, dist = steer_toward(tx, ty)
            v = 80.0

            if dist < 12.0:
                # Reached waypoint
                self.current_wp_idx += 1
                if self.current_wp_idx >= len(self.waypoints):
                    self.state = AgentState.FINISH
            return v, omega, target_z, pen_down, pressure

        elif self.state == AgentState.FINISH:
            # Task complete, hover or land
            return 0.0, 0.0, 30.0, False, 0.0

        return 0.0, 0.0, 30.0, False, 0.0
