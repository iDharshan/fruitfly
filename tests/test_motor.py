"""
Unit test suite for biological motor bridge, descending neurons, and premotor primitives.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from biology.motor import MotorPrimitives
from biology.descending import DescendingBridge
from biology.interfaces import BrainOutput, BiologyConfig


def test_motor_action_translation():
    """Verify that normalized actions map correctly to biological flight commands."""
    bridge = DescendingBridge()

    # Action: Neutral steering, full forward, cruise altitude, pen up
    action = np.array([0.0, 1.0, 1.0, -1.0], dtype=np.float32)
    output = bridge.process_command(policy_action=action, bio_steering_omega=0.0)

    assert isinstance(output, BrainOutput)
    assert abs(output.steering_omega) < 1e-4
    assert output.forward_velocity == bridge.cfg.v_max
    assert output.altitude_command > bridge.cfg.z_contact
    assert not output.pen_down
    assert output.pen_pressure == 0.0


def test_steering_bias_modulation():
    """Verify that learned bias modulates biological PFL3 steering without exceeding max."""
    bridge = DescendingBridge()

    # Biological steering is turning right at 2.0 rad/s
    # Policy commands max left bias (-1.0)
    action = np.array([-1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    output = bridge.process_command(policy_action=action, bio_steering_omega=2.0)

    # Net omega = 2.0 + (-1.0 * 2.5) = -0.5 rad/s
    assert abs(output.steering_omega - (-0.5)) < 1e-3

    # Check saturation clamp at omega_max
    action_max = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    output_sat = bridge.process_command(policy_action=action_max, bio_steering_omega=3.5)
    assert output_sat.steering_omega <= bridge.cfg.omega_max


def test_pen_and_altitude_contact():
    """Verify pen down and landing control."""
    bridge = DescendingBridge()

    # Action commanding ground descent (a2 <= 0) and pen contact with pressure 0.8
    action = np.array([0.0, 0.0, -0.5, 0.8], dtype=np.float32)
    output = bridge.process_command(policy_action=action, bio_steering_omega=0.0)

    assert output.altitude_command == 0.0
    assert output.pen_down
    assert abs(output.pen_pressure - 0.8) < 1e-4


def test_direct_torque_mode_condition_e():
    """Verify direct torque ablation mode."""
    bridge = DescendingBridge()
    action = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    out_direct = bridge.process_command(policy_action=action, direct_torque=True)
    out_hybrid = bridge.process_command(policy_action=action, direct_torque=False)

    assert isinstance(out_direct, BrainOutput)
    # Direct mode uses raw torque mapping
    assert out_direct.steering_omega != out_hybrid.steering_omega


if __name__ == "__main__":
    test_motor_action_translation()
    test_steering_bias_modulation()
    test_pen_and_altitude_contact()
    test_direct_torque_mode_condition_e()
    print("All motor bridge tests passed successfully!")
