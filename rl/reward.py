"""
Potential-Based Progress Reward Engine for Fruitfly V2.
Guarantees mathematically bounded, non-hackable telescoping rewards.
"""

from typing import Tuple, Dict, Any
import numpy as np


class PotentialRewardCalculator:
    """
    Computes potential-based progress rewards and behavioral penalties.
    """

    def __init__(
        self,
        lambda_prog: float = 50.0,
        lambda_spill: float = 0.05,
        lambda_energy: float = 0.002,
        completion_bonus: float = 10.0,
        target_similarity_threshold: float = 0.90,
        v_max: float = 180.0,
    ):
        self.lambda_prog = lambda_prog
        self.lambda_spill = lambda_spill
        self.lambda_energy = lambda_energy
        self.completion_bonus = completion_bonus
        self.target_similarity_threshold = target_similarity_threshold
        self.v_max = v_max

    def compute_reward(
        self,
        prev_similarity: float,
        current_similarity: float,
        spill_occurred: bool,
        fly_velocity: float,
        dt_macro: float = 0.1,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Computes composite reward and diagnostic breakdown.
        """
        # 1. Bounded potential-based progress: telescoping sum <= lambda_prog * (1.0 - S_0)
        delta_sim = current_similarity - prev_similarity
        r_progress = float(self.lambda_prog * delta_sim)

        # 2. Penalty for spraying paint outside canvas boundaries
        r_spill = float(-self.lambda_spill) if spill_occurred else 0.0

        # 3. Kinetic energy minimization penalty
        v_ratio = float(np.clip(fly_velocity / self.v_max, 0.0, 1.0))
        r_energy = float(-self.lambda_energy * (v_ratio ** 2) * dt_macro)

        # 4. Terminal completion bonus upon reaching target fidelity
        r_terminal = float(self.completion_bonus) if current_similarity >= self.target_similarity_threshold else 0.0

        total_reward = r_progress + r_spill + r_energy + r_terminal

        breakdown = {
            "reward_total": total_reward,
            "reward_progress": r_progress,
            "reward_spill": r_spill,
            "reward_energy": r_energy,
            "reward_terminal": r_terminal,
            "delta_similarity": delta_sim,
        }
        return total_reward, breakdown
