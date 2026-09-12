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
COLOR_PFL3_LEFT: Tuple[int, int, int] = (0, 195, 255)       # #00c3ff Left PFL3 (Counter-clockwise steering)
COLOR_PFL3_RIGHT: Tuple[int, int, int] = (255, 110, 50)     # #ff6e32 Right PFL3 (Clockwise steering)


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

# Mode button geometry
BTN_MODE_WIDTH: int = 86
BTN_MODE_HEIGHT: int = 24
BTN_MODE_SPACING: int = 6
BTN_MODES_TOTAL_W: int = 3 * BTN_MODE_WIDTH + 2 * BTN_MODE_SPACING  # 270px

# Compact Floating Stats HUD dimensions
STATS_HUD_W: int = 250
STATS_HUD_H: int = 198


def compute_layout(width: int = SCREEN_WIDTH, height: int = SCREEN_HEIGHT):
    """
    Computes dashboard panel dimensions and UI positions dynamically for any resolution.
    Returns a dictionary of computed layout geometry.
    """
    content_top = HEADER_HEIGHT + 6
    content_bottom = height - FOOTER_HEIGHT - 6
    content_height = max(100, content_bottom - content_top)

    margin = 14
    gap = 12
    panel_w = max(100, (width - margin * 2 - gap) // 2)

    panel_arena = (margin, content_top, panel_w, content_height)
    panel_neural = (margin + panel_w + gap, content_top, panel_w, content_height)

    btn_modes_x = panel_neural[0] + panel_neural[2] - BTN_MODES_TOTAL_W - 16
    btn_modes_y = content_top + 12

    stats_hud_arena_br = (
        panel_arena[0] + panel_arena[2] - STATS_HUD_W - 14,
        panel_arena[1] + panel_arena[3] - STATS_HUD_H - 14,
        STATS_HUD_W,
        STATS_HUD_H,
    )
    stats_hud_arena_tr = (
        panel_arena[0] + panel_arena[2] - STATS_HUD_W - 14,
        panel_arena[1] + 36,
        STATS_HUD_W,
        STATS_HUD_H,
    )
    stats_hud_neural_tr = (
        panel_neural[0] + panel_neural[2] - STATS_HUD_W - 16,
        content_top + 86,
        STATS_HUD_W,
        STATS_HUD_H,
    )

    neural_cx = panel_neural[0] + panel_neural[2] // 2
    neural_cy = panel_neural[1] + panel_neural[3] // 2 + 10

    return {
        "width": width,
        "height": height,
        "content_top": content_top,
        "content_bottom": content_bottom,
        "content_height": content_height,
        "panel_arena": panel_arena,
        "panel_neural": panel_neural,
        "btn_modes_x": btn_modes_x,
        "btn_modes_y": btn_modes_y,
        "stats_hud_arena_br": stats_hud_arena_br,
        "stats_hud_arena_tr": stats_hud_arena_tr,
        "stats_hud_neural_tr": stats_hud_neural_tr,
        "neural_cx": neural_cx,
        "neural_cy": neural_cy,
    }


# Initialize default layout constants for SCREEN_WIDTH x SCREEN_HEIGHT
_DEFAULT_LAYOUT = compute_layout(SCREEN_WIDTH, SCREEN_HEIGHT)
CONTENT_TOP: int = _DEFAULT_LAYOUT["content_top"]
CONTENT_BOTTOM: int = _DEFAULT_LAYOUT["content_bottom"]
CONTENT_HEIGHT: int = _DEFAULT_LAYOUT["content_height"]

PANEL_ARENA_RECT: Tuple[int, int, int, int] = _DEFAULT_LAYOUT["panel_arena"]
PANEL_NEURAL_RECT: Tuple[int, int, int, int] = _DEFAULT_LAYOUT["panel_neural"]

BTN_MODES_X: int = _DEFAULT_LAYOUT["btn_modes_x"]
BTN_MODES_Y: int = _DEFAULT_LAYOUT["btn_modes_y"]

STATS_HUD_RECT_ARENA_BR: Tuple[int, int, int, int] = _DEFAULT_LAYOUT["stats_hud_arena_br"]
STATS_HUD_RECT_ARENA_TR: Tuple[int, int, int, int] = _DEFAULT_LAYOUT["stats_hud_arena_tr"]
STATS_HUD_RECT: Tuple[int, int, int, int] = STATS_HUD_RECT_ARENA_BR

NEURAL_CENTER_X: int = _DEFAULT_LAYOUT["neural_cx"]
NEURAL_CENTER_Y: int = _DEFAULT_LAYOUT["neural_cy"]

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
    
    n_pfl3_side: int = 12        # PFL3 neurons per hemisphere (12 Left + 12 Right = 24)
    n_pfl3_total: int = 24
    tau_pfl3: float = 0.025      # PFL3 membrane integration constant: 25 ms
    k_pfl3_drive: float = 2.8    # PFL3 differential steering sensitivity (rad/s)
    
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
