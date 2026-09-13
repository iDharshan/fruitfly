"""
Publication-Quality Scientific Plotting for Fruitfly V2 Ablation Benchmarks.
Generates comparative bar charts, learning curves, and bump coherence figures.
"""

import sys
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt


def plot_ablation_comparison(
    results: List[Dict[str, Any]],
    output_path: str = "docs/figures/ablation_benchmark.png",
):
    """
    Renders 4-panel publication figure summarizing experimental conditions A-E.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    labels = [r["condition"].replace("Condition ", "") for r in results]
    ssims = [r["ssim"] for r in results]
    psnrs = [r["psnr"] for r in results]
    coherences = [r["bump_coherence"] for r in results]
    economies = [r["economy"] * 100.0 for r in results]

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle("Fruitfly V2: Biological Inductive Bias & Ablation Study", fontsize=15, fontweight="bold")

    colors = ["#2ecc71", "#3498db", "#9b59b6", "#e74c3c", "#f39c12"]

    # 1. SSIM
    ax1 = axes[0, 0]
    bars1 = ax1.bar(labels, ssims, color=colors[:len(labels)], width=0.55, edgecolor="black", linewidth=1)
    ax1.set_title("Structural Similarity Index (SSIM)", fontsize=12, fontweight="bold")
    ax1.set_ylabel("SSIM", fontsize=11)
    ax1.set_ylim([0.0, 1.05])
    for bar in bars1:
        y = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, y + 0.02, f"{y:.3f}", ha="center", va="bottom", fontsize=10)

    # 2. PSNR (dB)
    ax2 = axes[0, 1]
    bars2 = ax2.bar(labels, psnrs, color=colors[:len(labels)], width=0.55, edgecolor="black", linewidth=1)
    ax2.set_title("Peak Signal-to-Noise Ratio (PSNR)", fontsize=12, fontweight="bold")
    ax2.set_ylabel("dB", fontsize=11)
    for bar in bars2:
        y = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2.0, y + 0.3, f"{y:.1f}", ha="center", va="bottom", fontsize=10)

    # 3. Compass Bump Coherence
    ax3 = axes[1, 0]
    bars3 = ax3.bar(labels, coherences, color=colors[:len(labels)], width=0.55, edgecolor="black", linewidth=1)
    ax3.set_title("Mean E-PG Bump Coherence", fontsize=12, fontweight="bold")
    ax3.set_ylabel("Coherence [0, 1]", fontsize=11)
    ax3.set_ylim([0.0, 1.1])
    for bar in bars3:
        y = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width() / 2.0, y + 0.02, f"{y:.2f}", ha="center", va="bottom", fontsize=10)

    # 4. Pigment Economy (%)
    ax4 = axes[1, 1]
    bars4 = ax4.bar(labels, economies, color=colors[:len(labels)], width=0.55, edgecolor="black", linewidth=1)
    ax4.set_title("Pigment Deposition Economy", fontsize=12, fontweight="bold")
    ax4.set_ylabel("Deposited / Consumed (%)", fontsize=11)
    ax4.set_ylim([0.0, 105.0])
    for bar in bars4:
        y = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width() / 2.0, y + 1.5, f"{y:.1f}%", ha="center", va="bottom", fontsize=10)

    for ax in axes.flat:
        ax.tick_params(axis="x", rotation=18)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"Figure successfully saved to {output_path}!")


if __name__ == "__main__":
    from evaluation.ablations import run_full_ablation_suite
    results = run_full_ablation_suite()
    plot_ablation_comparison(results)
