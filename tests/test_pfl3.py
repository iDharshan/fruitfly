"""
Unit verification and regression tests for Biological PFL3 Comparator & Autonomous Steering.
Tests:
  1. 24x48 synaptic matrix alignment and numerical stability.
  2. Egocentric Left odor bearing (-90°) evokes stronger Left PFL3 firing and omega < 0.
  3. Egocentric Right odor bearing (+90°) evokes stronger Right PFL3 firing and omega > 0.
  4. Closed-loop autonomous navigation reaches and consumes food pellet within 120 frames.
"""

import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from toy.circuit import DualRingAttractor, wrap_angle, ang_dist
from toy.agent import FlyAgent
from toy.food import FoodSystem, OdorReading
from toy.config import CIRCUIT_CFG, AGENT_CFG, PANEL_ARENA_RECT


def test_pfl3_matrix_alignment():
    print("==================================================")
    print("Test 1: PFL3 Synaptic Matrix Alignment & Stability")
    print("==================================================")
    circuit = DualRingAttractor(CIRCUIT_CFG)

    # 1. Verify dimensions
    assert hasattr(circuit, "W_ep_pfl3"), "DualRingAttractor must have W_ep_pfl3 matrix"
    assert hasattr(circuit, "W_fb_pfl3"), "DualRingAttractor must have W_fb_pfl3 matrix"
    assert circuit.W_ep_pfl3.shape == (24, 48), f"W_ep_pfl3 shape must be (24, 48), got {circuit.W_ep_pfl3.shape}"
    assert circuit.W_fb_pfl3.shape == (24, 24), f"W_fb_pfl3 shape must be (24, 24), got {circuit.W_fb_pfl3.shape}"

    # 2. Check non-zero weights and finite values
    assert np.all(np.isfinite(circuit.W_ep_pfl3)), "W_ep_pfl3 contains NaN or Inf"
    assert np.all(np.isfinite(circuit.W_fb_pfl3)), "W_fb_pfl3 contains NaN or Inf"
    assert np.sum(circuit.W_ep_pfl3) > 100.0, "W_ep_pfl3 should have non-zero synaptic weights"
    assert np.sum(circuit.W_fb_pfl3) > 10.0, "W_fb_pfl3 should have non-zero synaptic weights"

    # 3. Check symmetry at neutral forward odor
    neutral_odor = OdorReading(
        strength=1.0, grad_x=0.0, grad_y=0.0, grad_mag=0.0,
        world_dir=0.0, relative_bearing=0.0, nearest_dist=100.0, nearest_id=1
    )
    for _ in range(30):
        omega, tv, l_mean, r_mean = circuit.step_pfl3(neutral_odor, dt=0.016)

    print(f"  Neutral Odor (Ψ=0°): PFL3_L={l_mean:.2f}, PFL3_R={r_mean:.2f}, omega={omega:.3f} rad/s")
    assert abs(omega) < 0.25, f"At neutral bearing, steering omega should be near zero (got {omega:.3f})"
    print("  [PASS] Test 1: PFL3 matrices aligned and symmetrically stable.")


def test_left_odor_steering():
    print("\n==================================================")
    print("Test 2: Left Odor Steering Response (Ψ = -90°)")
    print("==================================================")
    circuit = DualRingAttractor(CIRCUIT_CFG)
    circuit.reset(initial_heading=0.0)

    # Odor at 90 degrees to the left
    left_odor = OdorReading(
        strength=1.0, grad_x=0.0, grad_y=-1.0, grad_mag=1.0,
        world_dir=-np.pi / 2.0, relative_bearing=-np.pi / 2.0, nearest_dist=100.0, nearest_id=1
    )

    for _ in range(25):
        omega, target_v, l_rate, r_rate = circuit.step_pfl3(left_odor, dt=0.016)

    print(f"  Left Odor: PFL3_L={l_rate:.2f}, PFL3_R={r_rate:.2f}, omega_auto={omega:.2f} rad/s")
    assert l_rate > r_rate, f"Left PFL3 must fire stronger than Right PFL3 for left odor (L={l_rate:.2f}, R={r_rate:.2f})"
    assert omega < -0.4, f"Steering velocity omega must be negative (CCW left turn) for left odor (got {omega:.2f})"
    print("  [PASS] Test 2: Left odor properly drives Left PFL3 and produces leftward steering.")


