"""
Biological Visual Sensory Processing for Fruitfly V2.
Encodes egocentric visual bearings, retinotopic visual projection neurons (VPNs),
and packages complete SensoryState snapshots.
"""

from typing import Tuple, List, Optional
import numpy as np

from .interfaces import SensoryState, BiologyConfig
from .olfactory import OlfactorySystem
from painting.canvas import Canvas
from painting.paint_pot import PotManager
from toy.circuit import wrap_angle, ang_dist


class VisualSystem:
    """
    Simulates fly compound eye receptive fields and egocentric visual bearings.
    """

    def __init__(
        self,
        canvas: Canvas,
        pot_manager: PotManager,
        olfactory: OlfactorySystem,
        cfg: Optional[BiologyConfig] = None,
    ):
        self.canvas = canvas
        self.pot_manager = pot_manager
        self.olfactory = olfactory
        self.cfg = cfg or BiologyConfig()
        self.max_dist = float(np.hypot(self.cfg.arena_width, self.cfg.arena_height))

        # 16 Retinotopic Visual Projection Neuron sectors covering [-pi, pi)
        self.n_vpn = 16
        self.vpn_angles = np.linspace(-np.pi, np.pi, self.n_vpn, endpoint=False)

    def compute_sensory_state(
        self,
        fly_x: float,
        fly_y: float,
        fly_heading: float,
        fly_altitude: float,
    ) -> SensoryState:
        """
        Builds the complete immutable SensoryState snapshot.
        """
        # 1. Olfactory transduction
        concentrations = self.olfactory.compute_concentrations(fly_x, fly_y)
        al_glomeruli = self.olfactory.compute_al_glomeruli(concentrations)

        # 2. Canvas visual bearings and distance
        canvas_world_bearing = np.arctan2(self.canvas.center_y - fly_y, self.canvas.center_x - fly_x)
        canvas_bearing = float(wrap_angle(canvas_world_bearing - fly_heading))
        canvas_dist = float(np.hypot(self.canvas.center_x - fly_x, self.canvas.center_y - fly_y))
        canvas_dist_norm = float(np.clip(canvas_dist / (self.max_dist * 0.5), 0.0, 1.0))

        # 3. Pot visual bearings and distances
        pot_bearings = np.zeros(len(self.pot_manager), dtype=np.float32)
        pot_dists = np.zeros(len(self.pot_manager), dtype=np.float32)

        for i, pot in enumerate(self.pot_manager.pots):
            b_world = np.arctan2(pot.y - fly_y, pot.x - fly_x)
            pot_bearings[i] = float(wrap_angle(b_world - fly_heading))
            d = float(np.hypot(pot.x - fly_x, pot.y - fly_y))
            pot_dists[i] = float(np.clip(d / (self.max_dist * 0.5), 0.0, 1.0))

        min_pot_dist = float(np.min(pot_dists)) if len(pot_dists) else 1.0
        altitude_norm = float(np.clip(fly_altitude / self.cfg.z_max, 0.0, 1.0))

        # Mark arrays read-only
        concentrations.flags.writeable = False
        al_glomeruli.flags.writeable = False
        pot_bearings.flags.writeable = False
        pot_dists.flags.writeable = False

        return SensoryState(
            odor_concentrations=concentrations,
            al_glomeruli=al_glomeruli,
            canvas_bearing=canvas_bearing,
            canvas_dist_norm=canvas_dist_norm,
            pot_bearings=pot_bearings,
            pot_distances_norm=pot_dists,
            min_pot_dist=min_pot_dist,
            altitude_norm=altitude_norm,
        )

    def compute_retinotopic_receptive_fields(
        self,
        fly_x: float,
        fly_y: float,
        fly_heading: float,
    ) -> np.ndarray:
        """
        Computes 16-channel retinotopic visual projection neuron (VPN) activation profile.
        Activates visual wedges corresponding to the direction of canvas and pots.
        """
        vpn = np.zeros(self.n_vpn, dtype=np.float32)
        # Visual landmark 1: Canvas center
        cw_bearing = np.arctan2(self.canvas.center_y - fly_y, self.canvas.center_x - fly_x)
        c_rel = float(wrap_angle(cw_bearing - fly_heading))
        d_c = ang_dist(self.vpn_angles, c_rel)
        vpn += np.maximum(0.0, np.cos(d_c)) ** 2 * 0.7

        # Visual landmarks: pots
        for pot in self.pot_manager.pots:
            pw_bearing = np.arctan2(pot.y - fly_y, pot.x - fly_x)
            p_rel = float(wrap_angle(pw_bearing - fly_heading))
            d_p = ang_dist(self.vpn_angles, p_rel)
            vpn += np.maximum(0.0, np.cos(d_p)) ** 2 * 0.3

        return np.clip(vpn, 0.0, 1.0).astype(np.float32)
