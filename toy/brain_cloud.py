"""
3D Anatomical Drosophila Brain & Ventral Nerve Cord (VNC) Point Cloud Engine.
Models real-time whole-brain neural activations (0 - 200+ Hz)
grounded in the adult Drosophila connectome (hemibrain & FlyWire).
"""

from typing import List, Dict, Tuple
import math
import random
import numpy as np

from .circuit import DualRingAttractor, ang_dist, wrap_angle
from .agent import FlyAgent


class BrainPointCloud:
    """
    Simulates a 3D morphological point cloud of the fruit fly central nervous system:
      - Central Brain (Optic Lobes, Protocerebrum, Ellipsoid Body, Protocerebral Bridge)
      - Ventral Nerve Cord (Neck connective, T1 foreleg neuromere, T2 wing neuromere, T3 hindleg)
      - Real-time firing rate dynamics (0 - 200+ Hz) driven by closed-loop behavior
    """

    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        random.seed(seed)

        self.nodes: List[Dict] = []
        self._build_morphology()

        # Dynamic firing rates (Hz)
        self.firing_rates: np.ndarray = np.zeros(len(self.nodes), dtype=np.float32)

        # 3D view angles (radians)
        self.yaw: float = 0.0
        self.pitch: float = 0.28  # Subtle perspective tilt
        self.auto_rotate: bool = True
        self.time: float = 0.0

    def _build_morphology(self):
        """Constructs 3D coordinates and anatomical region assignments with proportional CNS bounds."""
        self.nodes.clear()

        # 1. Central Complex (EB Donut & PB Handlebar) ~ 360 nodes
        # EB Ring (Ellipsoid Body)
        for w in range(48):
            th = 2.0 * math.pi * w / 48.0
            for r in [18.0, 24.0, 30.0]:
                self.nodes.append({
                    "pos": np.array([r * math.cos(th), r * math.sin(th) * 0.75, 2.0], dtype=np.float32),
                    "region": "EB",
                    "wedge": w,
                    "azimuth": th,
                    "base_rate": 20.0,
                })

        # PB Handlebar (Protocerebral Bridge)
        for col in range(24):
            # Left bank
            x_l = -(12.0 + col * 2.4)
            y_l = 15.0 - 0.015 * (col * 3.0) ** 2
            z_l = 12.0 + 0.10 * col
            self.nodes.append({
                "pos": np.array([x_l, y_l, z_l], dtype=np.float32),
                "region": "PB_L",
                "col": col,
                "base_rate": 15.0,
            })
            # Right bank
            x_r = (12.0 + col * 2.4)
            y_r = 15.0 - 0.015 * (col * 3.0) ** 2
            z_r = 12.0 + 0.10 * col
            self.nodes.append({
                "pos": np.array([x_r, y_r, z_r], dtype=np.float32),
                "region": "PB_R",
                "col": col,
                "base_rate": 15.0,
            })

        # 2. Optic Lobes (Left & Right lateral wings) ~ 600 nodes
        for side, sign in [("OPTIC_L", -1), ("OPTIC_R", 1)]:
            for _ in range(300):
                u = random.uniform(0.1, math.pi * 0.9)
                v = random.uniform(-0.7, 0.7)
                ox = sign * (55.0 + 35.0 * math.sin(u) * math.cos(v))
                oy = 24.0 * math.sin(u) * math.sin(v)
                oz = 20.0 * math.cos(u) + random.uniform(-5.0, 5.0)
                self.nodes.append({
                    "pos": np.array([ox, oy, oz], dtype=np.float32),
                    "region": side,
                    "base_rate": 25.0,
                })

        # 3. Central Protocerebrum ~ 400 nodes
        for _ in range(400):
            px = np.random.normal(0.0, 26.0)
            py = np.random.normal(0.0, 20.0)
            pz = np.random.normal(8.0, 14.0)
            if abs(px) < 55.0:
                self.nodes.append({
                    "pos": np.array([px, py, pz], dtype=np.float32),
                    "region": "PROTOCEREBRUM",
                    "base_rate": 20.0,
                })

        # 4. Ventral Nerve Cord (VNC) ~ 600 nodes (Proportional z-range: -8 to -85)
        z_steps = np.linspace(-8.0, -85.0, 50)
        for z in z_steps:
            # Swellings at thoracic neuromeres:
            # T1: z ~ -26 (foreleg motor neurons)
            # T2: z ~ -48 (wing power + midleg)
            # T3: z ~ -70 (hindleg steering)
            t_factor = 1.0 + 0.8 * (
                math.exp(-((z + 26.0) / 9.0) ** 2)
                + math.exp(-((z + 48.0) / 10.0) ** 2)
                + math.exp(-((z + 70.0) / 10.0) ** 2)
            )
            rad_x = 11.0 * t_factor
            rad_y = 8.0 * t_factor
            reg = "VNC_T1" if z > -36.0 else ("VNC_T2" if z > -58.0 else ("VNC_T3" if z > -78.0 else "VNC_ABD"))

            for _ in range(12):
                vx = np.random.normal(0.0, rad_x * 0.44)
                vy = np.random.normal(0.0, rad_y * 0.44)
                self.nodes.append({
                    "pos": np.array([vx, vy, z], dtype=np.float32),
                    "region": reg,
                    "base_rate": 18.0,
                    "z_level": z,
                })

    def update_dynamics(self, circuit: DualRingAttractor, agent: FlyAgent, dt: float):
        """Computes live biological firing rates (0 - 200+ Hz) for all nodes."""
        self.time += dt
        if self.auto_rotate:
            self.yaw = 0.22 * math.sin(self.time * 0.40)

        max_epg = max(1.0, float(np.max(circuit.r_epg)))
        max_pen_l = max(1.0, float(np.max(circuit.r_pen_l)))
        max_pen_r = max(1.0, float(np.max(circuit.r_pen_r)))

        lm_bearing = agent.get_landmark_bearing()
        speed_frac = min(1.0, agent.v / agent.cfg.v_max)

        for i, node in enumerate(self.nodes):
            reg = node["region"]
            base = node["base_rate"] + random.uniform(-3.0, 3.0)

            if reg == "EB":
                w = node["wedge"]
                rate_norm = float(circuit.r_epg[w]) / max_epg
                target_hz = base + (rate_norm ** 2) * 195.0

            elif reg == "PB_L":
                col = node["col"]
                pen_rate = float(circuit.r_pen_l[col]) / max_pen_l
                target_hz = base + pen_rate * 180.0

            elif reg == "PB_R":
                col = node["col"]
                pen_rate = float(circuit.r_pen_r[col]) / max_pen_r
                target_hz = base + pen_rate * 180.0

            elif reg == "OPTIC_L":
                target_hz = base
                if agent.landmark_active and lm_bearing is not None:
                    if lm_bearing < 0.2:
                        proximity = max(0.0, math.cos(lm_bearing))
                        target_hz += proximity * 145.0

            elif reg == "OPTIC_R":
                target_hz = base
                if agent.landmark_active and lm_bearing is not None:
                    if lm_bearing > -0.2:
                        proximity = max(0.0, math.cos(lm_bearing))
                        target_hz += proximity * 145.0

            elif reg == "VNC_T1":
                act_l, act_r = circuit.get_shifter_activities()
                is_left_side = node["pos"][0] < 0
                side_drive = act_l if is_left_side else act_r
                target_hz = base + (side_drive / 6.0) * 135.0 + speed_frac * 40.0

            elif reg == "VNC_T2":
                phase = (self.time * 12.0 + node["pos"][2] * 0.20) % (2.0 * math.pi)
                wave = max(0.0, math.sin(phase))
                target_hz = base + speed_frac * (95.0 + 75.0 * wave)

            elif reg == "VNC_T3":
                target_hz = base + speed_frac * 85.0

            elif reg == "VNC_ABD":
                target_hz = base + speed_frac * 35.0

            else:  # PROTOCEREBRUM
                spont = math.sin(self.time * 3.0 + i * 0.05)
                target_hz = base + max(0.0, spont) * 25.0

            self.firing_rates[i] += (target_hz - self.firing_rates[i]) * min(1.0, 14.0 * dt)

    def project_and_depth_sort(
        self,
        center_x: float,
        center_y: float,
        scale: float = 1.6,
    ) -> List[Tuple[float, float, float, Tuple[int, int, int], float, str]]:
        """
        Projects 3D coordinates with perspective and returns depth-sorted nodes:
          (screen_x, screen_y, depth_z, (R, G, B), firing_rate_hz, region)
        """
        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)

        # Center of anatomical mass (midpoint between brain z=10 and VNC z=-85 is z~-35)
        z_pivot = -32.0

        projected = []
        for i, node in enumerate(self.nodes):
            x, y, z_raw = node["pos"]
            z = z_raw - z_pivot

            x1 = x * cos_y + y * sin_y
            y1 = -x * sin_y + y * cos_y
            z1 = z

            x2 = x1
            y2 = y1 * cos_p - z1 * sin_p
            z2 = y1 * sin_p + z1 * cos_p

            camera_dist = 420.0
            depth = camera_dist + y2
            focal = 380.0
            if depth < 10.0:
                continue

            factor = (focal / depth) * scale
            sx = center_x + x2 * factor
            sy = center_y - z2 * factor

            hz = float(self.firing_rates[i])

            # Depth-fog factor: near nodes are crisp and vivid, far nodes softly dimmed
            depth_ratio = max(0.0, min(1.0, (camera_dist + 80.0 - y2) / (camera_dist + 160.0)))
            fog = 0.65 + 0.35 * depth_ratio

            reg_name = node["region"]
            is_cx = reg_name in ("EB", "PB_L", "PB_R")

            # High-fidelity biological colormap: Deep Slate -> Electric Cyan -> Coral Pink -> Radiant Gold
            if hz < 35.0:
                f = hz / 35.0
                if is_cx:
                    # Central complex has intrinsic subtle cyan accent
                    r = int((20 + f * 20) * fog)
                    g = int((50 + f * 50) * fog)
                    b = int((75 + f * 55) * fog)
                else:
                    r = int((26 + f * 24) * fog)
                    g = int((36 + f * 32) * fog)
                    b = int((52 + f * 42) * fog)
            elif hz < 85.0:
                f = (hz - 35.0) / 50.0
                r = int((50 * (1 - f) + 0 * f) * fog)
                g = int((68 * (1 - f) + 235 * f) * fog)
                b = int((94 * (1 - f) + 215 * f) * fog)
            elif hz < 150.0:
                f = (hz - 85.0) / 65.0
                r = int((0 * (1 - f) + 250 * f) * fog)
                g = int((235 * (1 - f) + 140 * f) * fog)
                b = int((215 * (1 - f) + 160 * f) * fog)
            else:
                f = min(1.0, (hz - 150.0) / 50.0)
                r = int(255 * fog)
                g = int((150 + f * 105) * fog)
                b = int((130 + f * 125) * fog)

            color = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            projected.append((sx, sy, depth, color, hz, reg_name))

        projected.sort(key=lambda p: p[2], reverse=True)
        return projected
