"""
Physical Canvas Surface for Fruitfly V2.
Maintains high-resolution visual buffer (256x256 RGB) and accelerated evaluation grid (32x32 RGB).
Supports fast Gaussian pigment deposition and telescoping similarity evaluation.
"""

from typing import Tuple, Optional
import numpy as np


class Canvas:
    """
    Simulates the physical canvas within the arena.
    Arena placement: Centered by default at (500, 500) with size 256x256.
    """

    def __init__(
        self,
        center_x: float = 500.0,
        center_y: float = 500.0,
        size: int = 256,
        eval_size: int = 32,
    ):
        self.size = size
        self.eval_size = eval_size
        self.block_size = self.size // self.eval_size  # e.g., 8

        self.center_x = center_x
        self.center_y = center_y
        self.half_size = size / 2.0

        self.x_min = center_x - self.half_size
        self.x_max = center_x + self.half_size
        self.y_min = center_y - self.half_size
        self.y_max = center_y + self.half_size

        # High-resolution canvas buffer: (256, 256, 3) float32 in [0.0, 1.0], initialized to white
        self.buffer = np.ones((self.size, self.size, 3), dtype=np.float32)

        # Preallocated evaluation buffer (32, 32, 3)
        self._eval_buffer = np.ones((self.eval_size, self.eval_size, 3), dtype=np.float32)

    def reset(self):
        """Clears canvas to pristine white."""
        self.buffer.fill(1.0)
        self._eval_buffer.fill(1.0)

    def in_bounds(self, world_x: float, world_y: float) -> bool:
        """Returns True if world coordinates lie within canvas boundaries."""
        return (self.x_min <= world_x <= self.x_max) and (self.y_min <= world_y <= self.y_max)

    def world_to_canvas(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """Converts arena world coordinates to continuous canvas pixel coordinates [0, size]."""
        u_x = world_x - self.x_min
        u_y = world_y - self.y_min
        return u_x, u_y

    def canvas_to_world(self, u_x: float, u_y: float) -> Tuple[float, float]:
        """Converts canvas pixel coordinates to arena world coordinates."""
        world_x = self.x_min + u_x
        world_y = self.y_min + u_y
        return world_x, world_y

    def deposit_pigment(
        self,
        world_x: float,
        world_y: float,
        color_rgb: Tuple[float, float, float] | np.ndarray,
        pressure: float,
        delta_v: float,
        sigma_brush: float = 3.5,
    ) -> float:
        """
        Deposits pigment onto the canvas using a 2D Gaussian stamp footprint.
        Returns actual volume deposited.
        """
        if not self.in_bounds(world_x, world_y) or delta_v <= 0.0 or pressure <= 0.0:
            return 0.0

        u_x, u_y = self.world_to_canvas(world_x, world_y)
        cx = int(round(u_x))
        cy = int(round(u_y))

        radius = int(np.ceil(3.0 * sigma_brush))
        x0 = max(0, cx - radius)
        x1 = min(self.size, cx + radius + 1)
        y0 = max(0, cy - radius)
        y1 = min(self.size, cy + radius + 1)

        if x0 >= x1 or y0 >= y1:
            return 0.0

        # Create localized coordinate grid
        xs = np.arange(x0, x1, dtype=np.float32) - u_x
        ys = np.arange(y0, y1, dtype=np.float32) - u_y
        grid_x, grid_y = np.meshgrid(xs, ys)
        dist_sq = grid_x ** 2 + grid_y ** 2

        # 2D Gaussian footprint
        gauss = np.exp(-dist_sq / (2.0 * (sigma_brush ** 2)))

        # Alpha deposition rate
        deposit_strength = np.clip((delta_v * 150.0 / (sigma_brush + 1.0)) * pressure, 0.0, 0.98)
        alpha_stamp = (deposit_strength * gauss)[:, :, np.newaxis]

        target_color = np.asarray(color_rgb, dtype=np.float32).reshape(1, 1, 3)

        # Alpha blend into visual buffer: C <- (1 - alpha) * C + alpha * Color
        self.buffer[y0:y1, x0:x1, :] = (
            (1.0 - alpha_stamp) * self.buffer[y0:y1, x0:x1, :] + alpha_stamp * target_color
        )

        return delta_v

    def get_evaluation_grid(self) -> np.ndarray:
        """
        Downsamples 256x256 canvas buffer into 32x32 RGB evaluation grid via block averaging.
        Operates in <0.1ms using pure NumPy array reshaping.
        """
        # Shape: (32, 8, 32, 8, 3) -> mean over (1, 3) -> (32, 32, 3)
        reshaped = self.buffer.reshape(
            self.eval_size, self.block_size, self.eval_size, self.block_size, 3
        )
        self._eval_buffer = reshaped.mean(axis=(1, 3))
        return self._eval_buffer

    def get_policy_grid(self) -> np.ndarray:
        """
        Downsamples to 16x16 RGB grid for compact policy observation.
        """
        policy_size = 16
        block = self.size // policy_size  # 16
        reshaped = self.buffer.reshape(policy_size, block, policy_size, block, 3)
        return reshaped.mean(axis=(1, 3)).astype(np.float32)

    def compute_similarity(self, target_eval: np.ndarray) -> float:
        """
        Computes normalized L1 similarity S in [0.0, 1.0] against target evaluation grid:
          S = 1.0 - mean(|C_eval - Target_eval|)
        """
        c_eval = self.get_evaluation_grid()
        l1_diff = float(np.mean(np.abs(c_eval - target_eval)))
        return float(np.clip(1.0 - l1_diff, 0.0, 1.0))
