"""
Smoke test and verification for PPO training pipeline in Fruitfly V2.
Verifies policy network construction, gradient flow, SB3 learn step, and checkpointing.
"""

import sys
import os
import shutil
from pathlib import Path
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rl.env import FruitFlyPaintEnv
from rl.policy import FruitFlyFeaturesExtractor
from rl.evaluate import evaluate_policy
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv


def test_ppo_training_smoke():
    """Fast smoke test executing 128 steps of PPO learning."""
    print("Testing Fruitfly V2 PPO Training Smoke Test...")

    temp_dir = Path("scratch/test_training_artifacts")
    temp_dir.mkdir(parents=True, exist_ok=True)

    def make_env():
        return FruitFlyPaintEnv(max_episode_steps=64, substeps=4)

    vec_env = DummyVecEnv([make_env])

    policy_kwargs = dict(
        features_extractor_class=FruitFlyFeaturesExtractor,
        features_extractor_kwargs=dict(features_dim=176),
        net_arch=dict(pi=[64, 64], vf=[64, 64]),
    )

    model = PPO(
        "MultiInputPolicy",
        vec_env,
        policy_kwargs=policy_kwargs,
        n_steps=64,
        batch_size=32,
        n_epochs=2,
        learning_rate=1e-3,
        verbose=0,
        seed=42,
    )

    # Train for 128 environment steps (2 rollouts of 64)
    model.learn(total_timesteps=128)

    # Verify model prediction
    test_env = make_env()
    obs, info = test_env.reset(seed=10)
    action, _ = model.predict(obs, deterministic=True)
    assert action.shape == (4,)
    assert np.all(action >= -1.0) and np.all(action <= 1.0)

    # Verify save and reload
    save_file = temp_dir / "test_model.zip"
    model.save(save_file)
    assert save_file.exists()

    loaded_model = PPO.load(save_file)
    act_loaded, _ = loaded_model.predict(obs, deterministic=True)
    assert np.allclose(action, act_loaded, atol=1e-5)

    # Verify evaluation harness
    eval_res = evaluate_policy(model=loaded_model, env=test_env, num_episodes=2)
    assert "mean_similarity" in eval_res
    assert "mean_ssim" in eval_res
    print(f"Smoke test evaluation result: S={eval_res['mean_similarity']:.4f}, SSIM={eval_res['mean_ssim']:.4f}")

    # Cleanup temp directory
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("PPO training smoke test passed successfully!")


if __name__ == "__main__":
    test_ppo_training_smoke()
