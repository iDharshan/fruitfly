"""
Test suite for Gymnasium Environment (FruitFlyPaintEnv) in Fruitfly V2.
Verifies Gymnasium API compliance, spaces, reset, step, check_env, and stepping speed.
"""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rl.env import FruitFlyPaintEnv
from biology.interfaces import BiologyConfig
from painting.target import PaintingTarget


def test_gym_env_spaces():
    """Verify observation and action spaces match specification."""
    env = FruitFlyPaintEnv()

    assert env.action_space.shape == (4,)
    assert np.all(env.action_space.low == -1.0)
    assert np.all(env.action_space.high == 1.0)

    keys = set(env.observation_space.spaces.keys())
    expected_keys = {"compass", "sensory", "odor", "pigment", "kinematics", "task"}
    assert keys == expected_keys, f"Missing or extra keys in observation space: {keys ^ expected_keys}"

    assert env.observation_space["compass"].shape == (5,)
    assert env.observation_space["sensory"].shape == (8,)
    assert env.observation_space["odor"].shape == (4,)
    assert env.observation_space["pigment"].shape == (5,)
    assert env.observation_space["kinematics"].shape == (4,)
    assert env.observation_space["task"].shape == (16, 16, 3)


def test_gym_env_reset_and_step():
    """Verify reset and step dynamics."""
    env = FruitFlyPaintEnv()

    obs, info = env.reset(seed=42)
    assert isinstance(obs, dict)
    for key in env.observation_space.spaces:
        assert key in obs
        # Check values within bounds
        assert env.observation_space[key].contains(obs[key]), f"Observation key {key} out of bounds: {obs[key]}"

    # Execute 50 steps with random valid actions
    for step in range(50):
        action = env.action_space.sample()
        obs, reward, term, trunc, info = env.step(action)

        assert isinstance(reward, (float, np.floating))
        assert isinstance(term, bool)
        assert isinstance(trunc, bool)
        assert isinstance(info, dict)

        for key in env.observation_space.spaces:
            assert env.observation_space[key].contains(obs[key]), f"Step {step}: {key} out of bounds"


def test_sb3_check_env():
    """Run Stable-Baselines3 official check_env if installed."""
    try:
        from stable_baselines3.common.env_checker import check_env
        env = FruitFlyPaintEnv()
        check_env(env, warn=True)
        print("Stable-Baselines3 check_env passed successfully!")
    except ImportError:
        print("stable-baselines3 not yet imported; skipping check_env.")


def test_stepping_performance_throughput():
    """Profile headless stepping throughput in steps/second."""
    env = FruitFlyPaintEnv(substeps=12)
    obs, info = env.reset(seed=123)

    n_steps = 200
    action = np.array([0.1, 0.5, 0.5, -0.5], dtype=np.float32)

    t0 = time.perf_counter()
    for _ in range(n_steps):
        obs, reward, term, trunc, info = env.step(action)
    t1 = time.perf_counter()

    elapsed = t1 - t0
    macro_fps = n_steps / elapsed
    internal_physics_fps = macro_fps * 12

    print(f"\nThroughput Benchmark:")
    print(f"  Macro Steps/Second (10 Hz RL): {macro_fps:.1f} steps/s")
    print(f"  Internal Physics/CANN FPS (120 Hz): {internal_physics_fps:.1f} steps/s")

    assert macro_fps > 50.0, f"Stepping too slow: {macro_fps:.1f} steps/s"


if __name__ == "__main__":
    test_gym_env_spaces()
    test_gym_env_reset_and_step()
    test_sb3_check_env()
    test_stepping_performance_throughput()
    print("All Gymnasium environment tests passed successfully!")
