"""
Hardware-Accelerated Pygame Renderer for Drosophila Closed-Loop Compass Toy.
Features accurate scientific labeling, clean vertical partitioning in split mode,
high-fidelity 3D anatomical brain point cloud, 16-wedge dual-ring graphics,
and a compact floating stats HUD.
"""

from typing import Dict, Tuple, List, Optional
import math
import numpy as np
import pygame

from .config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    COLOR_BG, COLOR_PANEL_BG, COLOR_PANEL_BORDER, COLOR_PANEL_HEADER,
    COLOR_EPG_CYAN, COLOR_PEN_MAGENTA, COLOR_PEN_LEFT, COLOR_PEN_RIGHT,
    COLOR_GOLD_FORWARD, COLOR_LIME_FEEDBACK, COLOR_SUN_AMBER,
    COLOR_FOOD_EMERALD, COLOR_FOOD_CORE, COLOR_ODOR_AURA,
    COLOR_PFL3_LEFT, COLOR_PFL3_RIGHT,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
    COLOR_GRID, COLOR_GAUGE_BG, COLOR_ACTIVE_BORDER,
    PANEL_ARENA_RECT, PANEL_NEURAL_RECT, STATS_HUD_RECT,
    STATS_HUD_RECT_ARENA_BR, STATS_HUD_RECT_ARENA_TR, STATS_HUD_W, STATS_HUD_H,
    BTN_MODES_X, BTN_MODES_Y, BTN_MODE_WIDTH, BTN_MODE_HEIGHT, BTN_MODE_SPACING,
    RADIUS_EPG, RADIUS_PEN, HEADER_HEIGHT, FOOTER_HEIGHT, CONTENT_TOP
)
from .circuit import DualRingAttractor, wrap_angle, ang_dist
from .agent import FlyAgent
from .telemetry import TelemetryTracker
from .brain_cloud import BrainPointCloud
from .food import FoodSystem, FoodPellet, OdorReading


