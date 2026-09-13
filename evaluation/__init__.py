"""
Scientific Evaluation, Ablation Benchmark, and Publication Plotting Module for Fruitfly V2.
"""

from .metrics import (
    compute_l1,
    compute_psnr,
    compute_ssim,
    compute_kinematic_efficiency,
    compute_pigment_economy,
)

__all__ = [
    "compute_l1",
    "compute_psnr",
    "compute_ssim",
    "compute_kinematic_efficiency",
    "compute_pigment_economy",
]
