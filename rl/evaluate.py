"""
Evaluation Harness for Fruitfly V2 Hybrid Painting Agent.
Benchmarks trained policy or baselines across target geometric shapes.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import numpy as np

from rl.env import FruitFlyPaintEnv
from painting.target import PaintingTarget
from evaluation.metrics import compute_ssim, compute_psnr


def evaluate_policy(
    model: Any,
    env: Optional[FruitFlyPaintEnv] = None,
    target: Optional[PaintingTarget] = None,
    num_episodes: int = 5,
    deterministic: bool = True,
) -> Dict[str, Any]:
    """
    Evaluates a trained policy across target images and computes scientific metrics.
    """
    if env is None:
        env = FruitFlyPaintEnv(target=target, max_episode_steps=800)

    episode_rewards = []
    final_similarities = []
    final_ssims = []
    final_psnrs = []
    distances = []
    reloads = []
    depositions = []

    for ep in range(num_episodes):
        obs, info = env.reset(seed=ep + 100)
        done = False
        truncated = False
        ep_rew = 0.0

        while not (done or truncated):
            if hasattr(model, "predict"):
                action, _ = model.predict(obs, deterministic=deterministic)
            else:
                # Callable or policy function
                action = model(obs)

            obs, rew, done, truncated, info = env.step(action)
            ep_rew += rew

        final_sim = env.world.current_similarity
        canvas_img = env.world.canvas.buffer
        target_img = env.world.target.high_res

        ssim_val = compute_ssim(canvas_img, target_img)
        psnr_val = compute_psnr(canvas_img, target_img)

        episode_rewards.append(ep_rew)
        final_similarities.append(final_sim)
        final_ssims.append(ssim_val)
        final_psnrs.append(psnr_val)
        distances.append(env.world.total_distance)
        reloads.append(env.world.reloads_count)
        depositions.append(env.world.total_pigment_deposited)

    return {
        "mean_reward": float(np.mean(episode_rewards)),
        "std_reward": float(np.std(episode_rewards)),
        "mean_similarity": float(np.mean(final_similarities)),
        "mean_ssim": float(np.mean(final_ssims)),
        "mean_psnr": float(np.mean(final_psnrs)),
        "mean_distance": float(np.mean(distances)),
        "mean_reloads": float(np.mean(reloads)),
        "mean_deposition": float(np.mean(depositions)),
    }