class NeonDashboardRenderer:
    """
    Renders the complete 2-panel closed-loop central complex simulator:
      - Left Panel (Expanded): 2D Flight Arena (World) with Sun Beacon & Particle Wake
      - Right Panel: Cleanly Partitioned Neural Activity View (3D Brain / Dual Ring / Split)
      - Compact Top-Right Stats HUD
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen

        # Initialize fonts
        pygame.font.init()
        self.font_title = pygame.font.SysFont("dejavusans,freesansbold,arial", 16, bold=True)
        self.font_header = pygame.font.SysFont("dejavusans,freesansbold,arial", 13, bold=True)
        self.font_main = pygame.font.SysFont("dejavusans,freesansbold,arial", 12)
        self.font_mono = pygame.font.SysFont("dejavusansmono,consolas,monospace", 12)
        self.font_mono_bold = pygame.font.SysFont("dejavusansmono,consolas,monospace", 13, bold=True)
        self.font_big_digit = pygame.font.SysFont("dejavusansmono,consolas,monospace", 20, bold=True)
        self.font_hero = pygame.font.SysFont("dejavusans,freesansbold,arial", 19, bold=True)
        self.font_tiny = pygame.font.SysFont("dejavusans,freesansbold,arial", 10)
        self.font_sub = pygame.font.SysFont("dejavusans,freesansbold,arial", 11)

        # Pre-bake GPU bloom glow textures
        self.glow_cache: Dict[Tuple[Tuple[int, int, int], int], pygame.Surface] = {}
        self._prebake_glow_textures()

        # 3D Anatomical Brain Engine
        self.brain_cloud = BrainPointCloud()

        # View mode: 1 = BRAIN_3D, 2 = DUAL_RING, 3 = SPLIT (Default)
        self.view_mode: int = 3

        # Callout badges visibility toggle
        self.show_callouts: bool = True

        # Toast notification system
        self.toast_msg: Optional[str] = None
        self.toast_timer: float = 0.0

        # Animation timer
        self.anim_time: float = 0.0

        # HUD Position: 0 = Arena Bottom-Right (Default), 1 = Arena Top-Right, 2 = Neural Top-Right, 3 = Hidden
        self.hud_pos_index: int = 0
        self.hud_rect_current: Optional[Tuple[int, int, int, int]] = STATS_HUD_RECT_ARENA_BR

        # Pre-calculate View Mode button hitboxes
        self.mode_buttons: List[Tuple[int, pygame.Rect, str]] = [
            (1, pygame.Rect(BTN_MODES_X, BTN_MODES_Y, BTN_MODE_WIDTH, BTN_MODE_HEIGHT), "3D BRAIN"),
            (2, pygame.Rect(BTN_MODES_X + BTN_MODE_WIDTH + BTN_MODE_SPACING, BTN_MODES_Y, BTN_MODE_WIDTH, BTN_MODE_HEIGHT), "DUAL RING"),
            (3, pygame.Rect(BTN_MODES_X + (BTN_MODE_WIDTH + BTN_MODE_SPACING) * 2, BTN_MODES_Y, BTN_MODE_WIDTH, BTN_MODE_HEIGHT), "SPLIT"),
        ]

    def toggle_callouts(self) -> bool:
        """Toggles floating anatomical 3D callout badges on/off."""
        self.show_callouts = not self.show_callouts
        status = "ON" if self.show_callouts else "OFF"
        self.show_toast(f"CALLOUT BADGES: {status}")
        return self.show_callouts

    def cycle_hud_position(self) -> str:
        """Cycles the floating stats HUD between Arena BR -> Arena TR -> Neural TR -> Hidden."""
        self.hud_pos_index = (self.hud_pos_index + 1) % 4
        names = ["Arena Bottom-Right", "Arena Top-Right", "Neural Top-Right", "Hidden"]
        return names[self.hud_pos_index]

    def get_hud_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Returns the current bounds tuple (x, y, w, h) for the stats HUD, or None if hidden."""
        if self.hud_pos_index == 0:
            return STATS_HUD_RECT_ARENA_BR
        elif self.hud_pos_index == 1:
            return STATS_HUD_RECT_ARENA_TR
        elif self.hud_pos_index == 2:
            return (PANEL_NEURAL_RECT[0] + PANEL_NEURAL_RECT[2] - STATS_HUD_W - 16, CONTENT_TOP + 86, STATS_HUD_W, STATS_HUD_H)
        else:
            return None

    def handle_click(self, mx: int, my: int) -> bool:
        """
        Handles mouse clicks on UI elements (View Mode buttons & HUD card).
        Returns True if the click was consumed.
        """
        # Check View Mode Buttons
        for mode_id, rect, _ in self.mode_buttons:
            if rect.collidepoint(mx, my):
                self.set_view_mode(mode_id)
                return True

        # Check HUD Card click (cycles position)
        hud_box = self.get_hud_rect()
        if hud_box is not None:
            hx, hy, hw, hh = hud_box
            if hx <= mx <= hx + hw and hy <= my <= hy + hh:
                new_pos = self.cycle_hud_position()
                self.show_toast(f"HUD POSITION: {new_pos.upper()}")
                return True

        return False

    def _prebake_glow_textures(self):
        """Pre-computes smooth radial alpha halos for zero-overhead bloom rendering."""
        colors = [
            COLOR_EPG_CYAN,
            COLOR_PEN_MAGENTA,
            COLOR_PEN_LEFT,
            COLOR_PEN_RIGHT,
            COLOR_PFL3_LEFT,
            COLOR_PFL3_RIGHT,
            COLOR_LIME_FEEDBACK,
            COLOR_SUN_AMBER,
            COLOR_GOLD_FORWARD,
            COLOR_FOOD_EMERALD,
            (255, 255, 255),
        ]
        radii = [4, 6, 8, 10, 12, 16]

        for col in colors:
            for r in radii:
                size = r * 2
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                center = r
                for rad in range(r, 0, -1):
                    frac = 1.0 - (rad / r)
                    alpha = int(75 * (frac ** 2.2))
                    pygame.draw.circle(surf, (*col, alpha), (center, center), rad)
                self.glow_cache[(col, r)] = surf

    def draw_glow(self, center_x: float, center_y: float, color: Tuple[int, int, int], radius: int):
        """Blits cached radial bloom surface centered at (center_x, center_y)."""
        available = [4, 6, 8, 10, 12, 16]
        closest_r = min(available, key=lambda x: abs(x - radius))
        surf = self.glow_cache.get((color, closest_r))
        if not surf:
            # Match nearest pre-baked color
            cached_colors = list({k[0] for k in self.glow_cache.keys()})
            if cached_colors:
                closest_c = min(cached_colors, key=lambda c: (c[0]-color[0])**2 + (c[1]-color[1])**2 + (c[2]-color[2])**2)
                surf = self.glow_cache.get((closest_c, closest_r))
        if surf:
            self.screen.blit(surf, (int(center_x - closest_r), int(center_y - closest_r)), special_flags=pygame.BLEND_ADD)

    def handle_mouse_drag(self, dx: int, dy: int):
        """Orbits 3D brain camera when dragging in neural panel."""
        self.brain_cloud.yaw += dx * 0.007
        self.brain_cloud.pitch = float(np.clip(self.brain_cloud.pitch + dy * 0.007, -1.2, 1.2))
        self.brain_cloud.auto_rotate = False

    def handle_mouse_scroll(self, scroll_y: int):
        """Zooms 3D brain camera in/out."""
        self.brain_cloud.user_scale = float(np.clip(self.brain_cloud.user_scale + scroll_y * 0.12, 0.5, 3.0))

    def handle_reset_camera(self):
        """Resets 3D brain camera view to default."""
        self.brain_cloud.reset_camera()
        self.show_toast("3D CAMERA: RESET")

    def cycle_view_mode(self):
        """Cycles between SPLIT -> BRAIN 3D -> DUAL RING."""
        self.view_mode = (self.view_mode % 3) + 1
        return self.view_mode

    def set_view_mode(self, mode: int):
        if mode in (1, 2, 3):
            self.view_mode = mode

    def show_toast(self, msg: str, duration: float = 2.5):
        """Displays a floating on-screen confirmation toast."""
        self.toast_msg = msg
        self.toast_timer = duration

    def render_frame(
        self,
        dt: float,
        circuit: DualRingAttractor,
        agent: FlyAgent,
        telemetry: TelemetryTracker,
        fps_actual: float,
        is_paused: bool = False,
        food_system: Optional[FoodSystem] = None,
        mode: str = "MANUAL",
    ):
        """Full composite render of expanded arena, neural view, and compact HUD."""
        self.anim_time += dt

        # Update 3D brain activities
        self.brain_cloud.update_dynamics(circuit, agent, dt, food_system=food_system)

        # Clear background
        self.screen.fill(COLOR_BG)

        # Draw Window Chrome (Header & Footer)
        self._render_header(fps_actual, is_paused, mode)
        self._render_footer()

        # Render Left: Expanded Flight Arena
        self._render_panel_arena(agent, food_system, mode)

        # Render Right: Neural Activity View (3D Brain / Dual Ring / Split)
        self._render_panel_neural(circuit, agent, food_system=food_system, mode=mode)

        # Render Floating Compact Stats HUD
        self._render_stats_hud(circuit, agent, food_system, mode)

        # Render Active Toast Notification (e.g. Screenshot Saved)
        if self.toast_timer > 0 and self.toast_msg:
            self.toast_timer -= dt
            self._render_toast(self.toast_msg)

    def _render_toast(self, msg: str):
        """Renders floating glowing confirmation toast banner."""
        t_surf = self.font_mono_bold.render(msg, True, COLOR_EPG_CYAN)
        tw, th = t_surf.get_width() + 28, t_surf.get_height() + 14
        tx = SCREEN_WIDTH // 2 - tw // 2
        ty = 56

        toast_bg = pygame.Surface((tw, th), pygame.SRCALPHA)
        pygame.draw.rect(toast_bg, (15, 22, 32, 230), (0, 0, tw, th), border_radius=6)
        pygame.draw.rect(toast_bg, (0, 245, 212, 220), (0, 0, tw, th), width=1, border_radius=6)
        self.screen.blit(toast_bg, (tx, ty))
        self.screen.blit(t_surf, (tx + 14, ty + 7))

    def _render_header(self, fps: float, is_paused: bool, mode: str = "MANUAL"):
        """Draws top banner."""
        pygame.draw.rect(self.screen, COLOR_PANEL_HEADER, (0, 0, SCREEN_WIDTH, HEADER_HEIGHT))
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (0, HEADER_HEIGHT), (SCREEN_WIDTH, HEADER_HEIGHT), 1)

        title_surf = self.font_title.render("DROSOPHILA CENTRAL COMPLEX COMPASS SIMULATOR", True, COLOR_EPG_CYAN)
        self.screen.blit(title_surf, (20, 8))

        sub_surf = self.font_tiny.render(
            "CONNECTOMICS CANN ARCHITECTURE | 122 NEURONS (48 E-PG + 48 P-EN + 24 PFL3) | 2.09x TORQUE | 3D VNC MESH",
            True, COLOR_TEXT_SECONDARY
        )
        self.screen.blit(sub_surf, (22, 27))

        # Operating Mode badge
        mode_col = COLOR_EPG_CYAN if mode == "MANUAL" else COLOR_FOOD_EMERALD
        mode_surf = self.font_mono_bold.render(f"● [{mode}]", True, mode_col)
        self.screen.blit(mode_surf, (SCREEN_WIDTH - 400, 13))

        # Status indicator
        status_text = "PAUSED" if is_paused else "RUNNING"
        status_col = COLOR_SUN_AMBER if is_paused else COLOR_LIME_FEEDBACK
        status_surf = self.font_mono_bold.render(f"● {status_text}", True, status_col)
        self.screen.blit(status_surf, (SCREEN_WIDTH - 270, 13))

        fps_surf = self.font_mono.render(f"{fps:4.1f} FPS (GPU ACCEL)", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(fps_surf, (SCREEN_WIDTH - 165, 14))

    def _render_footer(self):
        """Draws bottom controls cheat-sheet."""
        foot_y = SCREEN_HEIGHT - FOOTER_HEIGHT
        pygame.draw.rect(self.screen, COLOR_PANEL_HEADER, (0, foot_y, SCREEN_WIDTH, FOOTER_HEIGHT))
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (0, foot_y), (SCREEN_WIDTH, foot_y), 1)

        controls = [
            ("< / > or A / D", "Steer Shifters"),
            ("^ / v or W / S", "Throttle"),
            ("M", "Manual/Auto"),
            ("TAB / 1-3", "View Mode"),
            ("L", "Labels"),
            ("H", "HUD Pos"),
            ("Right-Click", "Toggle Sun"),
            ("T", "Phototaxis"),
            ("P / F12", "Screenshot"),
            ("Space", "Pause"),
            ("R", "Reset"),
        ]

        x_cur = 20
        y_cur = foot_y + 16
        for key, desc in controls:
            key_surf = self.font_mono_bold.render(f"[{key}]", True, COLOR_EPG_CYAN)
            self.screen.blit(key_surf, (x_cur, y_cur))
            x_cur += key_surf.get_width() + 5

            desc_surf = self.font_main.render(desc, True, COLOR_TEXT_SECONDARY)
            self.screen.blit(desc_surf, (x_cur, y_cur + 1))
            x_cur += desc_surf.get_width() + 14

    def _render_panel_arena(self, agent: FlyAgent, food_system: Optional[FoodSystem] = None, mode: str = "MANUAL"):
        """Renders expanded 2-D flight arena with landmark, sensory beam, particle wake, food pellets, and fly."""
        rx, ry, rw, rh = PANEL_ARENA_RECT
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, PANEL_ARENA_RECT, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, PANEL_ARENA_RECT, width=1, border_radius=6)

        # Header bar
        header_h = 28
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (rx, ry + header_h), (rx + rw, ry + header_h), 1)
        t_surf = self.font_header.render("PANEL 1: 2-D FLIGHT ARENA (WORLD)", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(t_surf, (rx + 12, ry + 6))

        if agent.phototaxis_active:
            mode_badge = " [PHOTOTAXIS ACTIVE]"
        elif mode == "AUTO":
            mode_badge = " [AUTONOMOUS FLIGHT]"
        else:
            mode_badge = " [MANUAL FLIGHT]"
        food_count = len(food_system.pellets) if food_system else 0
        pellet_label = "PELLET" if food_count == 1 else "PELLETS"
        sub_surf = self.font_tiny.render(f"EXPANDED {rw}x{rh} TORUS{mode_badge} · {food_count} {pellet_label}", True, COLOR_TEXT_MUTED)
        self.screen.blit(sub_surf, (rx + rw - sub_surf.get_width() - 12, ry + 8))

        # Corner ticks
        tick_len = 10
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, (rx, ry), (rx + tick_len, ry), 2)
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, (rx, ry), (rx, ry + tick_len), 2)
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, (rx + rw - 1, ry), (rx + rw - 1 - tick_len, ry), 2)
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, (rx + rw - 1, ry), (rx + rw - 1, ry + tick_len), 2)

        # Arena clipping
        arena_clip = pygame.Rect(rx + 2, ry + 30, rw - 4, rh - 32)
        prev_clip = self.screen.get_clip()
        self.screen.set_clip(arena_clip)

        # Draw radar grid
        grid_step = 45
        for gx in range(int(agent.min_x), int(agent.max_x) + 1, grid_step):
            pygame.draw.line(self.screen, COLOR_GRID, (gx, int(agent.min_y)), (gx, int(agent.max_y)), 1)
        for gy in range(int(agent.min_y), int(agent.max_y) + 1, grid_step):
            pygame.draw.line(self.screen, COLOR_GRID, (int(agent.min_x), gy), (int(agent.max_x), gy), 1)

        # Boundary border
        pygame.draw.rect(
            self.screen,
            (28, 38, 54),
            (int(agent.min_x), int(agent.min_y), int(agent.max_x - agent.min_x), int(agent.max_y - agent.min_y)),
            width=1
        )

        # Draw Food Pellets & Odor Aura
        if food_system is not None:
            for p in food_system.pellets:
                px, py = int(p.x), int(p.y)
                pulse = 1.0 + 0.18 * math.sin(self.anim_time * 4.0 + p.pulse_phase)

                # Faint scent plume aura
                self.draw_glow(px, py, COLOR_FOOD_EMERALD, int(28 * pulse))
                self.draw_glow(px, py, COLOR_FOOD_CORE, int(12 * pulse))

                # Food pellet core
                pellet_r = max(4, int(p.radius * (0.92 + 0.12 * math.sin(p.pulse_phase))))
                pygame.draw.circle(self.screen, COLOR_FOOD_EMERALD, (px, py), pellet_r)
                pygame.draw.circle(self.screen, COLOR_FOOD_CORE, (px - 1, py - 1), max(2, pellet_r - 2))
                pygame.draw.circle(self.screen, (255, 255, 255), (px - 2, py - 2), 1)

            # Draw Food Eating Visual Effects
            for eff in food_system.effects:
                progress = eff.age / eff.max_age
                fade_alpha = max(0, min(255, int(255 * (1.0 - progress))))
                ring_r = int(5 + progress * 32)

                # Expanding bioluminescent halo ring
                if ring_r > 0 and fade_alpha > 0:
                    ring_surf = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(
                        ring_surf,
                        (*COLOR_FOOD_EMERALD, fade_alpha),
                        (ring_r + 2, ring_r + 2),
                        ring_r,
                        width=max(1, int(3 * (1.0 - progress))),
                    )
                    self.screen.blit(ring_surf, (int(eff.x - ring_r - 2), int(eff.y - ring_r - 2)), special_flags=pygame.BLEND_ADD)

                # Floating "+1" score popup
                pop_y = eff.y - 12 - progress * 24
                pop_surf = self.font_tiny.render("+1", True, (255, 255, 200))
                pop_surf.set_alpha(fade_alpha)
                self.screen.blit(pop_surf, (int(eff.x - pop_surf.get_width() // 2), int(pop_y)))

                # Sparkle particles
                for pt in eff.particles:
                    p_frac = max(0.0, pt.life / pt.max_life)
                    p_alpha = max(0, min(255, int(255 * (p_frac ** 1.3))))
                    pr = max(1, int(pt.radius * p_frac))
                    p_s = pygame.Surface((pr * 4, pr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(p_s, (*pt.color, p_alpha), (pr * 2, pr * 2), pr)
                    self.screen.blit(p_s, (int(pt.x - pr * 2), int(pt.y - pr * 2)), special_flags=pygame.BLEND_ADD)

        # Draw Visual Landmark (Sun)
        if agent.landmark_x is not None and agent.landmark_y is not None:
            lx, ly = agent.landmark_x, agent.landmark_y
            pulse = 1.0 + 0.15 * math.sin(self.anim_time * 5.0)

            if agent.landmark_active:
                # Multi-layer solar corona
                self.draw_glow(lx, ly, COLOR_SUN_AMBER, int(42 * pulse))
                self.draw_glow(lx, ly, (255, 230, 140), int(22 * pulse))

                ray_count = 12
                ray_r1 = 15.0
                ray_r2 = 27.0 * pulse
                angle_offset = self.anim_time * 1.8
                for ri in range(ray_count):
                    ang = angle_offset + ri * (2.0 * math.pi / ray_count)
                    x1 = lx + ray_r1 * math.cos(ang)
                    y1 = ly + ray_r1 * math.sin(ang)
                    x2 = lx + ray_r2 * math.cos(ang)
                    y2 = ly + ray_r2 * math.sin(ang)
                    r_col = (255, 215, 90) if (ri % 2 == 0) else COLOR_SUN_AMBER
                    pygame.draw.line(self.screen, r_col, (int(x1), int(y1)), (int(x2), int(y2)), 2 if ri % 2 == 0 else 1)

                # Sensory ray connecting Sun to Fly eye with distance & retinotopic bearing tag
                dx = agent.x - lx
                dy = agent.y - ly
                dist = math.hypot(dx, dy)
                if dist > 24.0:
                    steps = int(dist / 14.0)
                    for si in range(0, steps, 2):
                        p1x = lx + (si / steps) * dx
                        p1y = ly + (si / steps) * dy
                        p2x = lx + ((si + 1) / steps) * dx
                        p2y = ly + ((si + 1) / steps) * dy
                        pygame.draw.line(self.screen, (255, 209, 102, 170), (int(p1x), int(p1y)), (int(p2x), int(p2y)), 1)

                    # Retinotopic bearing tag at ray midpoint
                    mark_b = agent.get_landmark_bearing()
                    if mark_b is not None:
                        deg_b = math.degrees(mark_b)
                        mid_x = (lx + agent.x) / 2.0
                        mid_y = (ly + agent.y) / 2.0
                        b_tag = self.font_tiny.render(f"Ψ: {deg_b:+.0f}°", True, (255, 225, 140))
                        tag_bg = pygame.Surface((b_tag.get_width() + 6, b_tag.get_height() + 2), pygame.SRCALPHA)
                        pygame.draw.rect(tag_bg, (18, 24, 34, 200), (0, 0, tag_bg.get_width(), tag_bg.get_height()), border_radius=3)
                        self.screen.blit(tag_bg, (int(mid_x - tag_bg.get_width() / 2), int(mid_y - 8)))
                        self.screen.blit(b_tag, (int(mid_x - b_tag.get_width() / 2), int(mid_y - 7)))

                pygame.draw.circle(self.screen, COLOR_SUN_AMBER, (int(lx), int(ly)), 12)
                pygame.draw.circle(self.screen, (255, 245, 200), (int(lx), int(ly)), 6)
                pygame.draw.circle(self.screen, (255, 255, 255), (int(lx), int(ly)), 3)
            else:
                pygame.draw.circle(self.screen, (100, 80, 40), (int(lx), int(ly)), 8, width=1)
                pygame.draw.line(self.screen, (100, 80, 40), (int(lx - 9), int(ly - 9)), (int(lx + 9), int(ly + 9)), 1)
                t_off = self.font_tiny.render("OFF", True, (110, 95, 60))
                self.screen.blit(t_off, (int(lx - t_off.get_width() / 2), int(ly + 10)))

        # Draw Particle Wake
        for p in agent.particles:
            frac = p.life / p.max_life
            rad = max(1.0, p.radius * frac)
            col = COLOR_EPG_CYAN if p.color_type == "cyan" else COLOR_SUN_AMBER
            alpha = int(220 * (frac ** 1.5))
            p_surf = pygame.Surface((int(rad * 4), int(rad * 4)), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (*col, alpha), (int(rad * 2), int(rad * 2)), int(rad))
            self.screen.blit(p_surf, (int(p.x - rad * 2), int(p.y - rad * 2)), special_flags=pygame.BLEND_ADD)

        # Draw Fly Agent
        self._render_fly_vector(agent)

        self.screen.set_clip(prev_clip)

    def _render_fly_vector(self, agent: FlyAgent):
        """Draws detailed anatomical vector fruit fly with fluttering wings, halteres, and heading laser."""
        fx, fy = agent.x, agent.y
        h = agent.heading
        cos_h = math.cos(h)
        sin_h = math.sin(h)

        def rot(px: float, py: float) -> Tuple[int, int]:
            rx = fx + (px * cos_h - py * sin_h)
            ry = fy + (px * sin_h + py * cos_h)
            return int(rx), int(ry)

        # Heading laser line with glowing arrowhead
        laser_len = 52.0
        laser_end = (int(fx + laser_len * cos_h), int(fy + laser_len * sin_h))
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, (int(fx), int(fy)), laser_end, 2)
        self.draw_glow(laser_end[0], laser_end[1], COLOR_EPG_CYAN, 12)

        # Halteres (Dipteran gyroscopic balancing organs vibrating behind wings)
        halt_osc = math.cos(agent.wing_phase) * 3.5
        halt_l_base = rot(-6, -4)
        halt_l_tip = rot(-8, -13 + halt_osc)
        halt_r_base = rot(-6, 4)
        halt_r_tip = rot(-8, 13 - halt_osc)
        pygame.draw.line(self.screen, (150, 175, 205), halt_l_base, halt_l_tip, 1)
        pygame.draw.circle(self.screen, (220, 240, 255), halt_l_tip, 2)
        pygame.draw.line(self.screen, (150, 175, 205), halt_r_base, halt_r_tip, 1)
        pygame.draw.circle(self.screen, (220, 240, 255), halt_r_tip, 2)

        # Translucent fluttering wings with wing veins
        wing_flap = math.sin(agent.wing_phase) * 0.45
        wing_len = agent.cfg.wing_span
        wing_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        # Left wing
        w_l_pts = [
            rot(2, -4),
            rot(-4 - 10 * wing_flap, -wing_len),
            rot(-16, -wing_len * 0.75),
            rot(-8, -4),
        ]
        pygame.draw.polygon(wing_surf, (160, 225, 255, 120), w_l_pts)
        pygame.draw.polygon(wing_surf, (225, 248, 255, 190), w_l_pts, width=1)
        # Wing veins
        pygame.draw.line(wing_surf, (235, 250, 255, 150), rot(0, -4), rot(-8, -wing_len * 0.6), 1)
        pygame.draw.line(wing_surf, (200, 235, 255, 100), rot(-3, -4), rot(-12, -wing_len * 0.5), 1)

        # Right wing
        w_r_pts = [
            rot(2, 4),
            rot(-4 - 10 * wing_flap, wing_len),
            rot(-16, wing_len * 0.75),
            rot(-8, 4),
        ]
        pygame.draw.polygon(wing_surf, (160, 225, 255, 120), w_r_pts)
        pygame.draw.polygon(wing_surf, (225, 248, 255, 190), w_r_pts, width=1)
        # Wing veins
        pygame.draw.line(wing_surf, (235, 250, 255, 150), rot(0, 4), rot(-8, wing_len * 0.6), 1)
        pygame.draw.line(wing_surf, (200, 235, 255, 100), rot(-3, 4), rot(-12, wing_len * 0.5), 1)

        self.screen.blit(wing_surf, (0, 0))

        # Abdomen with tergite stripes
        ab_pts = [rot(-4, -6), rot(-18, -4), rot(-22, 0), rot(-18, 4), rot(-4, 6)]
        pygame.draw.polygon(self.screen, (42, 50, 64), ab_pts)
        pygame.draw.polygon(self.screen, (75, 90, 115), ab_pts, width=1)
        # Tergite segments
        pygame.draw.line(self.screen, (65, 78, 100), rot(-9, -5), rot(-9, 5), 1)
        pygame.draw.line(self.screen, (65, 78, 100), rot(-14, -4), rot(-14, 4), 1)

        # Thorax (Metallic slate)
        th_pts = [rot(6, -5), rot(6, 5), rot(-4, 6), rot(-4, -5)]
        pygame.draw.polygon(self.screen, (58, 72, 92), th_pts)
        pygame.draw.polygon(self.screen, (115, 138, 170), th_pts, width=1)

        # Head & glowing red compound eyes
        head_c = rot(10, 0)
        pygame.draw.circle(self.screen, (52, 62, 78), head_c, 6)
        eye_l = rot(11, -4)
        eye_r = rot(11, 4)
        self.draw_glow(eye_l[0], eye_l[1], (255, 50, 50), 8)
        self.draw_glow(eye_r[0], eye_r[1], (255, 50, 50), 8)
        pygame.draw.circle(self.screen, (235, 45, 45), eye_l, 3)
        pygame.draw.circle(self.screen, (235, 45, 45), eye_r, 3)
        pygame.draw.circle(self.screen, (255, 200, 200), (eye_l[0] - 1, eye_l[1] - 1), 1)
        pygame.draw.circle(self.screen, (255, 200, 200), (eye_r[0] - 1, eye_r[1] - 1), 1)

        # Antennae
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, rot(13, -2), rot(18, -6), 1)
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, rot(13, 2), rot(18, 6), 1)

    def _render_panel_neural(
        self,
        circuit: DualRingAttractor,
        agent: FlyAgent,
        food_system: Optional[FoodSystem] = None,
        mode: str = "MANUAL",
    ):
        """Renders Panel 2 with scientifically accurate text and clean vertical partitioning."""
        rx, ry, rw, rh = PANEL_NEURAL_RECT
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, PANEL_NEURAL_RECT, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, PANEL_NEURAL_RECT, width=1, border_radius=6)

        # Corner ticks
        tick_len = 10
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, (rx, ry), (rx + tick_len, ry), 2)
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, (rx, ry), (rx, ry + tick_len), 2)
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, (rx + rw - 1, ry), (rx + rw - 1 - tick_len, ry), 2)
        pygame.draw.line(self.screen, COLOR_EPG_CYAN, (rx + rw - 1, ry), (rx + rw - 1, ry + tick_len), 2)

        # Scientifically accurate header text
        header_y = ry + 8
        lbl_badge = self.font_tiny.render("CENTRAL COMPLEX NAVIGATION SUBNETWORK", True, COLOR_EPG_CYAN)
        self.screen.blit(lbl_badge, (rx + 16, header_y))

        lbl_count = self.font_hero.render("122 Biological Neurons", True, (255, 255, 255))
        self.screen.blit(lbl_count, (rx + 16, header_y + 16))

        lbl_desc = self.font_sub.render("48 E-PG Compass ⇄ 48 P-EN Shifters + 24 PFL3 Comparators (2.09x Torque)", True, (195, 210, 230))
        self.screen.blit(lbl_desc, (rx + 16, header_y + 40))

        lbl_context = self.font_tiny.render("(Modeled biological subnetwork extracted from 165,000 whole-brain connectome)", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl_context, (rx + 16, header_y + 58))

        # View mode selector buttons (Positioned cleanly on the right with zero overlap)
        for m_id, btn_rect, m_label in self.mode_buttons:
            is_active = (self.view_mode == m_id)
            bg_col = (18, 52, 64) if is_active else (18, 24, 34)
            border_col = COLOR_EPG_CYAN if is_active else (38, 50, 72)
            border_w = 2 if is_active else 1
            pygame.draw.rect(self.screen, bg_col, btn_rect, border_radius=4)
            pygame.draw.rect(self.screen, border_col, btn_rect, width=border_w, border_radius=4)

            text_col = COLOR_EPG_CYAN if is_active else (140, 160, 185)
            t_surf = self.font_mono_bold.render(m_label, True, text_col)
            self.screen.blit(t_surf, (btn_rect.x + (btn_rect.w - t_surf.get_width()) // 2, btn_rect.y + 4))

        # Render content based on mode
        if self.view_mode == 1:
            # Full 3D Brain Mesh Mode (Fills panel with rich high-definition connectome)
            center_x = rx + rw // 2
            center_y = ry + rh // 2 + 10
            self._render_brain_cloud(
                center_x,
                center_y,
                scale=2.35 * self.brain_cloud.user_scale,
                is_full_view=True,
                circuit=circuit,
                agent=agent,
                food_system=food_system,
            )
            self._render_activity_legend(rx + 24, ry + rh - 38)
            self._render_camera_hud(rx + 280, ry + rh - 38)

        elif self.view_mode == 2:
            # Full Dual Ring Attractor Mode
            center_x = rx + rw // 2
            center_y = ry + rh // 2 + 10
            self._render_dual_ring(circuit, center_x, center_y, scale=1.0)
            self._render_spectrum_bar(circuit, rx + 24, ry + rh - 110, rw - 48, 75)

        else:
            # Mode 3: SPLIT VIEW (Clean vertical partitioning)
            self._render_split_view(circuit, agent, food_system, rx, ry, rw, rh)

    def _render_split_view(
        self,
        circuit: DualRingAttractor,
        agent: FlyAgent,
        food_system: Optional[FoodSystem],
        rx: int,
        ry: int,
        rw: int,
        rh: int,
    ):
        """
        Renders clean vertically partitioned split view:
          - Upper box: 3D Anatomical Brain & VNC Activity Map (Strictly clipped)
          - Lower box: E-PG ⇄ P-EN Dual-Ring Attractor with 2.09x torque arcs
        """
        prev_clip = self.screen.get_clip()

        # ======================================================================
        # 1. UPPER SECTION: 3D Anatomical Brain (y: 126 to 466, height: 340px)
        # ======================================================================
        upper_box = pygame.Rect(rx + 12, ry + 76, rw - 24, 340)
        pygame.draw.rect(self.screen, (14, 18, 26), upper_box, border_radius=5)
        pygame.draw.rect(self.screen, (28, 38, 54), upper_box, width=1, border_radius=5)

        # Upper section header
        lbl_sec1 = self.font_tiny.render("ANATOMICAL BRAIN MESH: 1,920 CONNECTOME NODES & VNC (0–200+ Hz)", True, (160, 180, 205))
        self.screen.blit(lbl_sec1, (rx + 22, ry + 84))

        # Strict clipping for upper 3D brain
        clip_upper = pygame.Rect(rx + 14, ry + 78, rw - 28, 336)
        self.screen.set_clip(clip_upper)

        # Center and project 3D brain with proportional scale (stays strictly inside upper box)
        cloud_cx = rx + rw // 2
        cloud_cy = ry + 240
        self._render_brain_cloud(
            cloud_cx,
            cloud_cy,
            scale=1.52 * self.brain_cloud.user_scale,
            is_full_view=False,
            circuit=circuit,
            agent=agent,
            food_system=food_system,
        )

        # Anatomical Callout Badges
        lbl_opt_l = self.font_tiny.render("[OPTIC L]", True, (130, 150, 175))
        lbl_opt_r = self.font_tiny.render("[OPTIC R]", True, (130, 150, 175))
        lbl_cx = self.font_tiny.render("[CENTRAL COMPLEX (EB/PB)]", True, COLOR_EPG_CYAN)
        lbl_vnc = self.font_tiny.render("[VNC MOTOR CORD (T1-T3)]", True, (140, 170, 200))

        self.screen.blit(lbl_opt_l, (cloud_cx - 200, cloud_cy - 48))
        self.screen.blit(lbl_opt_r, (cloud_cx + 145, cloud_cy - 48))
        self.screen.blit(lbl_cx, (cloud_cx - lbl_cx.get_width() // 2, cloud_cy - 105))
        self.screen.blit(lbl_vnc, (cloud_cx - lbl_vnc.get_width() // 2, cloud_cy + 112))

        # Bottom activity legend inside upper box
        self._render_activity_legend(rx + 22, ry + 386)

        # Reset clip
        self.screen.set_clip(prev_clip)

        # Divider bar
        div_y = ry + 424
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (rx + 12, div_y), (rx + rw - 12, div_y), 1)

        # ======================================================================
        # 2. LOWER SECTION: Dual-Ring CANN (y: 432 to 836, height: 404px)
        # ======================================================================
        lower_box = pygame.Rect(rx + 12, div_y + 8, rw - 24, rh - (div_y - ry) - 16)
        pygame.draw.rect(self.screen, (14, 18, 26), lower_box, border_radius=5)
        pygame.draw.rect(self.screen, (28, 38, 54), lower_box, width=1, border_radius=5)

        # Lower section header
        lbl_sec2 = self.font_tiny.render("LIVE CANN DYNAMICS: 50 E-PG COMPASS ⇄ 48 P-EN SHIFTERS (2.09x TORQUE)", True, (160, 180, 205))
        self.screen.blit(lbl_sec2, (rx + 22, div_y + 14))

        # Clip for lower section
        clip_lower = pygame.Rect(rx + 14, div_y + 10, rw - 28, lower_box.height - 4)
        self.screen.set_clip(clip_lower)

        # Center of Dual Ring in lower section with balanced margins
        ring_cx = rx + rw // 2
        ring_cy = div_y + 158
        self._render_dual_ring(circuit, ring_cx, ring_cy, scale=0.58, legend_y=div_y + 306)

        self.screen.set_clip(prev_clip)

    def _render_brain_cloud(
        self,
        cx: float,
        cy: float,
        scale: float,
        is_full_view: bool = False,
        circuit: Optional[DualRingAttractor] = None,
        agent: Optional[FlyAgent] = None,
        food_system: Optional[FoodSystem] = None,
    ):
        """Projects and renders the 3D anatomical Drosophila brain & VNC with live bioluminescence, structural tracts, and pulses."""
        valid_nodes, proj_edges, anchors, proj_pulses = self.brain_cloud.project_and_depth_sort(cx, cy, scale=scale)

        # 1. Structural Connectome Tracts (Axons & Dendrites)
        for e in proj_edges:
            x1, y1 = int(e["x1"]), int(e["y1"])
            x2, y2 = int(e["x2"]), int(e["y2"])
            if abs(x1 - x2) > 380 or abs(y1 - y2) > 380:
                continue

            etype = e["type"]
            hz = e["hz"]
            ecol = e["color"]

            if etype.startswith("PFL3_L") or etype.startswith("PFL3_R"):
                w = 2 if (hz > 45.0 and is_full_view) else 1
                pygame.draw.line(self.screen, ecol, (x1, y1), (x2, y2), w)
            elif etype in ("EB_RING", "EPG_PB", "VNC_CORD"):
                w = 2 if (hz > 90.0 and is_full_view) else 1
                pygame.draw.line(self.screen, ecol, (x1, y1), (x2, y2), w)
            else:
                pygame.draw.line(self.screen, ecol, (x1, y1), (x2, y2), 1)

        # 2. Synaptic Action Potential Pulses
        for p in proj_pulses:
            px, py = int(p["x"]), int(p["y"])
            pcol = p["color"]
            glow_r = 8 if is_full_view else 6
            self.draw_glow(px, py, pcol, glow_r)
            pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 2)
            pygame.draw.circle(self.screen, pcol, (px, py), 3, width=1)

        # 3. Neural Nodes with Clean Visual Hierarchy
        for n in valid_nodes:
            sx, sy = int(n["sx"]), int(n["sy"])
            color = n["color"]
            hz = n["hz"]
            is_cx = n["is_cx"]
            is_cord = n.get("is_cord", False)
            is_scaffold = n.get("is_scaffold", False)

            if is_scaffold:
                # Translucent anatomical scaffold envelope (1px fine point, no bloom)
                pygame.draw.circle(self.screen, color, (sx, sy), 1)
                continue

            # Functional Circuit Nodes (Central Complex & Descending Motor Cords)
            if is_full_view:
                if hz < 35.0:
                    rad = 1.7
                elif hz < 85.0:
                    rad = 2.1
                    self.draw_glow(sx, sy, color, 4)
                elif hz < 140.0:
                    rad = 2.5
                    self.draw_glow(sx, sy, color, 6)
                else:
                    rad = 2.9
                    self.draw_glow(sx, sy, color, 8)
            else:
                if hz < 35.0:
                    rad = 1.2
                elif hz < 85.0:
                    rad = 1.6
                elif hz < 140.0:
                    rad = 2.0
                    self.draw_glow(sx, sy, color, 4)
                else:
                    rad = 2.4
                    self.draw_glow(sx, sy, color, 6)

            pygame.draw.circle(self.screen, color, (sx, sy), int(rad))

            # Specular pinpoint core for high-frequency bursting neurons
            if hz > 110.0:
                core_r = 1
                pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), core_r)

        # 4. Floating 3D Anatomical Callout Badges
        if is_full_view and circuit is not None and agent is not None:
            self._render_3d_callout_labels(anchors, circuit, agent, food_system)

    def _render_3d_callout_labels(
        self,
        anchors: Dict[str, Tuple[float, float]],
        circuit: DualRingAttractor,
        agent: FlyAgent,
        food_system: Optional[FoodSystem] = None,
    ):
        """Renders sleek floating 3D HUD callout cards docked cleanly along outer side rails with zero overlap."""
        if not self.show_callouts:
            return

        rx, ry, rw, rh = PANEL_NEURAL_RECT
        odor = food_system.get_odor_at(agent.x, agent.y, agent.heading) if food_system else None

        bump_deg = math.degrees(circuit.decode_heading()[0])
        act_l, act_r = circuit.get_shifter_activities()
        pfl3_l, pfl3_r = circuit.get_pfl3_activities() if hasattr(circuit, "get_pfl3_activities") else (0.0, 0.0)
        pfl3_bias = circuit.get_pfl3_directional_bias() if hasattr(circuit, "get_pfl3_directional_bias") else 0.0
        odor_deg = math.degrees(odor.relative_bearing) if odor else 0.0
        odor_pct = (odor.strength * 100.0) if odor else 0.0

        # Structured into Left Rail and Right Rail with dedicated vertical slots aligned with brain anatomy
        left_defs = [
            (
                "PB_L",
                "[PB] PROTOCEREBRAL BRIDGE",
                f"Shifters L:{act_l:.1f} R:{act_r:.1f} | 2.09x Torque",
                COLOR_PEN_LEFT,
                ry + 175,
            ),
            (
                "AL_L",
                "[AL] ANTENNAL LOBES",
                f"Olfactory | {odor_pct:.0f}% Scent Field",
                (80, 230, 120),
                ry + 295,
            ),
            (
                "LAL_L",
                "[LAL] MOTOR STEERING HUBS",
                f"Bias: {pfl3_bias:+.2f} | 24 PFL3 Axons",
                COLOR_PFL3_LEFT if pfl3_bias <= 0 else COLOR_PFL3_RIGHT,
                ry + 415,
            ),
        ]

        right_defs = [
            (
                "EB",
                "[EB] ELLIPSOID BODY",
                f"Heading: {bump_deg:+.0f}° | 48 E-PG Wedges",
                COLOR_EPG_CYAN,
                ry + 175,
            ),
            (
                "FB",
                "[FB] FAN-SHAPED BODY",
                f"9-Col Grid | Ψ:{odor_deg:+.0f}° Odor Goal",
                (50, 245, 140),
                ry + 295,
            ),
            (
                "VNC_T2",
                "[VNC] VENTRAL NERVE CORD",
                f"T1-T3 Neuromeres | {agent.v:.0f} px/s",
                (175, 215, 255),
                ry + 415,
            ),
        ]

        bw = 196
        bh = 34

        # Render Left Badges (Docked along left margin: rx + 16 to rx + 16 + bw)
        bx_l = rx + 16
        for akey, title, subtitle, col, slot_y in left_defs:
            if akey not in anchors:
                continue
            ax, ay = anchors[akey]
            by = slot_y
            pin_x = bx_l + bw
            pin_y = by + bh // 2

            # Target dot on 3D structure
            pygame.draw.circle(self.screen, col, (int(ax), int(ay)), 3)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(ax), int(ay)), 1)

            # Elegant leader line: anchor -> elbow -> pin
            elbow_x = min(ax - 10, pin_x + (ax - pin_x) * 0.45)
            line_col = (col[0] // 2, col[1] // 2, col[2] // 2)
            pygame.draw.line(self.screen, line_col, (int(ax), int(ay)), (int(elbow_x), int(pin_y)), 1)
            pygame.draw.line(self.screen, line_col, (int(elbow_x), int(pin_y)), (int(pin_x), int(pin_y)), 1)
            pygame.draw.circle(self.screen, col, (int(pin_x), int(pin_y)), 2)

            # Sleek translucent badge
            b_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(b_surf, (12, 17, 26, 225), (0, 0, bw, bh), border_radius=4)
            pygame.draw.rect(b_surf, (col[0], col[1], col[2], 140), (0, 0, bw, bh), width=1, border_radius=4)
            pygame.draw.rect(b_surf, col, (0, 0, 3, bh), border_top_left_radius=4, border_bottom_left_radius=4)
            self.screen.blit(b_surf, (int(bx_l), int(by)))

            t_surf = self.font_tiny.render(title, True, col)
            s_surf = self.font_tiny.render(subtitle, True, (165, 185, 210))
            self.screen.blit(t_surf, (int(bx_l + 8), int(by + 4)))
            self.screen.blit(s_surf, (int(bx_l + 8), int(by + 17)))

        # Render Right Badges (Docked along right margin: rx + rw - bw - 16)
        bx_r = rx + rw - bw - 16
        for akey, title, subtitle, col, slot_y in right_defs:
            if akey not in anchors:
                continue
            ax, ay = anchors[akey]
            by = slot_y
            pin_x = bx_r
            pin_y = by + bh // 2

            # Target dot on 3D structure
            pygame.draw.circle(self.screen, col, (int(ax), int(ay)), 3)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(ax), int(ay)), 1)

            # Elegant leader line: anchor -> elbow -> pin
            elbow_x = max(ax + 10, pin_x - (pin_x - ax) * 0.45)
            line_col = (col[0] // 2, col[1] // 2, col[2] // 2)
            pygame.draw.line(self.screen, line_col, (int(ax), int(ay)), (int(elbow_x), int(pin_y)), 1)
            pygame.draw.line(self.screen, line_col, (int(elbow_x), int(pin_y)), (int(pin_x), int(pin_y)), 1)
            pygame.draw.circle(self.screen, col, (int(pin_x), int(pin_y)), 2)

            # Sleek translucent badge
            b_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(b_surf, (12, 17, 26, 225), (0, 0, bw, bh), border_radius=4)
            pygame.draw.rect(b_surf, (col[0], col[1], col[2], 140), (0, 0, bw, bh), width=1, border_radius=4)
            pygame.draw.rect(b_surf, col, (bw - 3, 0, 3, bh), border_top_right_radius=4, border_bottom_right_radius=4)
            self.screen.blit(b_surf, (int(bx_r), int(by)))

            t_surf = self.font_tiny.render(title, True, col)
            s_surf = self.font_tiny.render(subtitle, True, (165, 185, 210))
            self.screen.blit(t_surf, (int(bx_r + 7), int(by + 4)))
            self.screen.blit(s_surf, (int(bx_r + 7), int(by + 17)))

    def _render_camera_hud(self, x: int, y: int):
        """Draws interactive camera view hints and orbital angle readouts."""
        yaw_deg = math.degrees(self.brain_cloud.yaw) % 360
        pitch_deg = math.degrees(self.brain_cloud.pitch)
        zoom = self.brain_cloud.user_scale
        lbl_status = "ON" if self.show_callouts else "OFF"
        text = f"3D CAMERA: [DRAG] Orbit ({yaw_deg:.0f}°, {pitch_deg:.0f}°) | [SCROLL] Zoom ({zoom:.1f}x) | [L] Badges ({lbl_status}) | [R-CLICK] Reset"
        txt_surf = self.font_tiny.render(text, True, COLOR_TEXT_MUTED)
        self.screen.blit(txt_surf, (x, y + 2))


    def _render_activity_legend(self, x: int, y: int):
        """Draws activity colorbar matching screenshot with clear Hz ticks."""
        lbl = self.font_tiny.render("Activity: 0 Hz (Resting) ── 100 Hz ── 200+ Hz (Max)", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl, (x, y))

        bar_w = 140
        bar_h = 5
        bar_y = y + 14
        for i in range(bar_w):
            f = i / bar_w
            if f < 0.25:
                col = (32 + int(f * 96), 44 + int(f * 136), 62 + int(f * 168))
            elif f < 0.65:
                col = (0, 200 + int((f - 0.25) * 120), 220)
            else:
                col = (255, 160 + int((f - 0.65) * 230), 120 + int((f - 0.65) * 280))
            pygame.draw.line(self.screen, col, (x + i, bar_y), (x + i, bar_y + bar_h), 1)

    def _render_dual_ring(self, circuit: DualRingAttractor, cx: float, cy: float, scale: float = 1.0, legend_y: Optional[int] = None):
        """Renders inner E-PG compass with 16-wedge spokes, outer P-EN shifter rings, and high-fidelity compass needle."""
        r_epg = RADIUS_EPG * scale
        r_pen = RADIUS_PEN * scale

        # Guide rings (Outer PB ring + Inner EB donut walls)
        pygame.draw.circle(self.screen, (22, 30, 46), (int(cx), int(cy)), int(r_pen), width=1)
        pygame.draw.circle(self.screen, (28, 40, 60), (int(cx), int(cy)), int(r_epg - 14 * scale), width=1)
        pygame.draw.circle(self.screen, (28, 40, 60), (int(cx), int(cy)), int(r_epg + 14 * scale), width=1)

        # 16 Anatomical Wedge Spokes of the Ellipsoid Body (EB Donut)
        for w_idx in range(16):
            w_ang = w_idx * (2.0 * math.pi / 16.0)
            wx1 = cx + (r_epg - 14 * scale) * math.cos(w_ang)
            wy1 = cy + (r_epg - 14 * scale) * math.sin(w_ang)
            wx2 = cx + (r_epg + 14 * scale) * math.cos(w_ang)
            wy2 = cy + (r_epg + 14 * scale) * math.sin(w_ang)
            pygame.draw.line(self.screen, (24, 34, 50), (int(wx1), int(wy1)), (int(wx2), int(wy2)), 1)

        # Cardinal ticks
        cardinals = [(0.0, "0°"), (math.pi / 2, "90°"), (math.pi, "180°"), (3 * math.pi / 2, "270°")]
        for ang, label in cardinals:
            tx = cx + (r_pen + 12 * scale) * math.cos(ang)
            ty = cy + (r_pen + 12 * scale) * math.sin(ang)
            t_s = self.font_tiny.render(label, True, COLOR_TEXT_MUTED)
            self.screen.blit(t_s, (int(tx - t_s.get_width() / 2), int(ty - t_s.get_height() / 2)))

        # Synaptic torque arcs (P-EN -> E-PG feedback)
        active_arcs = circuit.get_active_synaptic_arcs(threshold_ratio=0.30)
        arc_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        for arc_type, pen_idx, pen_ang, epg_idx, epg_ang, intensity in active_arcs:
            px = cx + r_pen * math.cos(pen_ang)
            py = cy + r_pen * math.sin(pen_ang)
            ex = cx + r_epg * math.cos(epg_ang)
            ey = cy + r_epg * math.sin(epg_ang)

            mid_ang = (pen_ang + epg_ang) / 2.0
            mid_r = (r_pen + r_epg) * 0.48
            ctrl_x = cx + mid_r * math.cos(mid_ang)
            ctrl_y = cy + mid_r * math.sin(mid_ang)

            points = []
            steps = 8
            for si in range(steps + 1):
                t = si / steps
                bx = (1 - t)**2 * px + 2 * (1 - t) * t * ctrl_x + t**2 * ex
                by = (1 - t)**2 * py + 2 * (1 - t) * t * ctrl_y + t**2 * ey
                points.append((int(bx), int(by)))

            alpha = int(220 * intensity)
            arc_col = (*COLOR_LIME_FEEDBACK, alpha)
            if len(points) >= 2:
                pygame.draw.lines(arc_surf, arc_col, False, points, 2 if intensity > 0.6 else 1)

            # Traveling neurotransmission spark dot
            spark_t = (self.anim_time * 3.5 + pen_idx * 0.2) % 1.0
            spark_x = (1 - spark_t)**2 * px + 2 * (1 - spark_t) * spark_t * ctrl_x + spark_t**2 * ex
            spark_y = (1 - spark_t)**2 * py + 2 * (1 - spark_t) * spark_t * ctrl_y + spark_t**2 * ey
            pygame.draw.circle(arc_surf, (255, 255, 255, int(240 * intensity)), (int(spark_x), int(spark_y)), 2)

        self.screen.blit(arc_surf, (0, 0), special_flags=pygame.BLEND_ADD)

        # Outer Ring: P-EN Shifters (Magenta)
        max_pen_l = float(np.max(circuit.r_pen_l)) if len(circuit.r_pen_l) else 0.0
        max_pen_r = float(np.max(circuit.r_pen_r)) if len(circuit.r_pen_r) else 0.0

        for i, ang in enumerate(circuit.theta_pen_l):
            rate = float(circuit.r_pen_l[i])
            nx = cx + r_pen * math.cos(ang)
            ny = cy + r_pen * math.sin(ang)
            node_r = (2.5 + min(4.5, (rate / (max_pen_l + 1e-4)) * 4.0)) * scale
            col = COLOR_PEN_LEFT
            if rate > 0.8:
                self.draw_glow(nx, ny, col, int(node_r * 2.5))
            pygame.draw.circle(self.screen, col, (int(nx), int(ny)), max(2, int(node_r)))

        for i, ang in enumerate(circuit.theta_pen_r):
            rate = float(circuit.r_pen_r[i])
            nx = cx + r_pen * math.cos(ang)
            ny = cy + r_pen * math.sin(ang)
            node_r = (2.5 + min(4.5, (rate / (max_pen_r + 1e-4)) * 4.0)) * scale
            col = COLOR_PEN_RIGHT
            if rate > 0.8:
                self.draw_glow(nx, ny, col, int(node_r * 2.5))
            pygame.draw.circle(self.screen, col, (int(nx), int(ny)), max(2, int(node_r)))

        # Inner Ring: E-PG Compass Neurons (Cyan)
        max_epg = float(np.max(circuit.r_epg)) if len(circuit.r_epg) else 1.0
        for i, ang in enumerate(circuit.theta_epg):
            rate = float(circuit.r_epg[i])
            nx = cx + r_epg * math.cos(ang)
            ny = cy + r_epg * math.sin(ang)
            norm_rate = rate / max_epg
            node_r = (2.5 + norm_rate * 5.5) * scale
            if norm_rate > 0.35:
                self.draw_glow(nx, ny, COLOR_EPG_CYAN, int(node_r * 2.6))
            pygame.draw.circle(self.screen, COLOR_EPG_CYAN, (int(nx), int(ny)), max(2, int(node_r)))

        # High-Fidelity Decoded Heading Needle with Arrowhead & Pivot Hub
        decoded_h, amp, coh = circuit.decode_heading()
        needle_len = r_epg + 16.0 * scale
        nd_x = cx + needle_len * math.cos(decoded_h)
        nd_y = cy + needle_len * math.sin(decoded_h)

        # Shaft
        pygame.draw.line(self.screen, (255, 255, 255), (int(cx), int(cy)), (int(nd_x), int(nd_y)), 2)

        # Center Pivot Hub
        pygame.draw.circle(self.screen, (16, 22, 32), (int(cx), int(cy)), int(7 * scale))
        pygame.draw.circle(self.screen, COLOR_EPG_CYAN, (int(cx), int(cy)), int(7 * scale), width=1)
        pygame.draw.circle(self.screen, (255, 255, 255), (int(cx), int(cy)), max(2, int(3 * scale)))

        # Arrowhead pointer at tip
        arr_size = 9.0 * scale
        tip_ang = decoded_h
        arr_p1 = (int(nd_x + arr_size * math.cos(tip_ang)), int(nd_y + arr_size * math.sin(tip_ang)))
        arr_p2 = (int(nd_x + arr_size * 0.7 * math.cos(tip_ang + 2.5)), int(nd_y + arr_size * 0.7 * math.sin(tip_ang + 2.5)))
        arr_p3 = (int(nd_x + arr_size * 0.7 * math.cos(tip_ang - 2.5)), int(nd_y + arr_size * 0.7 * math.sin(tip_ang - 2.5)))
        pygame.draw.polygon(self.screen, COLOR_EPG_CYAN, [arr_p1, arr_p2, arr_p3])
        pygame.draw.polygon(self.screen, (255, 255, 255), [arr_p1, arr_p2, arr_p3], width=1)
        self.draw_glow(arr_p1[0], arr_p1[1], COLOR_EPG_CYAN, int(14 * scale))

        # Bottom Legend (Badged Pill Bar)
        if legend_y is not None:
            leg_y = legend_y
        else:
            leg_y = int(cy + r_pen + 18 * scale)

        items = [
            (COLOR_EPG_CYAN, "● E-PG Compass (EB)"),
            (COLOR_PEN_LEFT, "● P-EN Left"),
            (COLOR_PEN_RIGHT, "● P-EN Right"),
            (COLOR_LIME_FEEDBACK, "⚡ 2.09x Torque Feedback"),
        ]
        total_w = sum(self.font_tiny.size(t)[0] + 16 for _, t in items)
        lx = int(cx - total_w // 2)

        leg_bg = pygame.Rect(lx - 8, leg_y - 2, int(total_w) + 8, 18)
        pygame.draw.rect(self.screen, (16, 22, 32), leg_bg, border_radius=4)
        pygame.draw.rect(self.screen, (28, 38, 54), leg_bg, width=1, border_radius=4)

        for col, text in items:
            s = self.font_tiny.render(text, True, col)
            self.screen.blit(s, (lx + 2, leg_y + 2))
            lx += s.get_width() + 16

    def _render_spectrum_bar(self, circuit: DualRingAttractor, x: int, y: int, w: int, h: int):
        """Draws 48-bar live E-PG firing spectrum."""
        pygame.draw.rect(self.screen, COLOR_GAUGE_BG, (x, y, w, h), border_radius=4)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, (x, y, w, h), width=1, border_radius=4)

        max_val = max(1.0, float(np.max(circuit.r_epg)))
        n_bars = len(circuit.r_epg)
        bar_w = (w - 8) / n_bars

        for bi, r_val in enumerate(circuit.r_epg):
            bar_h = (r_val / max_val) * (h - 10)
            bx = x + 4 + bi * bar_w
            by = y + h - 4 - bar_h
            is_peak = (r_val == max_val and max_val > 1.0)
            b_col = (255, 255, 255) if is_peak else COLOR_EPG_CYAN
            pygame.draw.rect(self.screen, b_col, (int(bx), int(by), max(1, int(bar_w - 1)), int(bar_h)))

    def _render_stats_hud(
        self,
        circuit: DualRingAttractor,
        agent: FlyAgent,
        food_system: Optional[FoodSystem] = None,
        mode: str = "MANUAL",
    ):
        """Draws compact, floating avionics stats HUD card with responsive placement."""
        hud_box = self.get_hud_rect()
        if hud_box is None:
            return  # HUD is toggled to Hidden

        rx, ry, rw, rh = hud_box

        hud_surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
        pygame.draw.rect(hud_surf, (12, 16, 25, 235), (0, 0, rw, rh), border_radius=6)
        mode_border_col = COLOR_EPG_CYAN if mode == "MANUAL" else COLOR_FOOD_EMERALD
        pygame.draw.rect(hud_surf, mode_border_col, (0, 0, rw, rh), width=1, border_radius=6)

        # Micro header: Left title, Right mode badge
        hdr_surf = self.font_tiny.render("AVIONICS TELEMETRY", True, COLOR_EPG_CYAN)
        hud_surf.blit(hdr_surf, (12, 5))

        mode_txt = self.font_mono_bold.render(f"[{mode}]", True, mode_border_col)
        hud_surf.blit(mode_txt, (rw - mode_txt.get_width() - 12, 4))
        pygame.draw.line(hud_surf, (30, 44, 62), (10, 19), (rw - 10, 19), 1)

        # 1. Heading Display
        decoded_h, amp, coh = circuit.decode_heading()
        deg_h = (math.degrees(decoded_h) + 360.0) % 360.0
        cardinals = ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]
        cardinal = cardinals[int(((deg_h + 22.5) % 360.0) // 45.0)]

        h_str = f"θ: {deg_h:5.1f}° {cardinal}"
        h_surf = self.font_big_digit.render(h_str, True, COLOR_EPG_CYAN)
        hud_surf.blit(h_surf, (12, 22))

        # 2. Speed & Stability Row
        sp_str = f"SPEED: {agent.v:3.0f} px/s"
        sp_surf = self.font_mono.render(sp_str, True, COLOR_TEXT_PRIMARY)
        hud_surf.blit(sp_surf, (12, 44))

        coh_clamped = max(0.0, min(1.0, coh))
        pygame.draw.rect(hud_surf, (24, 34, 48), (145, 47, 92, 9), border_radius=3)
        pygame.draw.rect(hud_surf, COLOR_EPG_CYAN, (145, 47, int(92 * coh_clamped), 9), border_radius=3)
        coh_txt = self.font_tiny.render(f"C:{coh*100:.0f}%", True, (255, 255, 255))
        hud_surf.blit(coh_txt, (182, 45))

        # 3. P-EN Shifter rates & Differential Steering Gauge
        act_l, act_r = circuit.get_shifter_activities()
        sh_str = f"P-EN: L{act_l:3.1f} | R{act_r:3.1f}"
        sh_surf = self.font_mono.render(sh_str, True, COLOR_PEN_LEFT)
        hud_surf.blit(sh_surf, (12, 62))

        bar_cx = 191
        bar_y = 67
        pygame.draw.line(hud_surf, (50, 64, 86), (145, bar_y + 3), (237, bar_y + 3), 1)
        pygame.draw.line(hud_surf, (255, 255, 255), (bar_cx, bar_y), (bar_cx, bar_y + 6), 1)
        pen_diff = (act_r - act_l) / 30.0
        pen_diff = max(-1.0, min(1.0, pen_diff))
        if pen_diff < 0:
            pygame.draw.rect(hud_surf, COLOR_PEN_LEFT, (int(bar_cx + pen_diff * 42), bar_y + 1, int(-pen_diff * 42), 5), border_radius=2)
        elif pen_diff > 0:
            pygame.draw.rect(hud_surf, COLOR_PEN_RIGHT, (bar_cx, bar_y + 1, int(pen_diff * 42), 5), border_radius=2)

        # 4. PFL3 Decision Neurons & Directional Steering Bias
        pfl3_l, pfl3_r = circuit.get_pfl3_activities()
        pfl3_str = f"PFL3: L{pfl3_l:3.1f} | R{pfl3_r:3.1f}"
        pfl3_surf = self.font_mono.render(pfl3_str, True, COLOR_PFL3_LEFT)
        hud_surf.blit(pfl3_surf, (12, 80))

        bar3_y = 85
        pygame.draw.line(hud_surf, (50, 64, 86), (145, bar3_y + 3), (237, bar3_y + 3), 1)
        pygame.draw.line(hud_surf, (255, 255, 255), (bar_cx, bar3_y), (bar_cx, bar3_y + 6), 1)
        pfl3_bias = circuit.get_pfl3_directional_bias()
        if pfl3_bias < 0:
            pygame.draw.rect(hud_surf, COLOR_PFL3_LEFT, (int(bar_cx + pfl3_bias * 42), bar3_y + 1, int(-pfl3_bias * 42), 5), border_radius=2)
        elif pfl3_bias > 0:
            pygame.draw.rect(hud_surf, COLOR_PFL3_RIGHT, (bar_cx, bar3_y + 1, int(pfl3_bias * 42), 5), border_radius=2)

        # 5. Food Score & Energy Bar Row
        sc_str = f"FOOD: {agent.score:2d}"
        sc_surf = self.font_mono_bold.render(sc_str, True, COLOR_FOOD_EMERALD)
        hud_surf.blit(sc_surf, (12, 100))

        # Energy bar
        en_frac = max(0.0, min(1.0, agent.energy / agent.max_energy))
        en_col = COLOR_FOOD_EMERALD if en_frac > 0.3 else (255, 140, 50)
        pygame.draw.rect(hud_surf, (24, 34, 48), (120, 103, 117, 9), border_radius=3)
        pygame.draw.rect(hud_surf, en_col, (120, 103, int(117 * en_frac), 9), border_radius=3)
        en_txt = self.font_tiny.render(f"NRG:{int(agent.energy)}%", True, (255, 255, 255))
        hud_surf.blit(en_txt, (155, 101))

        # 6. Odor Sensation Row
        if food_system is not None:
            odor = food_system.get_odor_at(agent.x, agent.y, agent.heading)
            od_bearing_deg = math.degrees(odor.relative_bearing)
            od_str = f"ODOR: {int(odor.strength * 100):2d}% | Ψ:{od_bearing_deg:+.0f}°"
            od_col = COLOR_FOOD_EMERALD if odor.strength > 0.25 else COLOR_TEXT_SECONDARY
            od_surf = self.font_mono.render(od_str, True, od_col)
            hud_surf.blit(od_surf, (12, 120))

            dist_str = f"d:{int(odor.nearest_dist)}px"
            dist_surf = self.font_tiny.render(dist_str, True, COLOR_TEXT_MUTED)
            hud_surf.blit(dist_surf, (rw - dist_surf.get_width() - 12, 121))
        else:
            od_surf = self.font_mono.render("ODOR: NO SENSOR", True, COLOR_TEXT_MUTED)
            hud_surf.blit(od_surf, (12, 120))

        # 7. Sun Landmark Status Row
        mark_bearing = agent.get_landmark_bearing()
        if agent.landmark_active and mark_bearing is not None:
            deg_bearing = math.degrees(mark_bearing)
            sign = "+" if deg_bearing >= 0 else ""
            sun_str = f"SUN: BEARING {sign}{deg_bearing:.0f}°"
            sun_col = COLOR_SUN_AMBER
        elif agent.landmark_x is not None:
            sun_str = "SUN: OFF (R-Click to arm)"
            sun_col = COLOR_TEXT_MUTED
        else:
            sun_str = "SUN: NONE (Click arena)"
            sun_col = COLOR_TEXT_MUTED

        sun_surf = self.font_tiny.render(sun_str, True, sun_col)
        hud_surf.blit(sun_surf, (12, 140))

        # 8. Biological Torque & Autopilot Status
        ratio_surf = self.font_tiny.render("2.09x TORQUE", True, COLOR_LIME_FEEDBACK)
        hud_surf.blit(ratio_surf, (12, 161))

        autopilot_txt = "AUTOPILOT: ON" if mode == "AUTO" else "AUTOPILOT: OFF"
        autopilot_col = COLOR_FOOD_EMERALD if mode == "AUTO" else COLOR_TEXT_MUTED
        auto_surf = self.font_tiny.render(autopilot_txt, True, autopilot_col)
        hud_surf.blit(auto_surf, (rw - auto_surf.get_width() - 12, 161))

        # 9. Quick Keys Hints
        hints_surf = self.font_tiny.render("[M] Auto Mode  [H] Move HUD", True, COLOR_TEXT_MUTED)
        hud_surf.blit(hints_surf, (12, 179))

        self.screen.blit(hud_surf, (rx, ry))
