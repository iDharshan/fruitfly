"""
Unit verification test for Continuous Attractor Neural Network (CANN) in circuit.py.
Verifies attractor formation, stability, velocity shifting, and cue locking.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from toy.circuit import DualRingAttractor, wrap_angle, ang_dist
from toy.config import CircuitConfig

def test_attractor_dynamics():
    print("==================================================")
    print("Testing Drosophila DualRingAttractor CANN Dynamics")
    print("==================================================")
    
    cfg = CircuitConfig()
    model = DualRingAttractor(cfg)
    
    # 1. Initial bump state
    theta0, amp0, coh0 = model.decode_heading()
    print(f"[1] Initial Bump: heading={np.degrees(theta0):.1f}°, amp={amp0:.2f}, coherence={coh0*100:.1f}%")
    assert amp0 > 1.0, "Attractor bump should have non-zero initial amplitude"
    assert coh0 > 0.4, "Attractor bump should be localized"
    
    # 2. Stability test (stationary for 1.0 s)
    dt = 0.016
    for _ in range(60):
        model.step_frame(dt_frame=dt, omega=0.0)
    
    theta_stat, amp_stat, coh_stat = model.decode_heading()
    drift = abs(float(wrap_angle(theta_stat - theta0)))
    print(f"[2] Stationary Stability (1s): heading={np.degrees(theta_stat):.1f}°, amp={amp_stat:.2f}, drift={np.degrees(drift):.2f}°")
    assert drift < 0.1, f"Stationary bump should not drift without input (drift={np.degrees(drift):.2f}°)"
    assert amp_stat > 10.0, "Bump should persist stably over time (working memory)"
    
    # 3. Left turn rotation test (omega = -2.5 rad/s)
    print("\n[3] Injecting Left Turn (omega = -2.5 rad/s, P-EN_L activated)...")
    h_prev = theta_stat
    cum_rot_left = 0.0
    for step in range(30):  # 0.5 second
        model.step_frame(dt_frame=dt, omega=-2.5)
        h, a, c = model.decode_heading()
        dh = float(ang_dist(h, h_prev))
        cum_rot_left += dh
        h_prev = h
        if step % 10 == 0:
            act_l, act_r = model.get_shifter_activities()
            print(f"    t={step*dt:.2f}s: heading={np.degrees(h):.1f}°, cum_rot={np.degrees(cum_rot_left):.1f}°, P-EN_L={act_l:.2f}, P-EN_R={act_r:.2f}")
    
    print(f"    Total Left unwrapped rotation: {np.degrees(cum_rot_left):.1f}°")
    assert cum_rot_left < -0.4, f"Bump must rotate leftward under negative angular velocity! Got {cum_rot_left:.2f} rad"
    
    # Check synaptic arcs
    arcs = model.get_active_synaptic_arcs()
    print(f"    Active P-EN -> E-PG synaptic transmission arcs: {len(arcs)}")
    assert len(arcs) > 0, "Active synaptic arcs should be generated when turning"

    # 4. Right turn rotation test (omega = +2.5 rad/s)
    print("\n[4] Injecting Right Turn (omega = +2.5 rad/s, P-EN_R activated)...")
    h_prev, _, _ = model.decode_heading()
    cum_rot_right = 0.0
    for step in range(30):  # 0.5 second
        model.step_frame(dt_frame=dt, omega=+2.5)
        h, a, c = model.decode_heading()
        dh = float(ang_dist(h, h_prev))
        cum_rot_right += dh
        h_prev = h
        if step % 10 == 0:
            act_l, act_r = model.get_shifter_activities()
            print(f"    t={step*dt:.2f}s: heading={np.degrees(h):.1f}°, cum_rot={np.degrees(cum_rot_right):.1f}°, P-EN_L={act_l:.2f}, P-EN_R={act_r:.2f}")
    
    print(f"    Total Right unwrapped rotation: {np.degrees(cum_rot_right):.1f}°")
    assert cum_rot_right > 0.4, f"Bump must rotate rightward under positive angular velocity! Got {cum_rot_right:.2f} rad"

    # 5. Visual Landmark Locking Test
    target_landmark = np.radians(110.0)  # +110 degrees
    print(f"\n[5] Injecting Visual Landmark Cue at {np.degrees(target_landmark):.1f}°...")
    for step in range(60):  # 1.0 second
        model.step_frame(dt_frame=dt, omega=0.0, landmark_bearing=target_landmark, landmark_active=True)
        if step % 15 == 0:
            h, a, c = model.decode_heading()
            err = abs(float(ang_dist(h, target_landmark)))
            print(f"    t={step*dt:.2f}s: heading={np.degrees(h):.1f}°, cue error={np.degrees(err):.1f}°")
            
    final_h, _, _ = model.decode_heading()
    cue_error = abs(float(ang_dist(final_h, target_landmark)))
    print(f"    Final heading: {np.degrees(final_h):.1f}°, error to cue: {np.degrees(cue_error):.2f}°")
    assert cue_error < 0.1, f"Bump should lock onto visual cue! Final error: {np.degrees(cue_error):.2f}°"

    print("\n>>> ALL CANN CIRCUIT DYNAMICS TESTS PASSED SUCCESSFULLY! <<<\n")

if __name__ == "__main__":
    test_attractor_dynamics()
