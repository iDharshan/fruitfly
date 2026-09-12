"""
Continuous Attractor Neural Network (CANN) Engine.
Models coupled E-PG compass neurons and P-EN angular velocity shifter neurons.
Connectomics-grounded 4-block asymmetric synaptic dynamics with 2.09x feedback ratio.
Features biological divisive normalization in the Ellipsoid Body (EB).
"""

from typing import Tuple, Optional, List, Any
from pathlib import Path
import numpy as np
from .config import CircuitConfig, CIRCUIT_CFG


def wrap_angle(angle: np.ndarray | float) -> np.ndarray | float:
    """Wraps angle to [-pi, pi)."""
    return (np.asarray(angle) + np.pi) % (2.0 * np.pi) - np.pi


def ang_dist(a1: np.ndarray | float, a2: np.ndarray | float) -> np.ndarray | float:
    """Computes signed minimal angular distance (a1 - a2) in [-pi, pi)."""
    return wrap_angle(a1 - a2)


class DualRingAttractor:
    """
    Simulates the Drosophila Central Complex Heading Compass:
      - E-PG: Compass neurons on Ellipsoid Body (EB) azimuth [0, 2pi)
      - P-EN_L: Left Protocerebral Bridge (PB) shifter neurons (-45 deg shift)
      - P-EN_R: Right Protocerebral Bridge (PB) shifter neurons (+45 deg shift)
    """

    def __init__(self, cfg: CircuitConfig = CIRCUIT_CFG):
        self.cfg = cfg
        self.n_epg = cfg.n_epg
        self.n_pen_side = cfg.n_pen_side
        self.n_pen_total = cfg.n_pen_total

        # Preferred azimuthal angles for each neuron population
        self.theta_epg = np.linspace(0.0, 2.0 * np.pi, self.n_epg, endpoint=False)
        self.theta_pen_l = np.linspace(0.0, 2.0 * np.pi, self.n_pen_side, endpoint=False)
        self.theta_pen_r = np.linspace(0.0, 2.0 * np.pi, self.n_pen_side, endpoint=False)

        # Firing rates (r_i >= 0)
        self.r_epg = np.zeros(self.n_epg, dtype=np.float64)
        self.r_pen_l = np.zeros(self.n_pen_side, dtype=np.float64)
        self.r_pen_r = np.zeros(self.n_pen_side, dtype=np.float64)

        # Biological PFL3 Steering Comparator Neurons (12 Left + 12 Right = 24)
        self.n_pfl3 = getattr(cfg, "n_pfl3_total", 24)
        self.n_pfl3_side = getattr(cfg, "n_pfl3_side", 12)
        self.tau_pfl3 = getattr(cfg, "tau_pfl3", 0.025)
        self.r_pfl3 = np.zeros(self.n_pfl3, dtype=np.float64)

        # Fan-Shaped Body (FB) sensory columns for egocentric odor bearing
        self.n_fb_cols = 24
        self.fb_angles = np.linspace(-np.pi, np.pi, self.n_fb_cols, endpoint=False)

        # Divisive normalization parameter
        self.k_div = 0.012

        # Build biological connectome synaptic matrices
        self._build_synaptic_matrices()
        self._load_pfl3_connectome()

        # Initialize bump with seed
        self.reset(initial_heading=0.0)

    def _build_synaptic_matrices(self):
        """
        Constructs biological 4-block matrices:
          1. W_ee: Local recurrent excitation in E-PG
          2. W_ep: Ascending topographic forward projection E-PG -> P-EN
          3. W_pe: Phase-shifted feedback P-EN -> E-PG (ratio 2.09x)
        """
        sigma = self.cfg.sigma_ee
        two_sigma_sq = 2.0 * (sigma ** 2)

        # 1. W_ee: Local Gaussian recurrent excitation in E-PG (48 x 48)
        d_ee = ang_dist(self.theta_epg[:, None], self.theta_epg[None, :])
        self.W_ee = self.cfg.w_ee * np.exp(-(d_ee ** 2) / two_sigma_sq)

        # 2. W_ep: E-PG -> P-EN forward projection (24 x 48)
        d_ep_l = ang_dist(self.theta_pen_l[:, None], self.theta_epg[None, :])
        self.W_ep_l = self.cfg.w_ep * np.exp(-(d_ep_l ** 2) / two_sigma_sq)

        d_ep_r = ang_dist(self.theta_pen_r[:, None], self.theta_epg[None, :])
        self.W_ep_r = self.cfg.w_ep * np.exp(-(d_ep_r ** 2) / two_sigma_sq)

        # 3. W_pe: P-EN -> E-PG phase-shifted feedback (48 x 24)
        # Connectome ratio: 2.09x stronger feedback than forward (21,937 / 10,479 syn)
        w_pe_strength = self.cfg.w_ep * self.cfg.w_pe_ratio
        shift = self.cfg.shift_angle  # pi / 4 = 45 degrees

        # P-EN_L shifts bump Counter-Clockwise (-45 deg)
        target_l = wrap_angle(self.theta_pen_l[None, :] - shift)
        d_pe_l = ang_dist(self.theta_epg[:, None], target_l)
        self.W_pe_l = w_pe_strength * np.exp(-(d_pe_l ** 2) / two_sigma_sq)

        # P-EN_R shifts bump Clockwise (+45 deg)
        target_r = wrap_angle(self.theta_pen_r[None, :] + shift)
        d_pe_r = ang_dist(self.theta_epg[:, None], target_r)
        self.W_pe_r = w_pe_strength * np.exp(-(d_pe_r ** 2) / two_sigma_sq)

    def _load_pfl3_connectome(self):
        """Loads biological W_ep_pfl3 and W_fb_pfl3 matrices, or builds fallback."""
        data_path = Path(__file__).resolve().parent.parent / "data" / "pfl3_circuit.npz"
        if data_path.exists():
            try:
                data = np.load(data_path)
                w_ep = data["W_ep_pfl3"]
                w_fb = data["W_fb_pfl3"]
                # Normalize Left and Right blocks to maintain symmetric baseline balance
                sum_l = np.sum(w_ep[:self.n_pfl3_side, :])
                sum_r = np.sum(w_ep[self.n_pfl3_side:, :])
                mean_sum = 0.5 * (sum_l + sum_r)
                w_ep_norm = w_ep.copy()
                if sum_l > 0:
                    w_ep_norm[:self.n_pfl3_side, :] *= (mean_sum / sum_l)
                if sum_r > 0:
                    w_ep_norm[self.n_pfl3_side:, :] *= (mean_sum / sum_r)

                self.W_ep_pfl3 = w_ep_norm
                self.W_fb_pfl3 = w_fb
                return
            except Exception:
                pass

        # Fallback synthetic biological comparator matrices
        n_p = self.n_pfl3
        self.W_ep_pfl3 = np.zeros((n_p, self.n_epg), dtype=np.float64)
        for i in range(self.n_pfl3_side):
            th_l = (i + 0.5) * (2.0 * np.pi / self.n_pfl3_side)
            d_l = ang_dist(self.theta_epg, th_l)
            self.W_ep_pfl3[i, :] = np.exp(-(d_l ** 2) / (2.0 * (0.5 ** 2))) * 15.0

            th_r = (i + 0.5) * (2.0 * np.pi / self.n_pfl3_side)
            d_r = ang_dist(self.theta_epg, th_r)
            self.W_ep_pfl3[self.n_pfl3_side + i, :] = np.exp(-(d_r ** 2) / (2.0 * (0.5 ** 2))) * 15.0

        self.W_fb_pfl3 = np.zeros((n_p, self.n_fb_cols), dtype=np.float64)
        for i in range(self.n_pfl3_side):
            # Left prefers -90 deg
            d_fb_l = ang_dist(self.fb_angles, -np.pi / 2.0)
            self.W_fb_pfl3[i, :] = (np.maximum(0.0, np.cos(d_fb_l)) ** 2) * 2.5
            # Right prefers +90 deg
            d_fb_r = ang_dist(self.fb_angles, np.pi / 2.0)
            self.W_fb_pfl3[self.n_pfl3_side + i, :] = (np.maximum(0.0, np.cos(d_fb_r)) ** 2) * 2.5

    def reset(self, initial_heading: float = 0.0):
        """Initializes the ring attractor with a cosine bump at initial_heading."""
        d = ang_dist(self.theta_epg, initial_heading)
        self.r_epg = np.maximum(0.0, np.cos(d)) * 2.0
        self.r_pen_l = np.zeros(self.n_pen_side, dtype=np.float64)
        self.r_pen_r = np.zeros(self.n_pen_side, dtype=np.float64)
        self.r_pfl3 = np.zeros(self.n_pfl3, dtype=np.float64)

    def step(
        self,
        dt: float,
        omega: float = 0.0,
        landmark_azimuth: Optional[float] = None,
        landmark_bearing: Optional[float] = None,
        landmark_active: bool = False,
    ):
        """
        Integrates continuous attractor dynamics with divisive normalization:
          dr_i / dt = (-r_i + phi(u_i)) / tau
        """
        h_current, _, _ = self.decode_heading()

        # Support either landmark_azimuth or landmark_bearing
        cue_angle = landmark_azimuth if landmark_azimuth is not None else landmark_bearing

        # Motor steering inputs (from user keyboard commands)
        g_l = self.cfg.k_turn_drive * max(0.0, -omega)
        g_r = self.cfg.k_turn_drive * max(0.0, omega)

        # Visual landmark sensory current in E-PG compass wedges
        u_vis_e = np.zeros(self.n_epg, dtype=np.float64)
        if landmark_active and cue_angle is not None:
            # Error between landmark world angle and current decoded heading
            err_cue = float(ang_dist(cue_angle, h_current))
            # Align bump to landmark world azimuth smoothly
            omega_cue = 3.5 * np.clip(err_cue, -3.0, 3.0)
            g_l += max(0.0, -omega_cue)
            g_r += max(0.0, omega_cue)

            # Receptive field cosine profile on E-PG matching landmark allocentric azimuth
            d_vis = ang_dist(self.theta_epg, cue_angle)
            u_vis_e = self.cfg.g_visual_gain * (np.maximum(0.0, np.cos(d_vis)) ** 2)

        # P-EN forward projection driven by E-PG and modulated by motor velocity
        u_pen_l = (self.W_ep_l @ self.r_epg) * (0.05 + 0.25 * g_l)
        u_pen_r = (self.W_ep_r @ self.r_epg) * (0.05 + 0.25 * g_r)

        dr_pen_l = (-self.r_pen_l + u_pen_l) / self.cfg.tau_m
        dr_pen_r = (-self.r_pen_r + u_pen_r) / self.cfg.tau_m
        self.r_pen_l = np.maximum(0.0, self.r_pen_l + dt * dr_pen_l)
        self.r_pen_r = np.maximum(0.0, self.r_pen_r + dt * dr_pen_r)

        # E-PG recurrent drive + phase-shifted feedback + visual sensory anchor
        u_e = (
            self.W_ee @ self.r_epg
            + 0.30 * (self.W_pe_l @ self.r_pen_l + self.W_pe_r @ self.r_pen_r)
            + u_vis_e
        )

        # Stochastic thermal fluctuation
        if self.cfg.noise_sigma > 0:
            u_e += np.random.normal(0.0, self.cfg.noise_sigma, size=self.n_epg)

        # Divisive normalization in EB: phi(u) = u^2 / (1 + k_div * sum(u^2))
        pos_u = np.maximum(0.0, u_e)
        sum_sq = np.sum(pos_u ** 2)
        phi_e = (pos_u ** 2) / (1.0 + self.k_div * sum_sq)

        dr_epg = (-self.r_epg + phi_e) / self.cfg.tau_m
        self.r_epg = np.maximum(0.0, self.r_epg + dt * dr_epg)

    def step_frame(
        self,
        dt_frame: float,
        omega: float = 0.0,
        landmark_azimuth: Optional[float] = None,
        landmark_bearing: Optional[float] = None,
        landmark_active: bool = False,
    ):
        """Performs multiple high-precision ODE substeps for a single display frame."""
        substeps = self.cfg.substeps_per_frame
        dt_sub = dt_frame / substeps
        for _ in range(substeps):
            self.step(
                dt=dt_sub,
                omega=omega,
                landmark_azimuth=landmark_azimuth,
                landmark_bearing=landmark_bearing,
                landmark_active=landmark_active,
            )

    def decode_heading(self) -> Tuple[float, float, float]:
        """
        Population Vector Readout:
          X = sum(r_i * cos(theta_i))
          Y = sum(r_i * sin(theta_i))
          theta_hat = atan2(Y, X)
        Returns:
          (decoded_angle_rad, amplitude, coherence)
        """
        x = float(np.sum(self.r_epg * np.cos(self.theta_epg)))
        y = float(np.sum(self.r_epg * np.sin(self.theta_epg)))
        amplitude = float(np.hypot(x, y))
        total_rate = float(np.sum(self.r_epg)) + 1e-8
        coherence = min(1.0, amplitude / (total_rate + 1e-6))
        heading_angle = float(np.arctan2(y, x))
        return heading_angle, amplitude, coherence

    def get_shifter_activities(self) -> Tuple[float, float]:
        """Returns average firing activity of Left and Right P-EN populations."""
        mean_l = float(np.mean(self.r_pen_l))
        mean_r = float(np.mean(self.r_pen_r))
        return mean_l, mean_r

    def get_active_synaptic_arcs(self, threshold_ratio: float = 0.35) -> List[Tuple[str, int, float, int, float, float]]:
        """
        Returns active P-EN -> E-PG synaptic transmission pairs for visual bloom rendering.
        Yields tuples: (pen_type, pen_idx, pen_angle, epg_idx, epg_angle, normalized_intensity)
        """
        arcs = []
        max_pen_l = float(np.max(self.r_pen_l)) if len(self.r_pen_l) else 0.0
        max_pen_r = float(np.max(self.r_pen_r)) if len(self.r_pen_r) else 0.0

        if max_pen_l > 0.5:
            thresh_l = max_pen_l * threshold_ratio
            active_indices = np.where(self.r_pen_l > thresh_l)[0]
            for idx in active_indices:
                rate = float(self.r_pen_l[idx])
                target_epg = int(np.argmax(self.W_pe_l[:, idx]))
                intensity = min(1.0, rate / (max_pen_l + 1e-6))
                arcs.append((
                    "LEFT",
                    idx,
                    float(self.theta_pen_l[idx]),
                    target_epg,
                    float(self.theta_epg[target_epg]),
                    intensity,
                ))

        if max_pen_r > 0.5:
            thresh_r = max_pen_r * threshold_ratio
            active_indices = np.where(self.r_pen_r > thresh_r)[0]
            for idx in active_indices:
                rate = float(self.r_pen_r[idx])
                target_epg = int(np.argmax(self.W_pe_r[:, idx]))
                intensity = min(1.0, rate / (max_pen_r + 1e-6))
                arcs.append((
                    "RIGHT",
                    idx,
                    float(self.theta_pen_r[idx]),
                    target_epg,
                    float(self.theta_epg[target_epg]),
                    intensity,
                ))

        return arcs

    def step_pfl3(
        self,
        odor_reading: Any = None,
        dt: float = 0.016,
        v_base: float = 150.0,
    ) -> Tuple[float, float, float, float]:
        """
        Integrates biological PFL3 decision neurons via leaky integrator dynamics:
          tau_PFL3 * dr_PFL3 / dt = -r_PFL3 + phi(W_EP-PFL3 @ r_EPG * 0.01 + W_FB-PFL3 @ u_odor * 0.8)
        Computes push-pull steering drive:
          omega_auto = k_drive * (sum(r_PFL3_R) - sum(r_PFL3_L))
        Computes forward speed drive:
          v_auto = v_base * (0.6 + 0.4 cos(Psi)) * (0.4 + 0.6 * strength)
        Returns:
          (omega_auto, target_v, pfl3_left_mean, pfl3_right_mean)
        """
        # Extract odor bearing and strength
        if odor_reading is not None:
            psi = getattr(odor_reading, "relative_bearing", 0.0)
            strength = getattr(odor_reading, "strength", 0.0)
        else:
            psi = 0.0
            strength = 0.0

        # Model Odor Sensory Input array across 24 Fan-Shaped Body (FB) columns
        d = ang_dist(self.fb_angles, psi)
        u_odor = strength * (np.maximum(0.0, np.cos(d)) ** 2)

        # Coincidence drive: compass heading (E-PG) + egocentric odor sensory goal (FB)
        epg_drive = (self.W_ep_pfl3 @ self.r_epg) * 0.01
        fb_drive = (self.W_fb_pfl3 @ u_odor) * 0.8
        drive = epg_drive + fb_drive

        # Leaky integrator dynamics: dr/dt = (-r + phi(drive)) / tau
        phi = np.maximum(0.0, drive)
        dr_pfl3 = (-self.r_pfl3 + phi) / self.tau_pfl3
        self.r_pfl3 = np.maximum(0.0, self.r_pfl3 + dt * dr_pfl3)

        # Differential steering command
        r_l = self.r_pfl3[:self.n_pfl3_side]
        r_r = self.r_pfl3[self.n_pfl3_side:]

        # Push-pull comparator: Right - Left
        # When odor is left (psi < 0), Left PFL3 dominates -> omega_auto < 0 (left turn)
        # When odor is right (psi > 0), Right PFL3 dominates -> omega_auto > 0 (right turn)
        diff = (np.sum(r_r) - np.sum(r_l)) / float(self.n_pfl3)
        k_drive = getattr(self.cfg, "k_pfl3_drive", 2.8)
        omega_auto = float(np.clip((k_drive * diff) / 4.5, -k_drive, k_drive))

        # Forward speed modulation: slows down on sharp turns, accelerates on target lock
        cos_psi = float(np.cos(psi))
        target_v = float(v_base * (0.6 + 0.4 * cos_psi) * (0.4 + 0.6 * strength))

        mean_l = float(np.mean(r_l))
        mean_r = float(np.mean(r_r))
        return omega_auto, target_v, mean_l, mean_r

    def get_pfl3_activities(self) -> Tuple[float, float]:
        """Returns average firing rates of Left and Right PFL3 populations."""
        mean_l = float(np.mean(self.r_pfl3[:self.n_pfl3_side]))
        mean_r = float(np.mean(self.r_pfl3[self.n_pfl3_side:]))
        return mean_l, mean_r

    def get_pfl3_directional_bias(self) -> float:
        """
        Returns normalized steering bias between [-1.0, 1.0].
        -1.0 = Max left turn bias, +1.0 = Max right turn bias.
        """
        r_l = float(np.sum(self.r_pfl3[:self.n_pfl3_side]))
        r_r = float(np.sum(self.r_pfl3[self.n_pfl3_side:]))
        tot = r_l + r_r
        if tot < 1e-4:
            return 0.0
        return float(np.clip((r_r - r_l) / tot, -1.0, 1.0))

