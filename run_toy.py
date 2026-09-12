#!/usr/bin/env python3
"""
Drosophila Closed-Loop Compass Attractor Toy.
Main application entry point and interactive event loop.
Simulates central complex E-PG compass neurons, P-EN velocity shifters,
and 3D whole-brain neural point cloud activations.

Usage:
  ./fly_env/bin/python run_toy.py
  ./fly_env/bin/python run_toy.py --headless-test
  ./fly_env/bin/python run_toy.py --fps 120 --fullscreen
"""

import argparse
import math
import os
import sys
import time
import pygame

from toy.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE,
    PANEL_ARENA_RECT, PANEL_NEURAL_RECT, CIRCUIT_CFG, AGENT_CFG
)
from toy.circuit import DualRingAttractor
from toy.agent import FlyAgent
from toy.food import FoodSystem
from toy.telemetry import TelemetryTracker
from toy.renderer import NeonDashboardRenderer


def parse_args():
    parser = argparse.ArgumentParser(
        description="Drosophila Closed-Loop Compass Attractor Simulator Toy"
    )
    parser.add_argument("--fps", type=int, default=FPS, help="Target frames per second (default: 60)")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--headless-test", action="store_true", help="Run 120 frames headlessly to verify stability and exit")
    parser.add_argument("--substeps", type=int, default=8, help="Neural ODE substeps per frame (default: 8)")
    parser.add_argument("--auto", action="store_true", help="Launch directly in autonomous PFL3 steering mode")
    parser.add_argument("--view-mode", type=int, default=3, choices=[1, 2, 3], help="Initial view mode: 1=3D Brain, 2=Dual Ring, 3=Split (default: 3)")
    return parser.parse_args()


