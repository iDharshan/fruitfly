"""
Verification test for Phase 1 Exit Criterion:
The deterministic scripted agent completes a simple painting (Red square on canvas)
achieving S > 0.85 without any reinforcement learning.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from painting.canvas import Canvas
from painting.world import PaintingWorld
from painting.target import PaintingTarget
from painting.scripted_agent import ScriptedPaintingFly, AgentState


def test_scripted_agent_paints_target():
    """
    Runs the deterministic scripted agent in a closed-loop simulation
    until the red square is painted with similarity S > 0.85.
    """
    print("\n==================================================")
    print("Testing Scripted Painting Agent (Condition A Baseline)")
    print("==================================================")

    target = PaintingTarget.create_solid_square(
        color_rgb=(1.0, 0.0, 0.0),
        u0=38,
        v0=38,
        width=180,
        height=180,
        name="solid_red_square",
    )

    world = PaintingWorld(target=target)
    agent = ScriptedPaintingFly(world=world, target_color_id=0, stroke_step_y=12.0)

    initial_sim = world.current_similarity
    print(f"Initial Canvas Similarity: {initial_sim:.4f}")

    dt = 0.02  # 50 Hz physics stepping
    max_steps = 10000  # Up to 200 seconds of simulated flight

    for step in range(max_steps):
        v, omega, target_z, pen_down, pressure = agent.step(dt=dt)
        step_info = world.step(
            dt=dt,
            target_v=v,
            steer_omega=omega,
            target_z=target_z,
            pen_down=pen_down,
            pen_pressure=pressure,
        )

        sim = step_info["similarity"]

        if step % 500 == 0:
            print(
                f"Step {step:4d} (t={step*dt:5.1f}s) | "
                f"State: {agent.state.name:15s} | "
                f"Alt: {world.brush.altitude:4.1f} | "
                f"Pigment: {world.brush.pigment_volume:4.2f} | "
                f"Reloads: {world.reloads_count} | "
                f"Similarity: {sim:.4f}"
            )

        if sim >= 0.85 and world.reloads_count >= 1:
            print(f"\nSUCCESS: Reached target similarity {sim:.4f} >= 0.85 at step {step} (t={step*dt:.1f}s)!")
            break

        if agent.state == AgentState.FINISH and sim >= 0.85:
            break

    final_sim = world.current_similarity
    print(f"\nFinal Similarity: {final_sim:.4f}")
    print(f"Total Distance Flown: {world.total_distance:.1f} px")
    print(f"Total Reloads: {world.reloads_count}")
    print(f"Total Pigment Deposited: {world.total_pigment_deposited:.2f}")
    print(f"Total Spills: {world.total_spills}")

    assert final_sim >= 0.85, f"Expected similarity >= 0.85, got {final_sim:.4f}"
    assert world.reloads_count >= 1, "Agent must have reloaded pigment from pot"
    assert world.total_pigment_deposited > 0.5, "Agent must have deposited pigment on canvas"


if __name__ == "__main__":
    test_scripted_agent_paints_target()
    print("Phase 1 Exit Criterion Verified!")
