"""
Frozen Continuous Attractor Neural Network (CANN) Engine.
Encapsulates E-PG / P-EN / PFL3 dynamics with cryptographic immutability guarantees.
Biological weights cannot be mutated or updated by RL gradient descent.
"""

import hashlib
from typing import Optional, Tuple
import numpy as np

from .interfaces import CompassState, BiologyConfig
from toy.circuit import DualRingAttractor, ang_dist, wrap_angle
from toy.config import CircuitConfig


class FrozenDualRingAttractor:
    """
    Biological Central Complex compass and steering comparator.
    Guarantees frozen weights with SHA-256 verification and immutable state readouts.
    """

    def __init__(self, cfg: Optional[BiologyConfig] = None, scramble_weights: bool = False, scramble_seed: int = 42):
        self.bio_cfg = cfg or BiologyConfig()

        # Build circuit config matching biological parameters
        circuit_cfg = CircuitConfig(
            n_epg=self.bio_cfg.n_epg,
            n_pen_side=self.bio_cfg.n_pen_side,
            tau_m=self.bio_cfg.tau_m,
            tau_pfl3=self.bio_cfg.tau_pfl3,
            w_ee=self.bio_cfg.w_ee,
            w_ep=self.bio_cfg.w_ep,
            w_pe_ratio=self.bio_cfg.w_pe_ratio,
            sigma_ee=self.bio_cfg.sigma_ee,
            shift_angle=self.bio_cfg.shift_angle,
            noise_sigma=self.bio_cfg.noise_sigma,
            k_turn_drive=self.bio_cfg.k_turn_drive,
            k_pfl3_drive=self.bio_cfg.k_pfl3_drive,
            substeps_per_frame=self.bio_cfg.substeps_per_frame,
        )

        self._circuit = DualRingAttractor(circuit_cfg)

        if scramble_weights:
            # Condition D: Scrambled CANN Control
            rng = np.random.RandomState(scramble_seed)
            shuff_ee = rng.permutation(self._circuit.W_ee.shape[0])
            self._circuit.W_ee = self._circuit.W_ee[shuff_ee, :][:, shuff_ee]
            shuff_pe_l = rng.permutation(self._circuit.W_pe_l.shape[0])
            self._circuit.W_pe_l = self._circuit.W_pe_l[shuff_pe_l, :]
            shuff_pe_r = rng.permutation(self._circuit.W_pe_r.shape[0])
            self._circuit.W_pe_r = self._circuit.W_pe_r[shuff_pe_r, :]

        # Mark synaptic matrices as read-only numpy arrays
        self._circuit.W_ee.flags.writeable = False
        self._circuit.W_ep_l.flags.writeable = False
        self._circuit.W_ep_r.flags.writeable = False
        self._circuit.W_pe_l.flags.writeable = False
        self._circuit.W_pe_r.flags.writeable = False
        if hasattr(self._circuit, "W_ep_pfl3"):
            self._circuit.W_ep_pfl3.flags.writeable = False
        if hasattr(self._circuit, "W_fb_pfl3"):
            self._circuit.W_fb_pfl3.flags.writeable = False

        # Record cryptographic fingerprint of all synaptic weights
        self._weight_fingerprint = self._compute_fingerprint()

    def _compute_fingerprint(self) -> str:
        """Computes SHA-256 hash across all biological synaptic matrices."""
        hasher = hashlib.sha256()
        hasher.update(self._circuit.W_ee.tobytes())
        hasher.update(self._circuit.W_ep_l.tobytes())
        hasher.update(self._circuit.W_ep_r.tobytes())
        hasher.update(self._circuit.W_pe_l.tobytes())
        hasher.update(self._circuit.W_pe_r.tobytes())
        if hasattr(self._circuit, "W_ep_pfl3"):
            hasher.update(self._circuit.W_ep_pfl3.tobytes())
        if hasattr(self._circuit, "W_fb_pfl3"):
            hasher.update(self._circuit.W_fb_pfl3.tobytes())
        return hasher.hexdigest()

    def verify_immutability(self) -> bool:
        """Verifies that no synaptic weights have been mutated."""
        return self._compute_fingerprint() == self._weight_fingerprint

    @property
    def fingerprint(self) -> str:
        return self._weight_fingerprint

    def reset(self, initial_heading: float = 0.0):
        """Initializes the compass bump at initial_heading."""
        self._circuit.reset(initial_heading=initial_heading)

    def step(
        self,
        dt: float,
        omega: float = 0.0,
        landmark_azimuth: Optional[float] = None,
        landmark_bearing: Optional[float] = None,
        landmark_active: bool = False,
    ):
        """Integrates ODE dynamics over dt seconds."""
        self._circuit.step(
            dt=dt,
            omega=omega,
            landmark_azimuth=landmark_azimuth,
            landmark_bearing=landmark_bearing,
            landmark_active=landmark_active,
        )

    def step_frame(
        self,
        dt_frame: float,
        omega: float = 0.0,
        landmark_azimuth: Optional[float] = None,
        landmark_bearing: Optional[float] = None,
        landmark_active: bool = False,
    ):
        """Integrates multiple sub-steps for a simulation step."""
        self._circuit.step_frame(
            dt_frame=dt_frame,
            omega=omega,
            landmark_azimuth=landmark_azimuth,
            landmark_bearing=landmark_bearing,
            landmark_active=landmark_active,
        )

    def step_pfl3(
        self,
        odor_reading: any = None,
        dt: float = 0.016,
        v_base: Optional[float] = None,
    ) -> Tuple[float, float, float, float]:
        """Runs the biological PFL3 steering comparator."""
        if v_base is None:
            v_base = self.bio_cfg.v_cruise
        return self._circuit.step_pfl3(odor_reading=odor_reading, dt=dt, v_base=v_base)

    def decode_heading(self) -> Tuple[float, float, float]:
        """Returns (heading_angle, amplitude, coherence)."""
        return self._circuit.decode_heading()

    def get_state(self) -> CompassState:
        """
        Emits an immutable snapshot of the biological compass state.
        """
        heading, amplitude, coherence = self._circuit.decode_heading()
        mean_l, mean_r = self._circuit.get_shifter_activities()
        torque = float(np.clip((mean_r - mean_l) / (mean_r + mean_l + 1e-6), -1.0, 1.0))
        pfl3_bias = self._circuit.get_pfl3_directional_bias()

        # Normalized E-PG activity buffer (read-only copy)
        epg_max = float(np.max(self._circuit.r_epg)) if len(self._circuit.r_epg) else 1.0
        denom = max(1e-4, epg_max)
        epg_norm = (self._circuit.r_epg / denom).astype(np.float32)
        epg_norm.flags.writeable = False

        return CompassState(
            heading=heading,
            sin_heading=float(np.sin(heading)),
            cos_heading=float(np.cos(heading)),
            coherence=coherence,
            amplitude=amplitude,
            torque=torque,
            epg_activity=epg_norm,
            pen_left_mean=mean_l,
            pen_right_mean=mean_r,
            pfl3_bias=pfl3_bias,
        )