def run_simulation():
    args = parse_args()

    # Headless test mode setup
    if args.headless_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        print("[INIT] Running in headless test mode with SDL dummy driver...")

    # Initialize Pygame
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    flags = pygame.DOUBLEBUF | pygame.HWSURFACE
    if args.fullscreen:
        flags |= pygame.FULLSCREEN

    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
    except pygame.error as e:
        print(f"[WARN] Hardware surface request failed ({e}), falling back to default surface...")
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    clock = pygame.time.Clock()

    # Core Components
    circuit_cfg = CIRCUIT_CFG
    circuit_cfg.substeps_per_frame = args.substeps
    circuit = DualRingAttractor(circuit_cfg)
    agent = FlyAgent(AGENT_CFG, PANEL_ARENA_RECT)
    food_system = FoodSystem(PANEL_ARENA_RECT, num_pellets=1)
    telemetry = TelemetryTracker(history_len=240)
    renderer = NeonDashboardRenderer(screen)
    renderer.set_view_mode(args.view_mode)

    simulation_mode = "AUTO" if args.auto else "MANUAL"
    running = True
    is_paused = False

    print("================================================================================")
    print(" DROSOPHILA CENTRAL COMPLEX COMPASS SIMULATOR ACTIVE")
    print("================================================================================")
    print(f" Target Resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT} | Target FPS: {args.fps}")
    print(f" Neural Populations: {circuit.n_epg} E-PG Compass Nodes + {circuit.n_pen_total} P-EN Shifters + {circuit.n_pfl3} PFL3 Comparators")
    print(f" 3D Brain Cloud: 1,920+ anatomical nodes with 0-200+ Hz live neural activations")
    print(f" Synaptic Torque Ratio: {circuit_cfg.w_pe_ratio:.2f}x (P-EN feedback vs E-PG forward)")
    pellet_noun = "Pellet" if len(food_system.pellets) == 1 else "Pellets"
    print(f" Food Arena: {len(food_system.pellets)} {pellet_noun} with continuous radial odor field")
    print(" Controls:")
    print("   [ < / > or A / D ]  Inject Angular Velocity to Left/Right P-EN Shifters")
    print("   [ ^ / v or W / S ]  Accelerate / Decelerate Forward Velocity")
    print("   [ M ]               Toggle Mode (MANUAL ↔ AUTO)")
    print("   [ TAB or 1 / 2 / 3] Switch View: 1=3D Brain, 2=Dual Ring, 3=Split View")
    print("   [ L ]               Toggle 3D Anatomical Callout Badges (On / Off)")
    print("   [ Left Click ]      Drop / Move Visual Sun Landmark in Arena")
    print("   [ Right Click ]     Toggle Sun Landmark Cue On / Off (Off by default)")
    print("   [ T ]               Toggle Phototaxis Seek (Auto-steering to Sun)")
    print("   [ Space ]           Pause / Resume Simulation")
    print("   [ R ]               Reset Fly, Compass Bump, and Food Pellets")
    print("   [ C ]               Clear Visual Landmark")
    print("   [ ESC / Q ]         Quit Simulator")
    print("================================================================================")

    frame_count = 0
    start_wall_time = time.time()

    # Place a default landmark at top-center of arena, but kept INACTIVE by default
    arena_center_x = (agent.min_x + agent.max_x) / 2.0
    arena_top_y = agent.min_y + 100.0
    agent.set_landmark(arena_center_x, arena_top_y, active=False)

    is_dragging_brain = False
    drag_last_pos = (0, 0)

    while running:
        dt = clock.tick(args.fps) / 1000.0
        dt = min(0.05, dt if dt > 0 else 1.0 / args.fps)
        actual_fps = clock.get_fps()

        # ----------------------------------------------------------------------
        # 1. PROCESS INPUT EVENTS
        # ----------------------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_SPACE:
                    is_paused = not is_paused
                elif event.key == pygame.K_TAB:
                    new_mode = renderer.cycle_view_mode()
                    names = {1: "3D BRAIN MESH", 2: "DUAL RING ATTRACTOR", 3: "SPLIT VIEW"}
                    print(f"[VIEW] Switched to {names.get(new_mode)}")
                elif event.key == pygame.K_1:
                    renderer.set_view_mode(1)
                elif event.key == pygame.K_2:
                    renderer.set_view_mode(2)
                elif event.key == pygame.K_3:
                    renderer.set_view_mode(3)
                elif event.key == pygame.K_h:
                    pos_name = renderer.cycle_hud_position()
                    renderer.show_toast(f"HUD POSITION: {pos_name.upper()}")
                    print(f"[UI] Stats HUD position: {pos_name}")
                elif event.key == pygame.K_l:
                    badges_on = renderer.toggle_callouts()
                    print(f"[UI] 3D Callout Badges: {'ON' if badges_on else 'OFF'}")
                elif event.key == pygame.K_t:
                    active = agent.toggle_phototaxis()
                    print(f"[PHOTOTAXIS] Auto-seek {'ON' if active else 'OFF (Free manual flight)'}")
                elif event.key == pygame.K_m:
                    simulation_mode = "AUTO" if simulation_mode == "MANUAL" else "MANUAL"
                    renderer.show_toast(f"MODE: {simulation_mode}")
                    print(f"[MODE] Switched to {simulation_mode}")
                elif event.key == pygame.K_r:
                    circuit.reset(initial_heading=0.0)
                    agent.reset(initial_heading=0.0)
                    food_system.reset()
                    print("[RESET] Attractor bump, fly, and food pellets reset")
                elif event.key == pygame.K_c:
                    agent.clear_landmark()
                    print("[LANDMARK] Visual cue cleared.")
                elif event.key in (pygame.K_p, pygame.K_F12, pygame.K_PRINTSCREEN, pygame.K_SYSREQ):
                    os.makedirs("screenshots", exist_ok=True)
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join("screenshots", f"screenshot_{timestamp}.png")
                    pygame.image.save(screen, filename)
                    renderer.show_toast(f"SAVED: {filename}")
                    print(f"[SCREENSHOT] Saved high-resolution capture to {filename}")

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # First check UI buttons & HUD clicks
                if event.button == 1 and renderer.handle_click(mx, my):
                    pass
                else:
                    rx_a, ry_a, rw_a, rh_a = PANEL_ARENA_RECT
                    rx_n, ry_n, rw_n, rh_n = PANEL_NEURAL_RECT

                    # Check click inside Arena (Left Panel)
                    if rx_a <= mx <= rx_a + rw_a and ry_a <= my <= ry_a + rh_a:
                        if event.button == 1:  # Left Click: Place / Move Sun
                            agent.set_landmark(mx, my)
                            print(f"[LANDMARK] Sun placed at ({mx}, {my})")
                        elif event.button == 3:  # Right Click: Toggle active
                            agent.toggle_landmark()
                            status = "ON" if agent.landmark_active else "OFF"
                            print(f"[LANDMARK] Sun visual cue {status}")

                    # Check click inside Neural Panel (Right Panel: 3D Camera Controls)
                    elif rx_n <= mx <= rx_n + rw_n and ry_n <= my <= ry_n + rh_n:
                        if event.button == 1:  # Left Click: Begin 3D Orbit Drag
                            is_dragging_brain = True
                            drag_last_pos = (mx, my)
                        elif event.button == 3:  # Right Click: Reset 3D Camera
                            renderer.handle_reset_camera()
                        elif event.button == 4:  # Scroll Up: Zoom in
                            renderer.handle_mouse_scroll(1)
                        elif event.button == 5:  # Scroll Down: Zoom out
                            renderer.handle_mouse_scroll(-1)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    is_dragging_brain = False

            elif event.type == pygame.MOUSEMOTION:
                if is_dragging_brain:
                    dx = event.pos[0] - drag_last_pos[0]
                    dy = event.pos[1] - drag_last_pos[1]
                    drag_last_pos = event.pos
                    renderer.handle_mouse_drag(dx, dy)

            elif event.type == pygame.MOUSEWHEEL:
                renderer.handle_mouse_scroll(event.y)


        # Steering and Throttle Inputs
        turn_rate = agent.cfg.turn_rate
        steering_omega = 0.0
        accel_dir = 0.0
        target_v_auto = None

        # Step biological PFL3 comparator neurons with current odor reading
        # (Runs in both MANUAL and AUTO modes for live telemetry & brain cloud visualization)
        odor_reading = food_system.get_odor_at(agent.x, agent.y, agent.heading)
        omega_pfl3, v_pfl3, pfl3_l, pfl3_r = circuit.step_pfl3(
            odor_reading=odor_reading,
            dt=dt,
            v_base=agent.cfg.v_base,
        )

        if simulation_mode == "MANUAL":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                steering_omega -= turn_rate  # Turn Left -> P-EN_L fires
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                steering_omega += turn_rate  # Turn Right -> P-EN_R fires

            # Acceleration / Throttle Input
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                accel_dir += 1.0
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                accel_dir -= 1.0

            # If phototaxis mode is explicitly enabled, add beacon steering
            if agent.phototaxis_active and steering_omega == 0.0:
                steering_omega = agent.compute_phototaxis_steering()
        else:
            # Autonomous Mode: Biological PFL3 comparator directly drives steering and speed
            steering_omega = omega_pfl3
            target_v_auto = v_pfl3

        # ----------------------------------------------------------------------
        # 2. UPDATE SIMULATION PHYSICS & NEURAL DYNAMICS
        # ----------------------------------------------------------------------
        if not is_paused:
            # 2a. Sensation: Get landmark allocentric azimuth in world
            lm_azimuth = agent.get_landmark_world_angle()

            # 2b. Neural CANN integration: Step E-PG + P-EN continuous attractor ODEs
            # In AUTO mode, steering_omega is driven by PFL3 differential activity.
            # In MANUAL mode, steering_omega is driven by user keyboard inputs.
            circuit.step_frame(
                dt_frame=dt,
                omega=steering_omega,
                landmark_azimuth=lm_azimuth,
                landmark_active=agent.landmark_active,
            )

            # 2c. Population Vector Readout: Decode compass heading angle from E-PG
            decoded_h, amplitude, coherence = circuit.decode_heading()

            # 2d. Motor Kinematics: Fly steers according to its central complex heading
            agent.update_velocity(accel_dir, dt, target_v=target_v_auto)
            agent.update_kinematics(decoded_h, dt)

            # 2e. Food & Odor System: Check eating and update food visual effects
            n_eaten, energy_gained = food_system.check_eating(agent.x, agent.y, agent.heading)
            if n_eaten > 0:
                agent.eat_food(energy_gained, count=n_eaten)
            food_system.update(dt)

            # 2f. Telemetry: Log biological CANN metrics
            act_l, act_r = circuit.get_shifter_activities()
            telemetry.record(
                dt=dt,
                heading_rad=decoded_h,
                angular_vel_rad=steering_omega,
                amplitude=amplitude,
                coherence=coherence,
                pen_left=act_l,
                pen_right=act_r,
                speed=agent.v,
                landmark_active=agent.landmark_active,
                landmark_bearing_rad=agent.get_landmark_bearing() or 0.0,
                pfl3_left=pfl3_l,
                pfl3_right=pfl3_r,
            )

        # ----------------------------------------------------------------------
        # 3. RENDER FRAME
        # ----------------------------------------------------------------------
        renderer.render_frame(
            dt=dt,
            circuit=circuit,
            agent=agent,
            telemetry=telemetry,
            fps_actual=actual_fps if actual_fps > 0 else float(args.fps),
            is_paused=is_paused,
            food_system=food_system,
            mode=simulation_mode,
        )

        pygame.display.flip()
        frame_count += 1

        # Headless test exit condition
        if args.headless_test and frame_count >= 120:
            elapsed = time.time() - start_wall_time
            print(f"[HEADLESS TEST COMPLETED] 120 frames executed in {elapsed:.2f}s (~{120/elapsed:.1f} FPS equivalent).")
            os.makedirs("screenshots", exist_ok=True)
            mode_names = {1: "toy_3d_brain.png", 2: "toy_dual_ring.png", 3: "toy_split_view.png"}
            shot_file = mode_names.get(renderer.view_mode, "toy_split_view.png")
            shot_path = os.path.join("screenshots", shot_file)
            pygame.image.save(screen, shot_path)
            print(f"[HEADLESS TEST] Verification frame saved to {shot_path}")
            running = False

    pygame.quit()
    print("[QUIT] Drosophila Compass Attractor Toy shut down cleanly.")


if __name__ == "__main__":
    run_simulation()
