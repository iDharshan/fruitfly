"""
Configuration and parameter constants for Drosophila Closed-Loop Compass Toy.
Expanded arena layout, 3D anatomical brain point cloud, and compact stats HUD.
"""

from dataclasses import dataclass
from typing import Tuple

# ==============================================================================
# DISPLAY & WINDOW CONFIGURATION
# ==============================================================================
SCREEN_WIDTH: int = 1600
SCREEN_HEIGHT: int = 900
FPS: int = 60

WINDOW_TITLE: str = "Drosophila Central Complex Compass Simulator | RTX 4060 Accelerated"

# ==============================================================================
# COLOR PALETTE (Cyberpunk Dark Neon)
# ==============================================================================
COLOR_BG: Tuple[int, int, int] = (10, 13, 18)           # #0a0d12 Deep Obsidian
COLOR_PANEL_BG: Tuple[int, int, int] = (16, 21, 30)     # #10151e Dark Panel Surface
COLOR_PANEL_BORDER: Tuple[int, int, int] = (32, 42, 60) # #202a3c Slate Border
COLOR_PANEL_HEADER: Tuple[int, int, int] = (22, 28, 40) # Header banner background

# Functional Neural Colors
COLOR_EPG_CYAN: Tuple[int, int, int] = (0, 245, 212)    # #00f5d4 Compass Needle (E-PG)
COLOR_PEN_MAGENTA: Tuple[int, int, int] = (247, 37, 133)# #f72585 Velocity Shifter (P-EN)
COLOR_PEN_LEFT: Tuple[int, int, int] = (255, 94, 180)   # Hot Pink for Left Shifters
COLOR_PEN_RIGHT: Tuple[int, int, int] = (181, 23, 158)  # Deep Violet-Pink for Right Shifters
COLOR_GOLD_FORWARD: Tuple[int, int, int] = (255, 209, 102) # #ffd166 E-PG -> P-EN Synapses
COLOR_LIME_FEEDBACK: Tuple[int, int, int] = (112, 224, 0)  # #70e000 P-EN -> E-PG Feedback
COLOR_SUN_AMBER: Tuple[int, int, int] = (255, 183, 3)   # #ffb703 Visual Landmark Cue
COLOR_FOOD_EMERALD: Tuple[int, int, int] = (50, 235, 120)  # #32eb78 Nutrient Pellet (Food)
COLOR_FOOD_CORE: Tuple[int, int, int] = (200, 255, 220)     # Highlight core
COLOR_ODOR_AURA: Tuple[int, int, int] = (40, 210, 110)      # Scent plume aura

# UI Accents & Text
COLOR_TEXT_PRIMARY: Tuple[int, int, int] = (240, 244, 252)
COLOR_TEXT_SECONDARY: Tuple[int, int, int] = (138, 152, 178)
COLOR_TEXT_MUTED: Tuple[int, int, int] = (74, 88, 114)
COLOR_GRID: Tuple[int, int, int] = (20, 26, 38)
COLOR_GAUGE_BG: Tuple[int, int, int] = (22, 30, 44)
COLOR_ACTIVE_BORDER: Tuple[int, int, int] = (0, 245, 212)

# ==============================================================================
# UI DASHBOARD LAYOUT (Expanded Arena + Neural Section + Compact Stats HUD)
# ==============================================================================
HEADER_HEIGHT: int = 44
FOOTER_HEIGHT: int = 50
CONTENT_TOP: int = HEADER_HEIGHT + 6
CONTENT_BOTTOM: int = SCREEN_HEIGHT - FOOTER_HEIGHT - 6
CONTENT_HEIGHT: int = CONTENT_BOTTOM - CONTENT_TOP

# 2 Main Panels:
# Panel 1: 2D Fly Arena (Left - Expanded to 780px wide)
PANEL_ARENA_RECT = (14, CONTENT_TOP, 780, CONTENT_HEIGHT)

# Panel 2: Live Neural Activity & Brain View (Right - 780px wide)
PANEL_NEURAL_RECT = (806, CONTENT_TOP, 780, CONTENT_HEIGHT)

