"""
Fruitfly V2: Interactive 2D Painting Simulator & Cyberpunk Telemetry Dashboard.
Visualizes real-time arena flight, canvas pigment accumulation, E-PG bump dynamics,
P-EN shifter activities, and Antennal Lobe odor channels.
"""

import sys
import os
import argparse
import time
import numpy as np

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

from rl.env import FruitFlyPaintEnv
from painting.target import PaintingTarget
from painting.scripted_agent import ScriptedPaintingFly, AgentState
from evaluation.metrics import compute_ssim, compute_psnr


class PaintingDashboard:
    """
    Real-time Pygame visualization dashboard with live biological telemetry.
    """

    def __init__(self, headless: bool = False, target_shape: str = "square"):
        self.headless = headless
        self.width = 1240
        self.height = 720
        self.fps = 60

        if target_shape == "disc":
            self.target = PaintingTarget.create_disc()
        elif target_shape == "two_tone":
            self.target = PaintingTarget.create_two_tone()
        elif target_shape == "quadrants":
            self.target = PaintingTarget.create_four_color_quadrants()
        else:
            self.target = PaintingTarget.create_solid_square(u0=48, v0=48, width=160, height=160)

        self.env = FruitFlyPaintEnv(target=self.target, substeps=8)
        self.scripted_agent = ScriptedPaintingFly(world=self.env.world, target_color_id=0, stroke_step_y=10.0)

        self.mode = "SCRIPTED"  # "SCRIPTED", "POLICY", "MANUAL"
        self.running = True

        if not self.headless:
            pygame.init()
            pygame.display.set_caption("Fruitfly V2: Hybrid Biological Painting Agent")
            self.screen = pygame.display.set_mode((self.width, self.height))
            self.clock = pygame.time.Clock()
            self.font_small = pygame.font.SysFont("monospace", 12)
            self.font_mid = pygame.font.SysFont("monospace", 15, bold=True)
            self.font_large = pygame.font.SysFont("monospace", 20, bold=True)

    def run(self, max_frames: int = 1000):
        """Main simulation loop."""
        obs, info = self.env.reset(seed=42)
        frame_idx = 0

        while self.running and frame_idx < max_frames:
            dt = 1.0 / float(self.fps)
            frame_idx += 1

            if not self.headless:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False
                        elif event.key == pygame.K_m:
                            # Toggle mode
                            modes = ["SCRIPTED", "MANUAL"]
                            self.mode = modes[(modes.index(self.mode) + 1) % len(modes)]
                        elif event.key == pygame.K_r:
                            obs, info = self.env.reset()
                            self.scripted_agent.reset()

            # Compute actions based on active mode
            if self.mode == "SCRIPTED":
                v, omega, target_z, pen_down, pressure = self.scripted_agent.step(dt=0.016)
                # Map to normalized env action: [steer_bias, throttle, alt, pen]
                steer_bias = float(np.clip(omega / self.env.bio_cfg.omega_bias_max, -1.0, 1.0))
                throttle = float(np.clip((v - self.env.bio_cfg.v_min) / (self.env.bio_cfg.v_max - self.env.bio_cfg.v_min) * 2.0 - 1.0, -1.0, 1.0))
                alt = 1.0 if target_z > 5.0 else -1.0
                pen = pressure if pen_down else -1.0
                action = np.array([steer_bias, throttle, alt, pen], dtype=np.float32)

            elif self.mode == "MANUAL" and not self.headless:
                keys = pygame.key.get_pressed()
                steer = 0.0
                throttle = 0.0
                alt = 1.0
                pen = -1.0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    steer = -1.0
                elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    steer = 1.0
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    throttle = 0.8
                if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    alt = -1.0
                if keys[pygame.K_SPACE]:
                    pen = 1.0
                    alt = -1.0
                action = np.array([steer, throttle, alt, pen], dtype=np.float32)
            else:
                action = np.array([0.0, 0.4, 1.0, -1.0], dtype=np.float32)

            obs, reward, terminated, truncated, info = self.env.step(action)

            if not self.headless:
                self._render_frame(obs, action, info)
                self.clock.tick(self.fps)

        if not self.headless:
            pygame.quit()

        return self.env.world.current_similarity

    def _render_frame(self, obs: dict, action: np.ndarray, info: dict):
        """Renders the split Cyberpunk HUD."""
        self.screen.fill((12, 16, 24))  # Dark background

        # --- LEFT PANEL: ARENA & LIVE CANVAS (0 to 700 px) ---
        arena_rect = pygame.Rect(15, 15, 690, 690)
        pygame.draw.rect(self.screen, (20, 26, 38), arena_rect, border_radius=6)
        pygame.draw.rect(self.screen, (0, 200, 255), arena_rect, width=2, border_radius=6)

        scale = 650.0 / 1000.0  # Scale 1000 arena to 650 display px
        ox, oy = 35, 35

        # 1. Render Odor Halos & Paint Pots
        for pot in self.env.world.pot_manager.pots:
            px = int(ox + pot.x * scale)
            py = int(oy + pot.y * scale)
            c_rgb = (int(pot.color_rgb[0] * 255), int(pot.color_rgb[1] * 255), int(pot.color_rgb[2] * 255))
            # Odor halo
            halo_surf = pygame.Surface((120, 120), pygame.SRCALPHA)
            pygame.draw.circle(halo_surf, (*c_rgb, 35), (60, 60), 55)
            self.screen.blit(halo_surf, (px - 60, py - 60))
            # Pot basin
            pygame.draw.circle(self.screen, c_rgb, (px, py), int(pot.radius * scale))
            pygame.draw.circle(self.screen, (255, 255, 255), (px, py), int(pot.radius * scale), width=2)
            lbl = self.font_small.render(pot.name, True, (240, 240, 240))
            self.screen.blit(lbl, (px - 15, py - 8))

        # 2. Render Live Canvas Surface
        c = self.env.world.canvas
        cx0 = int(ox + c.x_min * scale)
        cy0 = int(oy + c.y_min * scale)
        cw = int(c.size * scale)
        ch = int(c.size * scale)

        # Convert canvas numpy buffer to pygame surface
        canvas_uint8 = np.clip(c.buffer * 255.0, 0, 255).astype(np.uint8)
        # Transpose (256, 256, 3) to pygame surface format (w, h, c)
        surf_canvas = pygame.surfarray.make_surface(np.transpose(canvas_uint8, (1, 0, 2)))
        surf_scaled = pygame.transform.scale(surf_canvas, (cw, ch))
        self.screen.blit(surf_scaled, (cx0, cy0))
        pygame.draw.rect(self.screen, (255, 255, 0), (cx0, cy0, cw, ch), width=2)

        # 3. Render Fruit Fly Agent
        fx = int(ox + self.env.world.fly_x * scale)
        fy = int(oy + self.env.world.fly_y * scale)
        theta = self.env.world.fly_theta

        # Fly body triangle
        tip = (fx + int(14 * np.cos(theta)), fy + int(14 * np.sin(theta)))
        left_wing = (fx + int(10 * np.cos(theta + 2.5)), fy + int(10 * np.sin(theta + 2.5)))
        right_wing = (fx + int(10 * np.cos(theta - 2.5)), fy + int(10 * np.sin(theta - 2.5)))
        color_fly = (255, 100, 50) if self.env.world.brush.in_contact else (50, 255, 100)
        pygame.draw.polygon(self.screen, color_fly, [tip, left_wing, right_wing])

        # Brush pigment reservoir dot
        if self.env.world.brush.pigment_volume > 0.0:
            b_col = (
                int(self.env.world.brush.color_rgb[0] * 255),
                int(self.env.world.brush.color_rgb[1] * 255),
                int(self.env.world.brush.color_rgb[2] * 255),
            )
            pygame.draw.circle(self.screen, b_col, (fx, fy), 4)

        # --- RIGHT PANEL: BIOLOGICAL TELEMETRY & GAUGES (720 to 1220 px) ---
        rx = 720
        ry = 15

        title = self.font_large.render("NEURAL TELEMETRY (CX / VNC)", True, (0, 230, 255))
        self.screen.blit(title, (rx, ry))

        mode_str = f"MODE: [{self.mode}] (Press M to toggle)"
        lbl_mode = self.font_mid.render(mode_str, True, (255, 200, 0))
        self.screen.blit(lbl_mode, (rx, ry + 30))

        # A. Biological Compass Ring (E-PG bump)
        ring_cx, ring_cy = rx + 120, ry + 160
        ring_r = 70
        pygame.draw.circle(self.screen, (30, 40, 60), (ring_cx, ring_cy), ring_r, width=12)

        epg = obs["compass"]
        theta_head = np.arctan2(epg[0], epg[1])
        coherence = epg[2]
        bump_x = int(ring_cx + (ring_r - 6) * np.cos(theta_head))
        bump_y = int(ring_cy + (ring_r - 6) * np.sin(theta_head))
        glow_rad = max(4, int(coherence * 16))
        pygame.draw.circle(self.screen, (255, 220, 0), (bump_x, bump_y), glow_rad)

        lbl_c = self.font_mid.render(f"E-PG Compass: {np.degrees(theta_head):.1f}°", True, (200, 220, 255))
        self.screen.blit(lbl_c, (rx + 220, ry + 130))
        lbl_coh = self.font_small.render(f"Bump Coherence: {coherence*100:.1f}%", True, (160, 180, 200))
        self.screen.blit(lbl_coh, (rx + 220, ry + 155))
        lbl_trq = self.font_small.render(f"Torque Differential: {epg[3]:.2f}", True, (160, 180, 200))
        self.screen.blit(lbl_trq, (rx + 220, ry + 175))

        # B. Antennal Lobe Odor Glomeruli (R, G, B, Y)
        gy = ry + 260
        lbl_al = self.font_mid.render("Antennal Lobe Glomeruli:", True, (0, 230, 255))
        self.screen.blit(lbl_al, (rx, gy))

        pot_names = ["R (Red)", "G (Green)", "B (Blue)", "Y (Yellow)"]
        bar_cols = [(255, 60, 60), (60, 240, 60), (60, 120, 255), (255, 230, 0)]
        al_acts = obs["odor"]
        for idx, (pname, bcol) in enumerate(zip(pot_names, bar_cols)):
            by = gy + 25 + idx * 22
            pygame.draw.rect(self.screen, (30, 40, 55), (rx, by, 200, 16), border_radius=3)
            val = float(al_acts[idx])
            fill_w = int(val * 200)
            if fill_w > 0:
                pygame.draw.rect(self.screen, bcol, (rx, by, fill_w, 16), border_radius=3)
            lbl = self.font_small.render(f"{pname}: {val:.2f}", True, (220, 220, 220))
            self.screen.blit(lbl, (rx + 210, by))

        # C. Target Thumbnail & Painting Progress
        ty = ry + 380
        lbl_prog = self.font_mid.render(f"Painting Progress: S = {info['similarity']:.4f}", True, (0, 255, 180))
        self.screen.blit(lbl_prog, (rx, ty))

        # Render mini target preview
        t_uint8 = np.clip(self.target.high_res * 255.0, 0, 255).astype(np.uint8)
        t_surf = pygame.surfarray.make_surface(np.transpose(t_uint8, (1, 0, 2)))
        t_scaled = pygame.transform.scale(t_surf, (80, 80))
        self.screen.blit(t_scaled, (rx, ty + 30))
        pygame.draw.rect(self.screen, (255, 255, 255), (rx, ty + 30, 80, 80), width=1)
        lbl_t = self.font_small.render("Target Goal", True, (180, 180, 180))
        self.screen.blit(lbl_t, (rx, ty + 115))

        # Progress bar
        pygame.draw.rect(self.screen, (30, 40, 55), (rx + 100, ty + 40, 300, 22), border_radius=4)
        sim_val = info["similarity"]
        sim_w = int(np.clip(sim_val, 0.0, 1.0) * 300)
        pygame.draw.rect(self.screen, (0, 255, 180), (rx + 100, ty + 40, sim_w, 22), border_radius=4)

        lbl_sim_pct = self.font_small.render(f"Similarity Fidelity: {sim_val*100:.1f}%", True, (240, 240, 240))
        self.screen.blit(lbl_sim_pct, (rx + 100, ty + 70))
        lbl_rel = self.font_small.render(f"Pot Reloads: {info['reloads_count']}", True, (240, 240, 240))
        self.screen.blit(lbl_rel, (rx + 100, ty + 90))

        # D. Action Commands
        ay = ry + 520
        lbl_act = self.font_mid.render("Motor Action Commands:", True, (0, 230, 255))
        self.screen.blit(lbl_act, (rx, ay))
        cmd_labels = [
            f"Yaw Bias Δω : {action[0]:+.2f}",
            f"Throttle v  : {action[1]:+.2f}",
            f"Altitude z  : {action[2]:+.2f}",
            f"Brush Press : {action[3]:+.2f}",
        ]
        for idx, cmd in enumerate(cmd_labels):
            lbl_c = self.font_small.render(cmd, True, (200, 220, 240))
            self.screen.blit(lbl_c, (rx + (idx % 2) * 200, ay + 28 + (idx // 2) * 22))

        pygame.display.flip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fruitfly V2 Painting Dashboard")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display")
    parser.add_argument("--target", type=str, default="square", choices=["square", "disc", "two_tone", "quadrants"])
    parser.add_argument("--frames", type=int, default=1000, help="Max simulation frames")
    args = parser.parse_args()

    dashboard = PaintingDashboard(headless=args.headless, target_shape=args.target)
    dashboard.run(max_frames=args.frames)
