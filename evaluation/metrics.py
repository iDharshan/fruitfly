"""
Scientific Evaluation Metrics for Fruitfly V2.
Computes PSNR, SSIM, L1 error, Bump Coherence, Kinematic Efficiency, and Pigment Economy.
"""

from typing import Tuple, List
import numpy as np
from scipy.ndimage import gaussian_filter


def compute_l1(img1: np.ndarray, img2: np.ndarray) -> float:
    """Mean absolute error between two images in [0, 1]."""
    return float(np.mean(np.abs(img1 - img2)))


def compute_psnr(img1: np.ndarray, img2: np.ndarray) -> float:
    """Peak Signal-to-Noise Ratio (PSNR) in dB."""
    mse = float(np.mean((img1 - img2) ** 2))
    if mse < 1e-10:
        return 100.0
    return float(10.0 * np.log10(1.0 / mse))


def compute_ssim(
    img1: np.ndarray,
    img2: np.ndarray,
    k1: float = 0.01,
    k2: float = 0.03,
    sigma: float = 1.5,
) -> float:
    """
    Computes Structural Similarity Index (SSIM) on luminance channels.
    Range: [-1.0, 1.0], higher is better.
    """
    # Convert to grayscale luminance if RGB
    if img1.ndim == 3 and img1.shape[-1] == 3:
        lum1 = 0.299 * img1[:, :, 0] + 0.587 * img1[:, :, 1] + 0.114 * img1[:, :, 2]
    else:
        lum1 = img1

    if img2.ndim == 3 and img2.shape[-1] == 3:
        lum2 = 0.299 * img2[:, :, 0] + 0.587 * img2[:, :, 1] + 0.114 * img2[:, :, 2]
    else:
        lum2 = img2

    c1 = (k1 * 1.0) ** 2
    c2 = (k2 * 1.0) ** 2

    # Gaussian window smoothing
    mu1 = gaussian_filter(lum1, sigma=sigma)
    mu2 = gaussian_filter(lum2, sigma=sigma)

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = gaussian_filter(lum1 ** 2, sigma=sigma) - mu1_sq
    sigma2_sq = gaussian_filter(lum2 ** 2, sigma=sigma) - mu2_sq
    sigma12 = gaussian_filter(lum1 * lum2, sigma=sigma) - mu1_mu2

    ssim_map = ((2.0 * mu1_mu2 + c1) * (2.0 * sigma12 + c2)) / (
        (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2) + 1e-8
    )

    return float(np.clip(np.mean(ssim_map), -1.0, 1.0))


def compute_kinematic_efficiency(start_pos: Tuple[float, float], end_pos: Tuple[float, float], actual_path_length: float) -> float:
    """
    Computes directness ratio: Euclidean distance / Actual path length.
    Values closer to 1.0 indicate optimal straight flight paths.
    """
    euclidean = float(np.hypot(end_pos[0] - start_pos[0], end_pos[1] - start_pos[1]))
    if actual_path_length < 1e-4:
        return 1.0
    return float(np.clip(euclidean / actual_path_length, 0.0, 1.0))


def compute_pigment_economy(deposited_volume: float, consumed_volume: float) -> float:
    """
    Ratio of pigment deposited on canvas to total pigment drawn from pots.
    1.0 = zero spill or waste.
    """
    if consumed_volume < 1e-4:
        return 1.0
    return float(np.clip(deposited_volume / consumed_volume, 0.0, 1.0))
