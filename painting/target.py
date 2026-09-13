"""
Target image processor and structured representation for Fruitfly V2.
Generates multi-resolution visual representations:
  - 256x256 high-resolution ground truth
  - 32x32 evaluation buffer for fast reward calculation
  - 16x16 RGB + Sobel edge map + 8-bin palette for compact RL observation
"""

from typing import Tuple, Optional, List
from pathlib import Path
import numpy as np
from scipy.ndimage import sobel


class PaintingTarget:
    """
    Encapsulates the goal visual pattern to be painted onto the canvas.
    """

    def __init__(self, high_res_rgb: np.ndarray, name: str = "custom_target"):
        """
        high_res_rgb: (256, 256, 3) float32 in [0.0, 1.0].
        """
        assert high_res_rgb.shape == (256, 256, 3), f"Expected (256, 256, 3), got {high_res_rgb.shape}"
        self.name = name
        self.high_res = np.clip(high_res_rgb, 0.0, 1.0).astype(np.float32)

        # 32x32 evaluation target for fast reward calculation
        self.eval_grid = self._downsample(self.high_res, target_size=32)

        # 16x16 compact RGB for policy observation
        self.policy_grid = self._downsample(self.high_res, target_size=16)

        # 16x16 Sobel edge map
        self.edge_map = self._compute_edge_map(self.policy_grid)

        # 8-bin color palette distribution
        self.palette = self._compute_palette(self.policy_grid)

    @staticmethod
    def _downsample(img: np.ndarray, target_size: int) -> np.ndarray:
        """Area downsamples square RGB image to target_size x target_size."""
        h, w, c = img.shape
        block = h // target_size
        return img.reshape(target_size, block, target_size, block, c).mean(axis=(1, 3)).astype(np.float32)

    @staticmethod
    def _compute_edge_map(rgb_16: np.ndarray) -> np.ndarray:
        """Computes Sobel magnitude on luminance channel of 16x16 image."""
        # Luminance = 0.299 R + 0.587 G + 0.114 B
        lum = 0.299 * rgb_16[:, :, 0] + 0.587 * rgb_16[:, :, 1] + 0.114 * rgb_16[:, :, 2]
        gx = sobel(lum, axis=1)
        gy = sobel(lum, axis=0)
        mag = np.hypot(gx, gy)
        # Normalize to [0.0, 1.0]
        max_val = float(np.max(mag))
        if max_val > 1e-4:
            mag = mag / max_val
        return mag.astype(np.float32)

    @staticmethod
    def _compute_palette(rgb_16: np.ndarray) -> np.ndarray:
        """
        Quantizes pixels into 8 primary color bins (RGB cube corners)
        and computes histogram distribution (sum = 1.0).
        """
        pixels = rgb_16.reshape(-1, 3)
        # Binary threshold each channel at 0.5
        bin_idx = ((pixels[:, 0] > 0.5).astype(int) << 2) | \
                  ((pixels[:, 1] > 0.5).astype(int) << 1) | \
                  ((pixels[:, 2] > 0.5).astype(int))
        hist, _ = np.histogram(bin_idx, bins=8, range=(0, 8))
        return (hist / max(1, len(pixels))).astype(np.float32)

    def get_task_discrepancy(self, canvas_policy_grid: np.ndarray) -> np.ndarray:
        """
        Returns (Target_16x16 - Canvas_16x16) difference tensor in [-1.0, 1.0].
        Shape: (16, 16, 3)
        """
        return np.clip(self.policy_grid - canvas_policy_grid, -1.0, 1.0).astype(np.float32)

    # Factory methods for procedural benchmark targets
    @classmethod
    def create_solid_square(
        cls,
        color_rgb: Tuple[float, float, float] = (1.0, 0.0, 0.0),
        u0: int = 64,
        v0: int = 64,
        width: int = 128,
        height: int = 128,
        name: str = "solid_square",
    ) -> "PaintingTarget":
        """Creates a canvas with white background and a centered colored rectangle."""
        buf = np.ones((256, 256, 3), dtype=np.float32)
        buf[v0 : v0 + height, u0 : u0 + width, :] = np.array(color_rgb, dtype=np.float32)
        return cls(high_res_rgb=buf, name=name)

    @classmethod
    def create_disc(
        cls,
        color_rgb: Tuple[float, float, float] = (0.1, 0.2, 1.0),
        cx: int = 128,
        cy: int = 128,
        radius: int = 60,
        name: str = "disc",
    ) -> "PaintingTarget":
        """Creates a centered colored disc on white background."""
        buf = np.ones((256, 256, 3), dtype=np.float32)
        y, x = np.ogrid[:256, :256]
        mask = ((x - cx) ** 2 + (y - cy) ** 2) <= (radius ** 2)
        buf[mask] = np.array(color_rgb, dtype=np.float32)
        return cls(high_res_rgb=buf, name=name)

    @classmethod
    def create_two_tone(
        cls,
        color1: Tuple[float, float, float] = (1.0, 0.0, 0.0),
        color2: Tuple[float, float, float] = (0.1, 0.2, 1.0),
        name: str = "two_tone",
    ) -> "PaintingTarget":
        """Creates left half color1, right half color2 patch."""
        buf = np.ones((256, 256, 3), dtype=np.float32)
        buf[64:192, 64:128, :] = np.array(color1, dtype=np.float32)
        buf[64:192, 128:192, :] = np.array(color2, dtype=np.float32)
        return cls(high_res_rgb=buf, name=name)

    @classmethod
    def create_four_color_quadrants(
        cls,
        colors: Optional[List[Tuple[float, float, float]]] = None,
        name: str = "four_color_quadrants",
    ) -> "PaintingTarget":
        """Creates 4-quadrant benchmark target: Red, Green, Blue, Yellow."""
        c = colors or [
            (1.0, 0.0, 0.0),  # Red top-left
            (0.0, 0.9, 0.1),  # Green top-right
            (0.1, 0.2, 1.0),  # Blue bottom-right
            (1.0, 0.9, 0.0),  # Yellow bottom-left
        ]
        buf = np.ones((256, 256, 3), dtype=np.float32)
        buf[64:128, 64:128, :] = np.array(c[0], dtype=np.float32)
        buf[64:128, 128:192, :] = np.array(c[1], dtype=np.float32)
        buf[128:192, 128:192, :] = np.array(c[2], dtype=np.float32)
        buf[128:192, 64:128, :] = np.array(c[3], dtype=np.float32)
        return cls(high_res_rgb=buf, name=name)

    @classmethod
    def create_crossbar(
        cls,
        color_h: Tuple[float, float, float] = (1.0, 0.0, 0.0),
        color_v: Tuple[float, float, float] = (0.1, 0.2, 1.0),
        thickness: int = 32,
        name: str = "crossbar",
    ) -> "PaintingTarget":
        """Creates intersecting horizontal and vertical colored bars."""
        buf = np.ones((256, 256, 3), dtype=np.float32)
        c_mid = 128
        h_half = thickness // 2
        # Horizontal bar
        buf[c_mid - h_half : c_mid + h_half, 48:208, :] = np.array(color_h, dtype=np.float32)
        # Vertical bar
        buf[48:208, c_mid - h_half : c_mid + h_half, :] = np.array(color_v, dtype=np.float32)
        return cls(high_res_rgb=buf, name=name)

    @classmethod
    def create_random_target(cls, rng: Optional[np.random.RandomState] = None, name: str = "random_procedural") -> "PaintingTarget":
        """Generates randomized multi-shape procedural composition."""
        r = rng or np.random.RandomState()
        buf = np.ones((256, 256, 3), dtype=np.float32)
        pot_colors = [
            (1.0, 0.0, 0.0),
            (0.0, 0.9, 0.1),
            (0.1, 0.2, 1.0),
            (1.0, 0.9, 0.0),
        ]
        # Choose 1 to 3 random geometric shapes
        n_shapes = r.randint(1, 4)
        for _ in range(n_shapes):
            col = pot_colors[r.randint(0, len(pot_colors))]
            shape_type = r.choice(["rect", "circle"])
            if shape_type == "rect":
                w = r.randint(30, 90)
                h = r.randint(30, 90)
                x0 = r.randint(40, 256 - 40 - w)
                y0 = r.randint(40, 256 - 40 - h)
                buf[y0 : y0 + h, x0 : x0 + w, :] = np.array(col, dtype=np.float32)
            else:
                rad = r.randint(20, 45)
                cx = r.randint(50 + rad, 256 - 50 - rad)
                cy = r.randint(50 + rad, 256 - 50 - rad)
                y_idx, x_idx = np.ogrid[:256, :256]
                mask = ((x_idx - cx) ** 2 + (y_idx - cy) ** 2) <= (rad ** 2)
                buf[mask] = np.array(col, dtype=np.float32)

        return cls(high_res_rgb=buf, name=name)