def test_right_odor_steering():
    print("\n==================================================")
    print("Test 3: Right Odor Steering Response (Ψ = +90°)")
    print("==================================================")
    circuit = DualRingAttractor(CIRCUIT_CFG)
    circuit.reset(initial_heading=0.0)

    # Odor at 90 degrees to the right
    right_odor = OdorReading(
        strength=1.0, grad_x=0.0, grad_y=1.0, grad_mag=1.0,
        world_dir=np.pi / 2.0, relative_bearing=np.pi / 2.0, nearest_dist=100.0, nearest_id=1
    )

    for _ in range(25):
        omega, target_v, l_rate, r_rate = circuit.step_pfl3(right_odor, dt=0.016)

    print(f"  Right Odor: PFL3_L={l_rate:.2f}, PFL3_R={r_rate:.2f}, omega_auto={omega:.2f} rad/s")
    assert r_rate > l_rate, f"Right PFL3 must fire stronger than Left PFL3 for right odor (L={l_rate:.2f}, R={r_rate:.2f})"
    assert omega > 0.4, f"Steering velocity omega must be positive (CW right turn) for right odor (got {omega:.2f})"
    print("  [PASS] Test 3: Right odor properly drives Right PFL3 and produces rightward steering.")


def test_closed_loop_autonomous_consumption():
    print("\n==================================================")
    print("Test 4: Closed-Loop Headless Autonomous Food Foraging")
    print("==================================================")
    circuit = DualRingAttractor(CIRCUIT_CFG)
    agent = FlyAgent(AGENT_CFG, PANEL_ARENA_RECT)
    food_system = FoodSystem(PANEL_ARENA_RECT, num_pellets=1)

    # Set predictable initial condition:
    # Fly at center (400, 400), facing East (heading = 0.0)
    # Food pellet placed at (490, 340) - 100 px away at roughly -35° angle
    agent.x = 400.0
    agent.y = 400.0
    agent.heading = 0.0
    circuit.reset(initial_heading=0.0)

    pellet = food_system.pellets[0]
    pellet.x = 490.0
    pellet.y = 340.0

    dt = 0.016
    reached = False
    reached_step = None

    for step in range(120):
        # 1. Sense odor
        odor = food_system.get_odor_at(agent.x, agent.y, agent.heading)

        # 2. PFL3 decision
        omega_auto, target_v, l_act, r_act = circuit.step_pfl3(
            odor_reading=odor, dt=dt, v_base=agent.cfg.v_base
        )

        # 3. Dual-ring CANN integration
        circuit.step_frame(dt_frame=dt, omega=omega_auto)

        # 4. Decode compass heading & update kinematics
        dec_h, amp, coh = circuit.decode_heading()
        agent.update_velocity(0.0, dt, target_v=target_v)
        agent.update_kinematics(dec_h, dt)

        # 5. Check eating
        n_eaten, nrg = food_system.check_eating(agent.x, agent.y, agent.heading)
        if n_eaten > 0:
            agent.eat_food(nrg, n_eaten)
            reached = True
            reached_step = step
            print(f"  Food pellet consumed at step {step} ({step * dt:.2f}s)! Agent pos: ({agent.x:.1f}, {agent.y:.1f})")
            break

        food_system.update(dt)

    assert reached, f"Fly failed to reach and eat food pellet within 120 frames! Final agent pos: ({agent.x:.1f}, {agent.y:.1f})"
    assert agent.food_eaten >= 1, "Agent food_eaten count should be at least 1"
    print(f"  [PASS] Test 4: Autonomous navigation successfully consumed food in {reached_step} frames.")


if __name__ == "__main__":
    test_pfl3_matrix_alignment()
    test_left_odor_steering()
    test_right_odor_steering()
    test_closed_loop_autonomous_consumption()
    print("\n>>> ALL PFL3 BIOLOGICAL STEERING TESTS PASSED SUCCESSFULLY! <<<\n")
