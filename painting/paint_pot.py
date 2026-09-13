"""
Paint Pots and Multi-Channel Odor Sources for Fruitfly V2.
Models discrete color reservoirs with physical reload zones.
"""

from typing import List, Optional, Tuple
import numpy as np


class PaintPot:
    """
    Individual paint pot serving as physical paint source and volatile chemical plume origin.
    """

    def __init__(
        self,
        pot_id: int,
        name: str,
        color_rgb: Tuple[float, float, float],
        x: float,
        y: float,
        radius: float = 40.0,
    ):
        self.pot_id = pot_id
        self.name = name
        self.color_rgb = np.array(color_rgb, dtype=np.float32)
        self.x = float(x)
        self.y = float(y)
        self.radius = float(radius)

    def contains(self, world_x: float, world_y: float) -> bool:
        """Returns True if world coordinate is within the reload basin."""
        dx = world_x - self.x
        dy = world_y - self.y
        return (dx ** 2 + dy ** 2) <= (self.radius ** 2)

    def distance_to(self, world_x: float, world_y: float) -> float:
        """Euclidean distance to pot center."""
        return float(np.hypot(world_x - self.x, world_y - self.y))


class PotManager:
    """
    Manages the 4 canonical paint pots: Red, Green, Blue, Yellow.
    """

    CANONICAL_POTS = [
        (0, "Red", (1.0, 0.0, 0.0), 150.0, 150.0),
        (1, "Green", (0.0, 0.9, 0.1), 850.0, 150.0),
        (2, "Blue", (0.1, 0.2, 1.0), 850.0, 850.0),
        (3, "Yellow", (1.0, 0.9, 0.0), 150.0, 850.0),
    ]

    def __init__(self, pots_config: Optional[List[Tuple[int, str, Tuple[float, float, float], float, float]]] = None):
        configs = pots_config or self.CANONICAL_POTS
        self.pots: List[PaintPot] = [
            PaintPot(pot_id=pid, name=name, color_rgb=rgb, x=x, y=y)
            for pid, name, rgb, x, y in configs
        ]

    def __len__(self) -> int:
        return len(self.pots)

    def __getitem__(self, idx: int) -> PaintPot:
        return self.pots[idx]

    def get_pot_by_id(self, pot_id: int) -> Optional[PaintPot]:
        for pot in self.pots:
            if pot.pot_id == pot_id:
                return pot
        return None

    def check_reload(
        self,
        world_x: float,
        world_y: float,
        altitude: float,
        z_contact: float = 2.5,
    ) -> Optional[PaintPot]:
        """
        Returns the PaintPot if the fly has descended to ground contact within the pot basin.
        """
        if altitude > z_contact:
            return None
        for pot in self.pots:
            if pot.contains(world_x, world_y):
                return pot
        return None

    def get_positions(self) -> np.ndarray:
        """Returns (K, 2) positions array."""
        return np.array([[p.x, p.y] for p in self.pots], dtype=np.float32)

    def get_colors(self) -> np.ndarray:
        """Returns (K, 3) RGB array."""
        return np.array([p.color_rgb for p in self.pots], dtype=np.float32)
