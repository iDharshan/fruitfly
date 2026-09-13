"""
PPO Training Pipeline and Progressive Curriculum for Fruitfly V2.
Supports staged training from sensory homing to full multi-color painting.
"""

import argparse
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

from rl.env import FruitFlyPaintEnv
from rl.policy import FruitFlyFeaturesExtractor
from painting.target import PaintingTarget
from biology.interfaces import BiologyConfig


def create_env_for_stage(stage: int = 4, seed: int = 42, **kwargs) -> FruitFlyPaintEnv:
    """
    Factory creating FruitFlyPaintEnv configured for the specified curriculum stage:
      - Stage 0: Navigation
      - Stage 1: Odor Homing
      - Stage 2: Reloading
      - Stage 3: Canvas Delivery
      - Stage 4: Full Painting
    """
    if stage == 0:
        # Simple navigation to beacon
        target = PaintingTarget.create_solid_square(width=64, height=64)
        env = FruitFlyPaintEnv(target=target, max_episode_steps=300, **kwargs)
    elif stage == 1:
        # Odor homing to pot
        target = PaintingTarget.create_solid_square(width=64, height=64)
        env = FruitFlyPaintEnv(target=target, max_episode_steps=400, **kwargs)
    elif stage == 2:
        # Pot reload practice
        target = PaintingTarget.create_solid_square(width=80, height=80)
        env = FruitFlyPaintEnv(target=target, max_episode_steps=500, **kwargs)
    elif stage == 3:
        # Pot to canvas flight
        target = PaintingTarget.create_solid_square(width=100, height=100)
        env = FruitFlyPaintEnv(target=target, max_episode_steps=600, **kwargs)
    else:
        # Full painting task
        target = PaintingTarget.create_solid_square(width=128, height=128)
        env = FruitFlyPaintEnv(target=target, max_episode_steps=1000, **kwargs)

    env.reset(seed=seed)
    return env


def train(
    stage: int = 4,
    total_timesteps: int = 10000,
    seed: int = 42,
    save_dir: str = "models",
    log_dir: str = "logs",
    device: str = "auto",
):
    """Executes PPO training with Stable-Baselines3."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    Path(save_dir).mkdir(parents=True, exist_ok=True)
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    def env_fn():
        return create_env_for_stage(stage=stage, seed=seed)

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
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=1,
        tensorboard_log=log_dir,
        device=device,
        seed=seed,
    )

    print(f"Starting Fruitfly V2 PPO Training (Stage {stage}) for {total_timesteps} timesteps...")
    model.learn(total_timesteps=total_timesteps)

    save_path = Path(save_dir) / f"fruitfly_ppo_stage_{stage}.zip"
    model.save(save_path)
    print(f"Model saved successfully to {save_path}!")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Fruitfly V2 PPO Agent")
    parser.add_argument("--stage", type=int, default=4, help="Curriculum stage (0-4)")
    parser.add_argument("--timesteps", type=int, default=2000, help="Total environment steps")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="auto", help="Device (cpu, cuda, auto)")
    args = parser.parse_args()

    train(
        stage=args.stage,
        total_timesteps=args.timesteps,
        seed=args.seed,
        device=args.device,
    )
