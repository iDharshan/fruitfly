"""
Altitude-Aware Brush Actuator and Pigment Reservoir for Fruitfly V2.
Models flight altitude, physical canvas contact, pen pressure, and fluid pigment flow.
"""

from typing import Tuple, Optional
import numpy as np
from .canvas import Canvas


class Brush:
    """
    Simulates the physical paintbrush attached to the fruit fly.
    """

    def __init__(
        self,
        z_cruise: float = 30.0,
        z_max: float = 50.0,
        z_contact: float = 2.0,
        flow_rate: float = 0.40,
        sigma_brush: float = 8.0,
    ):
        self.z_cruise = z_cruise
        self.z_max = z_max
        self.z_contact = z_contact
        self.flow_rate = flow_rate
        self.sigma_brush = sigma_brush

        # Dynamic state
        self.altitude = z_cruise
        self.is_down = False
        self.pressure = 0.0
        self.pigment_volume = 0.0
        self.color_id = -1
        self.color_rgb = np.array([1.0, 1.0, 1.0], dtype=np.float32)

        # Vertical velocity for smooth altitude transitions
        self.vz = 0.0
        self.climb_rate = 60.0  # px/s vertical speed

    def reset(self):
        """Resets brush to cruising altitude with empty reservoir."""
        self.altitude = self.z_cruise
        self.is_down = False
        self.pressure = 0.0
        self.pigment_volume = 0.0
        self.color_id = -1
        self.color_rgb.fill(1.0)
        self.vz = 0.0

    @property
    def in_contact(self) -> bool:
        """Returns True if the brush tip physically makes contact with the ground/surface."""
        return self.is_down and (self.altitude <= self.z_contact)

    def reload(self, color_id: int, color_rgb: Tuple[float, float, float] | np.ndarray, volume: float = 1.0):
        """Reloads brush reservoir from a paint pot."""
        self.color_id = color_id
        self.color_rgb = np.asarray(color_rgb, dtype=np.float32)
        self.pigment_volume = float(np.clip(volume, 0.0, 1.0))

    def update_altitude(self, target_z: float, dt: float):
        """Smoothly guides altitude towards target_z."""
        target_z = float(np.clip(target_z, 0.0, self.z_max))
        dz = target_z - self.altitude
        max_step = self.climb_rate * dt
        if abs(dz) <= max_step:
            self.altitude = target_z
        else:
            self.altitude += np.sign(dz) * max_step

    def step(
        self,
        dt: float,
        world_x: float,
        world_y: float,
        canvas: Optional[Canvas],
        z_target: float,
        pen_down: bool,
        pressure: float,
    ) -> Tuple[float, bool, bool]:
        """
        Integrates brush kinematics and pigment deposition.
        Returns:
            (delta_v_deposited, was_deposited_on_canvas, is_spill)
        """
        self.update_altitude(target_z=z_target, dt=dt)
        self.is_down = bool(pen_down)
        self.pressure = float(np.clip(pressure, 0.0, 1.0))

        delta_v = 0.0
        on_canvas = False
        is_spill = False

        if self.in_contact and self.pigment_volume > 1e-4:
            in_canvas_zone = canvas is not None and canvas.in_bounds(world_x, world_y)
            flow_capacity = self.flow_rate * self.pressure * dt
            deposit_v = min(self.pigment_volume, flow_capacity)

            if in_canvas_zone and deposit_v > 0.0:
                actual_dep = canvas.deposit_pigment(
                    world_x=world_x,
                    world_y=world_y,
                    color_rgb=self.color_rgb,
                    pressure=self.pressure,
                    delta_v=deposit_v,
                    sigma_brush=self.sigma_brush,
                )
                self.pigment_volume = max(0.0, self.pigment_volume - actual_dep)
                delta_v = actual_dep
                on_canvas = True
            elif not in_canvas_zone and self.pressure > 0.1:
                # Pen down on arena floor outside canvas wastes pigment
                self.pigment_volume = max(0.0, self.pigment_volume - deposit_v)
                delta_v = deposit_v
                is_spill = True

            if self.pigment_volume <= 1e-4:
                self.pigment_volume = 0.0
                self.color_id = -1

        return delta_v, on_canvas, is_spill
