"""
Unit verification test for FlyAgent in agent.py.
Verifies kinematics, torus boundary wrapping, landmark bearing, and particle wake.
"""

import sys
import os
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from toy.agent import FlyAgent
from toy.config import AgentConfig, PANEL_ARENA_RECT

def test_agent_kinematics():
    print("==================================================")
    print("Testing FlyAgent Kinematics & Closed-Loop Feedback")
    print("==================================================")

    agent = FlyAgent()
    print(f"[1] Initial Position: ({agent.x:.1f}, {agent.y:.1f}), Heading: {math.degrees(agent.heading):.1f}°")
    assert agent.min_x < agent.x < agent.max_x
    assert agent.min_y < agent.y < agent.max_y

    # 2. Kinematic stepping with decoded heading
    dt = 0.016
    initial_x = agent.x
    for _ in range(30):
        # Move at 0 deg (towards +X)
        agent.update_kinematics(decoded_heading=0.0, dt=dt)
    
    print(f"[2] Forward translation (0.5s): x moved from {initial_x:.1f} to {agent.x:.1f}")
    assert agent.x > initial_x, "Fly must advance along heading vector"
    assert len(agent.particles) > 0, "Exhaust particles should be emitted while flying"

    # 3. Torus wrapping test
    agent.x = agent.max_x - 5.0
    agent.update_kinematics(decoded_heading=0.0, dt=0.1)
    print(f"[3] Torus wrapping: x wrapped to {agent.x:.1f} (min_x={agent.min_x:.1f}, max_x={agent.max_x:.1f})")
    assert agent.min_x <= agent.x <= agent.max_x, "Agent must wrap within bounds"

    # 4. Landmark placement and bearing
    # Place landmark directly in front of fly
    agent.heading = 0.0
    agent.x = 200.0
    agent.y = 200.0
    agent.set_landmark(x=300.0, y=200.0) # Directly to the right (bearing 0)
    bearing_ahead = agent.get_landmark_bearing()
    print(f"[4] Landmark ahead bearing: {math.degrees(bearing_ahead):.1f}°")
    assert abs(bearing_ahead) < 1e-4

    # Place landmark directly 90 degrees to the right (+Y is down in screen coordinates)
    agent.set_landmark(x=200.0, y=300.0)
    bearing_right = agent.get_landmark_bearing()
    print(f"    Landmark right bearing: {math.degrees(bearing_right):.1f}°")
    assert abs(bearing_right - math.pi/2) < 1e-4

    # Toggle landmark off
    agent.toggle_landmark()
    assert agent.get_landmark_bearing() is None, "Inactive landmark should yield None bearing"

    # 5. Velocity throttle test
    v_init = agent.v
    agent.update_velocity(accel_dir=1.0, dt=0.5)
    print(f"[5] Acceleration: v went from {v_init:.1f} to {agent.v:.1f}")
    assert agent.v > v_init, "Fly must accelerate forward"

    agent.update_velocity(accel_dir=-1.0, dt=1.5)
    print(f"    Braking: v decreased to {agent.v:.1f}")
    assert agent.v < agent.cfg.v_base, "Fly must brake when decelerating"

    print("\n>>> ALL FLY AGENT KINEMATICS TESTS PASSED SUCCESSFULLY! <<<\n")

if __name__ == "__main__":
    test_agent_kinematics()
