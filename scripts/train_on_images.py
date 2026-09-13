"""
Batch Training Runner for Custom Images in data/
Automatically discovers all images in data/, trains PPO agent with CUDA GPU,
evaluates painting fidelity, saves models, and generates comparative visual diffs.
"""

import sys
import os
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rl.env import FruitFlyPaintEnv
from rl.policy import FruitFlyFeaturesExtractor
from rl.evaluate import evaluate_policy
from painting.target import PaintingTarget
from evaluation.metrics import compute_ssim, compute_psnr, compute_l1, compute_pigment_economy

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv


def train_single_image(
    image_path: Path,
    timesteps: int = 10000,
    device: str = "cuda",
    seed: int = 42,
    results_dir: Path = Path("data/results"),
    models_dir: Path = Path("models"),
) -> dict:
    """Trains PPO agent on a single custom image target and outputs results."""
    print(f"\n========================================================")
    print(f"🎨 Processing Custom Target: {image_path.name}")
    print(f"========================================================")

    results_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    target = PaintingTarget.from_image(image_path)

    def env_fn():
        return FruitFlyPaintEnv(target=target, max_episode_steps=800, substeps=8)

    vec_env = DummyVecEnv([env_fn])

    policy_kwargs = dict(
        features_extractor_class=FruitFlyFeaturesExtractor,
        features_extractor_kwargs=dict(features_dim=176),
        net_arch=dict(pi=[256, 256], vf=[256, 256]),
    )

    model = PPO(
        "MultiInputPolicy",
        vec_env,
        policy_kwargs=policy_kwargs,
        learning_rate=3e-4,
        n_steps=256,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=1,
        device=device,
        seed=seed,
    )

    print(f"Training PPO on {device.upper()} for {timesteps} steps...")
    model.learn(total_timesteps=timesteps)

    stem_clean = image_path.stem.replace(" ", "_").lower()

    # Save model
    model_save_path = models_dir / f"fruitfly_ppo_{stem_clean}.zip"
    model.save(model_save_path)
    print(f"Model saved to {model_save_path}")

    # Evaluate trained policy
    eval_env = env_fn()
    eval_metrics = evaluate_policy(model=model, env=eval_env, num_episodes=3)

    # Save side-by-side comparison figure
    canvas_buf = eval_env.world.canvas.buffer
    target_buf = target.high_res
    diff_buf = np.abs(target_buf - canvas_buf)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].imshow(target_buf)
    axes[0].set_title(f"Target Goal: {image_path.name}", fontsize=11, fontweight="bold")
    axes[0].axis("off")

    axes[1].imshow(canvas_buf)
    axes[1].set_title(f"Trained Canvas (SSIM: {eval_metrics['mean_ssim']:.3f})", fontsize=11, fontweight="bold")
    axes[1].axis("off")

    axes[2].imshow(diff_buf, cmap="hot")
    axes[2].set_title(f"Discrepancy Error Map", fontsize=11, fontweight="bold")
    axes[2].axis("off")

    plt.tight_layout()
    comp_save_path = results_dir / f"{stem_clean}_comparison.png"
    plt.savefig(comp_save_path, dpi=180)
    plt.close()
    print(f"Saved comparison figure to {comp_save_path}")

    return {
        "image": image_path.name,
        "ssim": eval_metrics["mean_ssim"],
        "psnr": eval_metrics["mean_psnr"],
        "similarity": eval_metrics["mean_similarity"],
        "model_path": str(model_save_path),
        "comparison_image": str(comp_save_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Batch Train Fruitfly V2 on data/ Images")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory containing target images")
    parser.add_argument("--timesteps", type=int, default=10000, help="Timesteps per image")
    parser.add_argument("--device", type=str, default="cuda", help="Training device (cuda or cpu)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    data_path = Path(args.data_dir)
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    # Discover images in data_dir and any subdirectories (excluding results / comparisons)
    images = [
        f for f in data_path.glob("**/*")
        if f.is_file()
        and f.suffix.lower() in image_extensions
        and "results" not in f.parts
        and not f.name.endswith("_comparison.png")
    ]

    if not images:
        print(f"No image files found in {data_path.resolve()}. Supported: {image_extensions}")
        return

    print(f"Found {len(images)} target image(s) in {data_path}: {[str(img.relative_to(data_path)) for img in images]}")

    results = []
    for img in sorted(images):
        res = train_single_image(
            image_path=img,
            timesteps=args.timesteps,
            device=args.device,
            seed=args.seed,
        )
        results.append(res)

    # Output Markdown summary table
    report_path = Path("docs/custom_paintings_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write("# 🎨 Custom Images Painting Benchmark Report\n\n")
        f.write(f"Trained on {len(results)} image(s) using device `{args.device}` for {args.timesteps} timesteps each.\n\n")
        f.write("| Image | SSIM | PSNR (dB) | Canvas Similarity | Model File | Visual Comparison |\n")
        f.write("| :--- | :---: | :---: | :---: | :--- | :--- |\n")
        for r in results:
            f.write(f"| **{r['image']}** | {r['ssim']:.4f} | {r['psnr']:.2f} | {r['similarity']:.4f} | `{r['model_path']}` | `![]({r['comparison_image']})` |\n")

    print(f"\n✅ All images trained and evaluated! Report written to {report_path.resolve()}")


if __name__ == "__main__":
    main()
