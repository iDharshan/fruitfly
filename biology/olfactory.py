"""
Biological Olfactory Sensory Transduction for Fruitfly V2.
Models multi-channel volatile chemical plumes from paint pots,
Olfactory Receptor Neurons (ORNs), and Antennal Lobe (AL) glomeruli rate coding.
"""

from typing import Tuple, List, Optional
import numpy as np

from painting.paint_pot import PotManager, PaintPot
from toy.circuit import wrap_angle


class OdorReading:
    """
    Lightweight reading for biological PFL3 steering integration.
    """
    def __init__(self, relative_bearing: float, strength: float, pot_id: int):
        self.relative_bearing = float(relative_bearing)
        self.strength = float(np.clip(strength, 0.0, 1.0))
        self.pot_id = int(pot_id)


class OlfactorySystem:
    """
    Multi-channel chemical odor dispersion field and Antennal Lobe model.
    Channels: 0: Red, 1: Green, 2: Blue, 3: Yellow.
    """

    def __init__(
        self,
        pot_manager: PotManager,
        sigma_odor: float = 120.0,
        beta_odor: float = 3.0,
        arena_width: float = 1000.0,
        arena_height: float = 1000.0,
    ):
        self.pot_manager = pot_manager
        self.sigma_odor = float(sigma_odor)
        self.beta_odor = float(beta_odor)
        self.arena_width = float(arena_width)
        self.arena_height = float(arena_height)
        self.two_sigma_sq = 2.0 * (self.sigma_odor ** 2)

    def compute_concentrations(self, world_x: float, world_y: float) -> np.ndarray:
        """
        Computes Gaussian volatile concentration for each pot channel at (world_x, world_y).
        Returns array of shape (K,), values in [0.0, 1.0].
        """
        concentrations = np.zeros(len(self.pot_manager), dtype=np.float32)
        for i, pot in enumerate(self.pot_manager.pots):
            dx = world_x - pot.x
            dy = world_y - pot.y
            dist_sq = dx ** 2 + dy ** 2
            concentrations[i] = np.exp(-dist_sq / self.two_sigma_sq)
        return concentrations

    def compute_al_glomeruli(self, concentrations: np.ndarray) -> np.ndarray:
        """
        Transforms chemical concentrations into Antennal Lobe (AL) projection neuron firing rates:
          r_AL = tanh(beta_odor * C)
        Returns array of shape (K,), values in [0.0, 1.0].
        """
        return np.tanh(self.beta_odor * concentrations).astype(np.float32)

    def compute_gradient(self, pot_id: int, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Computes analytical spatial gradient (dC/dx, dC/dy) for channel pot_id.
        """
        pot = self.pot_manager.get_pot_by_id(pot_id)
        if pot is None:
            return 0.0, 0.0
        dx = pot.x - world_x
        dy = pot.y - world_y
        dist_sq = dx ** 2 + dy ** 2
        c = np.exp(-dist_sq / self.two_sigma_sq)
        grad_x = float((dx / (self.sigma_odor ** 2)) * c)
        grad_y = float((dy / (self.sigma_odor ** 2)) * c)
        return grad_x, grad_y

    def get_odor_reading(
        self,
        world_x: float,
        world_y: float,
        fly_heading: float,
        target_pot_id: int = 0,
    ) -> OdorReading:
        """
        Generates OdorReading targeted at a specific pot channel for PFL3 steering.
        """
        pot = self.pot_manager.get_pot_by_id(target_pot_id)
        if pot is None:
            return OdorReading(0.0, 0.0, target_pot_id)

        # Egocentric bearing to pot
        world_bearing = np.arctan2(pot.y - world_y, pot.x - world_x)
        rel_bearing = float(wrap_angle(world_bearing - fly_heading))

        dx = world_x - pot.x
        dy = world_y - pot.y
        dist_sq = dx ** 2 + dy ** 2
        strength = float(np.exp(-dist_sq / self.two_sigma_sq))

        return OdorReading(
            relative_bearing=rel_bearing,
            strength=strength,
            pot_id=target_pot_id,
        )