# View Mode Selector Buttons Layout (Panel 2 Header Right)
BTN_MODE_WIDTH: int = 86
BTN_MODE_HEIGHT: int = 24
BTN_MODE_SPACING: int = 6
BTN_MODES_TOTAL_W: int = 3 * BTN_MODE_WIDTH + 2 * BTN_MODE_SPACING  # 270px
BTN_MODES_X: int = PANEL_NEURAL_RECT[0] + PANEL_NEURAL_RECT[2] - BTN_MODES_TOTAL_W - 16
BTN_MODES_Y: int = CONTENT_TOP + 12

# Compact Floating Stats HUD (Placed in Flight Arena corner for clear cockpit avionics)
STATS_HUD_W: int = 250
STATS_HUD_H: int = 175
STATS_HUD_RECT_ARENA_BR = (PANEL_ARENA_RECT[0] + PANEL_ARENA_RECT[2] - STATS_HUD_W - 14,
                           PANEL_ARENA_RECT[1] + PANEL_ARENA_RECT[3] - STATS_HUD_H - 14,
                           STATS_HUD_W, STATS_HUD_H)
STATS_HUD_RECT_ARENA_TR = (PANEL_ARENA_RECT[0] + PANEL_ARENA_RECT[2] - STATS_HUD_W - 14,
                           PANEL_ARENA_RECT[1] + 36,
                           STATS_HUD_W, STATS_HUD_H)
STATS_HUD_RECT = STATS_HUD_RECT_ARENA_BR

# Centers for Visualizations inside Panel 2
NEURAL_CENTER_X: int = PANEL_NEURAL_RECT[0] + PANEL_NEURAL_RECT[2] // 2
NEURAL_CENTER_Y: int = PANEL_NEURAL_RECT[1] + PANEL_NEURAL_RECT[3] // 2 + 10

RADIUS_EPG: float = 130.0   # Inner ring (E-PG azimuth)
RADIUS_PEN: float = 195.0   # Outer ring (P-EN shifters)

# ==============================================================================
# BIOLOGICAL NEURAL NETWORK PARAMETERS (CANN)
# ==============================================================================
@dataclass
class CircuitConfig:
    n_epg: int = 48              # E-PG compass neurons covering [0, 2pi)
    n_pen_side: int = 24         # P-EN neurons per hemisphere (24 Left + 24 Right = 48)
    n_pen_total: int = 48
    
    tau_m: float = 0.020         # Membrane integration time constant: 20 ms
    dt_ode: float = 0.002        # ODE step: 2 ms
    substeps_per_frame: int = 8  # 8 x 2ms = 16ms = ~60 FPS integration
    
    sigma_ee: float = 0.5236     # Width of local E-PG excitation (30 degrees)
    w_ee: float = 1.0            # Recurrent excitation strength
    w_ep: float = 0.8            # E-PG -> P-EN forward projection
    w_pe_ratio: float = 2.09     # Feedback ratio (21,937 / 10,479 syn)
    
    shift_angle: float = 0.7854  # 45 degrees (pi/4 radians) phase shift
    k_turn_drive: float = 2.5    # Sensitivity to steering angular velocity
    g_visual_gain: float = 2.0   # Visual landmark anchoring gain
    noise_sigma: float = 0.015   # Thermal noise

# ==============================================================================
# AGENT KINEMATICS & ARENA CONFIGURATION
# ==============================================================================
@dataclass
class AgentConfig:
    v_base: float = 150.0        # Default forward velocity (pixels / sec)
    v_min: float = 0.0           # Minimum forward velocity
    v_max: float = 280.0         # Maximum forward sprint velocity
    accel: float = 140.0         # Linear acceleration
    turn_rate: float = 2.8       # Turn rate in rad/s (~160 deg/s)
    
    body_length: float = 28.0
    body_width: float = 15.0
    wing_span: float = 32.0
    
    max_particles: int = 150
    particle_lifetime: float = 0.9
    arena_padding: int = 24

CIRCUIT_CFG = CircuitConfig()
AGENT_CFG = AgentConfig()
