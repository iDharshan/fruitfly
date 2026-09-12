"""
3D Anatomical Drosophila Brain & Ventral Nerve Cord (VNC) Point Cloud & Connectome Engine.
Models high-fidelity whole-brain neural activations (0 - 200+ Hz) grounded in the
adult Drosophila connectome (hemibrain & FlyWire):
  - Ellipsoid Body (EB) 3D torus mesh with E-PG compass bump
  - Protocerebral Bridge (PB) 3D handlebar with P-EN angular velocity shifters
  - Fan-Shaped Body (FB) 9-column sensory integration grid
  - Antennal Lobes (AL) olfactory glomeruli reacting to odor plumes
  - Lateral Accessory Lobes (LAL) motor steering descending hubs
  - Biological PFL3 axonal tracts connecting PB -> FB -> LAL
  - Ventral Nerve Cord (VNC) thoracic neuromeres (T1 legs, T2 wings, T3 steering)
  - Synaptic tract filament lines and real-time action potential pulses
"""

from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import json
import math
import random
import numpy as np

from .circuit import DualRingAttractor, ang_dist, wrap_angle
from .agent import FlyAgent


class BrainPointCloud:
    """
    Simulates a high-definition 3D morphological connectome of the fruit fly nervous system
    with live multi-layered bioluminescent activations, structural tract fibers, and
    action potential synaptic pulses.
    """

    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        random.seed(seed)

        self.nodes: List[Dict[str, Any]] = []
        self.tract_edges: List[Tuple[int, int, str]] = []
        self.pulses: List[Dict[str, Any]] = []

        # 3D interactive camera view
        self.yaw: float = 0.0
        self.pitch: float = 0.28  # Subtle perspective tilt
        self.user_scale: float = 1.0  # Interactive zoom multiplier [0.5 to 3.0]
        self.auto_rotate: bool = True
        self.is_dragging: bool = False
        self.time: float = 0.0

        self._build_morphology()

        # Dynamic firing rates (Hz)
        self.firing_rates: np.ndarray = np.zeros(len(self.nodes), dtype=np.float32)

    def reset_camera(self):
        """Resets camera view angles and zoom to default."""
        self.yaw = 0.0
        self.pitch = 0.28
        self.user_scale = 1.0
        self.auto_rotate = True

    def _build_morphology(self):
        """Constructs 3D coordinates, anatomical regions, and structural tract edges."""
        self.nodes.clear()
        self.tract_edges.clear()

        # ======================================================================
        # 1. CENTRAL COMPLEX: Ellipsoid Body (EB) Torus ~ 144 nodes
        # ======================================================================
        eb_start_idx = len(self.nodes)
        eb_radii = [18.0, 24.0, 30.0]
        for w in range(48):
            th = 2.0 * math.pi * w / 48.0
            for r_idx, r in enumerate(eb_radii):
                # Subtle toroidal curvature
                z_curv = 2.0 + math.cos(th * 2.0) * 0.8
                self.nodes.append({
                    "pos": np.array([r * math.cos(th), r * math.sin(th) * 0.72, z_curv], dtype=np.float32),
                    "region": "EB",
                    "wedge": w,
                    "ring": r_idx,
                    "azimuth": th,
                    "base_rate": 20.0,
                })

        # Connect circular EB tract rings & radial spokes
        for r_idx in range(len(eb_radii)):
            for w in range(48):
                idx1 = eb_start_idx + w * len(eb_radii) + r_idx
                idx2 = eb_start_idx + ((w + 1) % 48) * len(eb_radii) + r_idx
                self.tract_edges.append((idx1, idx2, "EB_RING"))

        for w in range(48):
            for r_idx in range(len(eb_radii) - 1):
                idx1 = eb_start_idx + w * len(eb_radii) + r_idx
                idx2 = eb_start_idx + w * len(eb_radii) + (r_idx + 1)
                self.tract_edges.append((idx1, idx2, "EB_SPOKE"))

        # ======================================================================
        # 2. CENTRAL COMPLEX: Protocerebral Bridge (PB) Handlebar ~ 48 nodes
        # ======================================================================
        pb_l_start = len(self.nodes)
        for col in range(24):
            x_l = -(12.0 + col * 2.3)
            y_l = 15.0 - 0.015 * (col * 3.0) ** 2
            z_l = 12.0 + 0.10 * col
            self.nodes.append({
                "pos": np.array([x_l, y_l, z_l], dtype=np.float32),
                "region": "PB_L",
                "col": col,
                "base_rate": 16.0,
            })
            if col > 0:
                self.tract_edges.append((pb_l_start + col - 1, pb_l_start + col, "PB_TRACT"))

        pb_r_start = len(self.nodes)
        for col in range(24):
            x_r = (12.0 + col * 2.3)
            y_r = 15.0 - 0.015 * (col * 3.0) ** 2
            z_r = 12.0 + 0.10 * col
            self.nodes.append({
                "pos": np.array([x_r, y_r, z_r], dtype=np.float32),
                "region": "PB_R",
                "col": col,
                "base_rate": 16.0,
            })
            if col > 0:
                self.tract_edges.append((pb_r_start + col - 1, pb_r_start + col, "PB_TRACT"))

        # Central medial commissure between PB Left and Right
        self.tract_edges.append((pb_l_start, pb_r_start, "PB_BRIDGE"))

        # Connect E-PG projection tracts from EB wedges into PB columns
        for col in range(12):
            w_l = (col * 2) % 48
            w_r = ((col * 2) + 24) % 48
            eb_node_l = eb_start_idx + w_l * len(eb_radii) + 1
            eb_node_r = eb_start_idx + w_r * len(eb_radii) + 1
            self.tract_edges.append((eb_node_l, pb_l_start + col, "EPG_PB"))
            self.tract_edges.append((eb_node_r, pb_r_start + col, "EPG_PB"))

        # ======================================================================
        # 3. CENTRAL COMPLEX: Fan-Shaped Body (FB) 9 Columns x 4 Layers ~ 72 nodes
        # ======================================================================
        fb_start = len(self.nodes)
        n_fb_columns = 9
        n_fb_layers = 4
        for c in range(n_fb_columns):
            # Columns span left (-24) to right (+24) across midline
            col_x = (c - 4.0) * 5.2
            for layer in range(n_fb_layers):
                ly_y = 6.0 + layer * 2.0
                ly_z = 7.0 + layer * 2.2
                self.nodes.append({
                    "pos": np.array([col_x, ly_y, ly_z], dtype=np.float32),
                    "region": "FB",
                    "column": c,
                    "layer": layer,
                    "base_rate": 22.0,
                })
                # Column vertical fiber
                if layer > 0:
                    curr = fb_start + c * n_fb_layers + layer
                    prev = curr - 1
                    self.tract_edges.append((prev, curr, "FB_LAYER"))

        # Horizontal layer sheets in FB
        for layer in range(n_fb_layers):
            for c in range(n_fb_columns - 1):
                idx1 = fb_start + c * n_fb_layers + layer
                idx2 = fb_start + (c + 1) * n_fb_layers + layer
                self.tract_edges.append((idx1, idx2, "FB_SHEET"))

        # ======================================================================
        # 4. SENSORY & MOTOR HUBS: Antennal Lobes (AL) & Lateral Accessory Lobes (LAL)
        # ======================================================================
        # Antennal Lobes: Primary Olfactory Neuropils (receiving food odor plume)
        al_l_start = len(self.nodes)
        for _ in range(28):
            ox = np.random.normal(-15.0, 3.8)
            oy = np.random.normal(19.0, 3.2)
            oz = np.random.normal(-6.0, 3.5)
            self.nodes.append({
                "pos": np.array([ox, oy, oz], dtype=np.float32),
                "region": "AL_L",
                "base_rate": 18.0,
            })
        for i in range(1, 28):
            if i % 3 == 0:
                self.tract_edges.append((al_l_start + i - 1, al_l_start + i, "AL_MESH"))

        al_r_start = len(self.nodes)
        for _ in range(28):
            ox = np.random.normal(15.0, 3.8)
            oy = np.random.normal(19.0, 3.2)
            oz = np.random.normal(-6.0, 3.5)
            self.nodes.append({
                "pos": np.array([ox, oy, oz], dtype=np.float32),
                "region": "AL_R",
                "base_rate": 18.0,
            })
        for i in range(1, 28):
            if i % 3 == 0:
                self.tract_edges.append((al_r_start + i - 1, al_r_start + i, "AL_MESH"))

        # Antennal Projection Tracts (AL -> FB sensory columns)
        for c in range(3):
            self.tract_edges.append((al_l_start + c * 4, fb_start + c * n_fb_layers, "AL_FB"))
            self.tract_edges.append((al_r_start + c * 4, fb_start + (8 - c) * n_fb_layers, "AL_FB"))

        # Lateral Accessory Lobes (LAL): Steering motor descending hubs
        lal_l_start = len(self.nodes)
        for _ in range(24):
            lx = np.random.normal(-18.0, 4.0)
            ly = np.random.normal(-3.0, 3.5)
            lz = np.random.normal(-2.0, 3.0)
            self.nodes.append({
                "pos": np.array([lx, ly, lz], dtype=np.float32),
                "region": "LAL_L",
                "base_rate": 16.0,
            })

        lal_r_start = len(self.nodes)
        for _ in range(24):
            lx = np.random.normal(18.0, 4.0)
            ly = np.random.normal(-3.0, 3.5)
            lz = np.random.normal(-2.0, 3.0)
            self.nodes.append({
                "pos": np.array([lx, ly, lz], dtype=np.float32),
                "region": "LAL_R",
                "base_rate": 16.0,
            })

        # ======================================================================
        # 5. BIOLOGICAL PFL3 STEERING NEURONS: PB -> FB -> LAL Tracts ~ 1,104 nodes
        # ======================================================================
        skeletons_path = Path(__file__).resolve().parent.parent / "data" / "pfl3_skeletons.json"
        if skeletons_path.exists():
            try:
                with open(skeletons_path, "r") as f:
                    skels_data = json.load(f)
                for s_idx, s in enumerate(skels_data):
                    side = s.get("side", "L")
                    reg = "PFL3_L" if side == "L" else "PFL3_R"
                    skel_nodes = s.get("nodes", [])
                    s_start = len(self.nodes)
                    for n in skel_nodes:
                        self.nodes.append({
                            "pos": np.array(n["pos"], dtype=np.float32),
                            "region": reg,
                            "pfl3_idx": s_idx,
                            "base_rate": 18.0,
                        })
                    # Link consecutive nodes into 3D axonal tracts
                    for ni in range(len(skel_nodes) - 1):
                        self.tract_edges.append((s_start + ni, s_start + ni + 1, f"PFL3_{side}"))
            except Exception:
                pass
        else:
            # Fallback procedural PFL3 tracts
            for p_idx in range(24):
                side = "L" if p_idx < 12 else "R"
                sign = -1.0 if side == "L" else 1.0
                reg = f"PFL3_{side}"
                col_i = p_idx % 12
                pb_x = sign * (12.0 + col_i * 2.0)
                pb_y = 15.0
                pb_z = 12.0
                fb_x = (col_i - 5.5) * 2.8
                fb_y = 6.0
                fb_z = 8.0
                lal_x = -sign * (16.0 + (col_i % 4) * 2.5)
                lal_y = -4.0
                lal_z = -2.0
                s_start = len(self.nodes)
                for t in np.linspace(0.0, 1.0, 30):
                    bx = (1 - t) ** 2 * pb_x + 2 * (1 - t) * t * fb_x + t ** 2 * lal_x + random.uniform(-0.8, 0.8)
                    by = (1 - t) ** 2 * pb_y + 2 * (1 - t) * t * fb_y + t ** 2 * lal_y + random.uniform(-0.8, 0.8)
                    bz = (1 - t) ** 2 * pb_z + 2 * (1 - t) * t * fb_z + t ** 2 * lal_z + random.uniform(-0.8, 0.8)
                    self.nodes.append({
                        "pos": np.array([bx, by, bz], dtype=np.float32),
                        "region": reg,
                        "pfl3_idx": p_idx,
                        "base_rate": 18.0,
                    })
                for ni in range(29):
                    self.tract_edges.append((s_start + ni, s_start + ni + 1, f"PFL3_{side}"))

        # ======================================================================
        # 6. OPTIC LOBES & PROTOCEREBRUM ~ 850 nodes
        # ======================================================================
        # 6. OPTIC LOBES & PROTOCEREBRUM ~ 850 nodes (Anatomical Scaffold Envelope)
        # ======================================================================
        for side, sign in [("OPTIC_L", -1), ("OPTIC_R", 1)]:
            for _ in range(250):
                u = random.uniform(0.1, math.pi * 0.9)
                v = random.uniform(-0.7, 0.7)
                ox = sign * (54.0 + 32.0 * math.sin(u) * math.cos(v))
                oy = 22.0 * math.sin(u) * math.sin(v)
                oz = 18.0 * math.cos(u) + random.uniform(-4.0, 4.0)
                self.nodes.append({
                    "pos": np.array([ox, oy, oz], dtype=np.float32),
                    "region": side,
                    "is_scaffold": True,
                    "base_rate": 20.0,
                })

        for _ in range(350):
            px = np.random.normal(0.0, 24.0)
            py = np.random.normal(0.0, 18.0)
            pz = np.random.normal(7.0, 13.0)
            if abs(px) < 52.0:
                self.nodes.append({
                    "pos": np.array([px, py, pz], dtype=np.float32),
                    "region": "PROTOCEREBRUM",
                    "is_scaffold": True,
                    "base_rate": 18.0,
                })

        # ======================================================================
        # 7. VENTRAL NERVE CORD (VNC) & DESCENDING MOTOR TRACTS ~ 650 nodes
        # ======================================================================
        # Paired longitudinal motor cords running down from LAL through neck to VNC
        vnc_cord_l, vnc_cord_r = [], []
        z_steps = np.linspace(-6.0, -85.0, 52)
        for z in z_steps:
            # Swellings at thoracic neuromeres (T1 leg, T2 wing, T3 hindleg)
            t_factor = 1.0 + 0.85 * (
                math.exp(-((z + 26.0) / 9.0) ** 2)
                + math.exp(-((z + 48.0) / 10.0) ** 2)
                + math.exp(-((z + 70.0) / 10.0) ** 2)
            )
            rad_x = 11.0 * t_factor
            rad_y = 8.0 * t_factor
            reg = "VNC_T1" if z > -36.0 else ("VNC_T2" if z > -58.0 else ("VNC_T3" if z > -78.0 else "VNC_ABD"))

            # Left cord node
            idx_l = len(self.nodes)
            self.nodes.append({
                "pos": np.array([-4.5 * t_factor, 0.0, z], dtype=np.float32),
                "region": reg,
                "is_cord": True,
                "side": "L",
                "base_rate": 18.0,
            })
            vnc_cord_l.append(idx_l)

            # Right cord node
            idx_r = len(self.nodes)
            self.nodes.append({
                "pos": np.array([4.5 * t_factor, 0.0, z], dtype=np.float32),
                "region": reg,
                "is_cord": True,
                "side": "R",
                "base_rate": 18.0,
            })
            vnc_cord_r.append(idx_r)

            # Cross commissure at this level
            self.tract_edges.append((idx_l, idx_r, "VNC_COMMISSURE"))

            # Surrounding motor neuromere cloud nodes (thoracic ganglion envelope)
            for _ in range(10):
                vx = np.random.normal(0.0, rad_x * 0.45)
                vy = np.random.normal(0.0, rad_y * 0.45)
                self.nodes.append({
                    "pos": np.array([vx, vy, z], dtype=np.float32),
                    "region": reg,
                    "is_scaffold": True,
                    "base_rate": 14.0,
                })

        # Connect longitudinal cord tract fibers
        for k in range(len(vnc_cord_l) - 1):
            self.tract_edges.append((vnc_cord_l[k], vnc_cord_l[k + 1], "VNC_CORD"))
            self.tract_edges.append((vnc_cord_r[k], vnc_cord_r[k + 1], "VNC_CORD"))

        # Connect LAL descending motor outputs into VNC top cords
        self.tract_edges.append((lal_l_start, vnc_cord_l[0], "LAL_VNC"))
        self.tract_edges.append((lal_r_start, vnc_cord_r[0], "LAL_VNC"))

    def update_dynamics(
        self,
        circuit: DualRingAttractor,
        agent: FlyAgent,
        dt: float,
        food_system: Optional[Any] = None,
    ):
        """Computes live biological firing rates (0 - 200+ Hz) and updates synaptic pulses."""
        self.time += dt
        if self.auto_rotate and not self.is_dragging:
            self.yaw = 0.26 * math.sin(self.time * 0.35)

        max_epg = max(1.0, float(np.max(circuit.r_epg)))
        max_pen_l = max(1.0, float(np.max(circuit.r_pen_l)))
        max_pen_r = max(1.0, float(np.max(circuit.r_pen_r)))

        lm_bearing = agent.get_landmark_bearing()
        speed_frac = min(1.0, agent.v / agent.cfg.v_max)

        # Odor sensation metrics for Antennal Lobes (AL) and Fan-Shaped Body (FB)
        odor_strength = 0.0
        odor_bearing = 0.0
        if food_system is not None:
            odor = food_system.get_odor_at(agent.x, agent.y, agent.heading)
            odor_strength = float(odor.strength)
            odor_bearing = float(odor.relative_bearing)

        for i, node in enumerate(self.nodes):
            reg = node["region"]
            base = node["base_rate"] + random.uniform(-2.5, 2.5)

            if reg == "EB":
                w = node["wedge"]
                rate_norm = float(circuit.r_epg[w]) / max_epg
                # High-contrast quadratic excitation on active wedge
                target_hz = base + (rate_norm ** 2.2) * 200.0

            elif reg == "PB_L":
                col = node["col"]
                pen_rate = float(circuit.r_pen_l[col]) / max_pen_l
                target_hz = base + (pen_rate ** 1.8) * 190.0

            elif reg == "PB_R":
                col = node["col"]
                pen_rate = float(circuit.r_pen_r[col]) / max_pen_r
                target_hz = base + (pen_rate ** 1.8) * 190.0

            elif reg == "FB":
                # Fan-Shaped Body 9 columns reflect egocentric odor bearing Psi
                col_i = node["column"]
                col_phi = -math.pi + (col_i + 0.5) * (2.0 * math.pi / 9.0)
                d_phi = ang_dist(col_phi, odor_bearing)
                col_act = max(0.0, math.cos(d_phi)) ** 2 * odor_strength
                target_hz = base + col_act * 185.0

            elif reg == "AL_L":
                # Left Antennal Lobe illuminates with odor concentration
                # Slight bilateral bias if odor is to the left
                side_bias = 1.0 + 0.3 * max(0.0, -math.sin(odor_bearing))
                target_hz = base + (odor_strength ** 1.3) * side_bias * 175.0

            elif reg == "AL_R":
                # Right Antennal Lobe
                side_bias = 1.0 + 0.3 * max(0.0, math.sin(odor_bearing))
                target_hz = base + (odor_strength ** 1.3) * side_bias * 175.0

            elif reg == "LAL_L":
                # Left LAL motor output: driven by Right PFL3 activity (turning right)
                r_pfl3_r = circuit.get_pfl3_activities()[1] if hasattr(circuit, "get_pfl3_activities") else 0.0
                target_hz = base + min(180.0, r_pfl3_r * 18.0)

            elif reg == "LAL_R":
                # Right LAL motor output: driven by Left PFL3 activity (turning left)
                r_pfl3_l = circuit.get_pfl3_activities()[0] if hasattr(circuit, "get_pfl3_activities") else 0.0
                target_hz = base + min(180.0, r_pfl3_l * 18.0)

            elif reg == "PFL3_L":
                pfl3_idx = node.get("pfl3_idx", 0)
                rate = float(circuit.r_pfl3[pfl3_idx]) if hasattr(circuit, "r_pfl3") and pfl3_idx < len(circuit.r_pfl3) else 0.0
                rate_norm = min(1.0, rate / 22.0)
                target_hz = base + (rate_norm ** 1.4) * 195.0

            elif reg == "PFL3_R":
                pfl3_idx = node.get("pfl3_idx", 12)
                rate = float(circuit.r_pfl3[pfl3_idx]) if hasattr(circuit, "r_pfl3") and pfl3_idx < len(circuit.r_pfl3) else 0.0
                rate_norm = min(1.0, rate / 22.0)
                target_hz = base + (rate_norm ** 1.4) * 195.0

            elif reg == "OPTIC_L":
                target_hz = base
                if agent.landmark_active and lm_bearing is not None and lm_bearing < 0.2:
                    target_hz += max(0.0, math.cos(lm_bearing)) * 145.0

            elif reg == "OPTIC_R":
                target_hz = base
                if agent.landmark_active and lm_bearing is not None and lm_bearing > -0.2:
                    target_hz += max(0.0, math.cos(lm_bearing)) * 145.0

            elif reg.startswith("VNC_"):
                if node.get("is_cord", False):
                    # Paired longitudinal descending motor cables (T1 legs, T2 wings, T3 hindlegs)
                    act_l, act_r = circuit.get_shifter_activities()
                    side = node.get("side", "L")
                    side_drive = act_l if side == "L" else act_r
                    target_hz = base + (side_drive / 5.0) * 110.0 + speed_frac * 75.0
                else:
                    # Subtle surrounding thoracic neuromere volume
                    target_hz = base + speed_frac * 18.0

            else:  # PROTOCEREBRUM
                spont = math.sin(self.time * 3.0 + i * 0.05)
                target_hz = base + max(0.0, spont) * 15.0

            self.firing_rates[i] += (target_hz - self.firing_rates[i]) * min(1.0, 16.0 * dt)

        # Update action potential synaptic pulses
        self._update_synaptic_pulses(circuit, dt)

    def _update_synaptic_pulses(self, circuit: DualRingAttractor, dt: float):
        """Advances active action potential pulses traversing structural tract edges."""
        # Clean expired pulses
        self.pulses = [p for p in self.pulses if p["t"] < 1.0]

        for p in self.pulses:
            p["t"] += p["speed"] * dt

        # Spawn new pulses if PFL3, compass bump, olfactory, or motor tracts are active
        if len(self.pulses) < 48 and random.random() < 0.65:
            candidates = [
                e for e in self.tract_edges
                if e[2].startswith("PFL3") or e[2].startswith("VNC") or e[2] in ("AL_FB", "EPG_PB", "LAL_VNC", "EB_RING")
            ]
            if candidates:
                # Sample a few edges to find one with high firing rate
                for _ in range(5):
                    edge = random.choice(candidates)
                    idx_a, idx_b, etype = edge
                    rate_a = self.firing_rates[idx_a]
                    if rate_a > 35.0:
                        if etype.startswith("PFL3_L"):
                            color = (0, 210, 255)
                        elif etype.startswith("PFL3_R"):
                            color = (255, 110, 50)
                        elif etype == "AL_FB":
                            color = (50, 255, 130)
                        elif etype in ("EPG_PB", "EB_RING"):
                            color = (0, 245, 212)
                        elif etype.startswith("VNC"):
                            color = (180, 225, 255)
                        else:
                            color = (255, 200, 100)

                        self.pulses.append({
                            "node_a": idx_a,
                            "node_b": idx_b,
                            "t": 0.0,
                            "speed": random.uniform(2.2, 3.8),
                            "color": color,
                        })
                        break

    def project_and_depth_sort(
        self,
        center_x: float,
        center_y: float,
        scale: float = 1.6,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Tuple[float, float]], List[Dict[str, Any]]]:
        """
        Projects 3D nodes and structural tracts with perspective and depth sorting:
        Returns:
          (projected_nodes, projected_edges, anatomical_anchors, projected_pulses)
        """
        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)

        # Pivot around brain center (midpoint between brain z=8 and VNC z=-85 is z~-30)
        z_pivot = -30.0
        camera_dist = 440.0
        focal = 400.0

        # Project all nodes
        node_proj = []
        for i, node in enumerate(self.nodes):
            x, y, z_raw = node["pos"]
            z = z_raw - z_pivot

            x1 = x * cos_y + y * sin_y
            y1 = -x * sin_y + y * cos_y
            z1 = z

            x2 = x1
            y2 = y1 * cos_p - z1 * sin_p
            z2 = y1 * sin_p + z1 * cos_p

            depth = camera_dist + y2
            if depth < 10.0:
                node_proj.append(None)
                continue

            factor = (focal / depth) * scale
            sx = center_x + x2 * factor
            sy = center_y - z2 * factor

            hz = float(self.firing_rates[i])

            # Depth fog factor: near nodes vivid, far nodes softly dimmed
            depth_ratio = max(0.0, min(1.0, (camera_dist + 80.0 - y2) / (camera_dist + 160.0)))
            fog = 0.65 + 0.35 * depth_ratio

            reg_name = node["region"]
            is_cx = reg_name in ("EB", "PB_L", "PB_R", "FB", "AL_L", "AL_R", "LAL_L", "LAL_R", "PFL3_L", "PFL3_R")
            is_cord = node.get("is_cord", False)
            is_scaffold = node.get("is_scaffold", False) or (not is_cx and not is_cord)

            # High-fidelity biological colormap
            if is_scaffold:
                # Translucent anatomical scaffold envelope (Optic lobes, protocerebrum, VNC neuromere volume)
                r = int(45 * fog)
                g = int(62 * fog)
                b = int(88 * fog)
            elif reg_name == "EB":
                # Ellipsoid Body (E-PG Compass): Deep Teal resting -> Vivid Neon Cyan active bump
                f = min(1.0, (hz - 15.0) / 160.0) if hz > 15.0 else 0.0
                r = int((15 * (1 - f) + 30 * f) * fog)
                g = int((55 * (1 - f) + 245 * f) * fog)
                b = int((75 * (1 - f) + 215 * f) * fog)
            elif reg_name in ("PB_L", "PB_R"):
                # Protocerebral Bridge (P-EN Shifters): Dark Wine resting -> Hot Neon Magenta active
                f = min(1.0, (hz - 15.0) / 160.0) if hz > 15.0 else 0.0
                r = int((65 * (1 - f) + 250 * f) * fog)
                g = int((18 * (1 - f) + 42 * f) * fog)
                b = int((50 * (1 - f) + 165 * f) * fog)
            elif reg_name == "FB":
                # Fan-Shaped Body (9-Col Sensory Grid): Dark Pine resting -> Vivid Emerald active
                f = min(1.0, (hz - 15.0) / 140.0) if hz > 15.0 else 0.0
                r = int((20 * (1 - f) + 160 * (f ** 2.0)) * fog)
                g = int((55 * (1 - f) + 245 * f) * fog)
                b = int((35 * (1 - f) + 135 * f) * fog)
            elif reg_name in ("AL_L", "AL_R"):
                # Antennal Lobes (Olfactory Glomeruli): Dark Moss resting -> Citrus Mint active
                f = min(1.0, (hz - 15.0) / 140.0) if hz > 15.0 else 0.0
                r = int((25 * (1 - f) + 120 * f) * fog)
                g = int((60 * (1 - f) + 240 * f) * fog)
                b = int((35 * (1 - f) + 110 * f) * fog)
            elif reg_name in ("LAL_L", "PFL3_L") or (is_cord and node.get("side") == "L"):
                # Left Steering & Motor Pathway: Azure Sky Blue
                f = min(1.0, (hz - 15.0) / 140.0) if hz > 15.0 else 0.0
                r = int((15 * (1 - f) + 110 * (f ** 2.0)) * fog)
                g = int((60 * (1 - f) + 215 * f) * fog)
                b = int((120 * (1 - f) + 255 * f) * fog)
            elif reg_name in ("LAL_R", "PFL3_R") or (is_cord and node.get("side") == "R"):
                # Right Steering & Motor Pathway: Electric Tangerine / Amber
                f = min(1.0, (hz - 15.0) / 140.0) if hz > 15.0 else 0.0
                r = int((110 * (1 - f) + 255 * f) * fog)
                g = int((45 * (1 - f) + 130 * f) * fog)
                b = int((20 * (1 - f) + 45 * f) * fog)
            else:
                # Default CX / other
                f = min(1.0, hz / 120.0)
                r = int((35 + 160 * f) * fog)
                g = int((55 + 160 * f) * fog)
                b = int((85 + 150 * f) * fog)

            color = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

            node_proj.append({
                "idx": i,
                "sx": sx,
                "sy": sy,
                "depth": depth,
                "color": color,
                "hz": hz,
                "region": reg_name,
                "is_cx": is_cx,
                "is_cord": is_cord,
                "is_scaffold": is_scaffold,
                "side": node.get("side", ""),
                "fog": fog,
            })

        # Project structural tract edges
        proj_edges = []
        for idx_a, idx_b, etype in self.tract_edges:
            pa = node_proj[idx_a]
            pb = node_proj[idx_b]
            if pa is not None and pb is not None:
                avg_depth = (pa["depth"] + pb["depth"]) * 0.5
                avg_hz = (pa["hz"] + pb["hz"]) * 0.5
                fog_e = (pa["fog"] + pb["fog"]) * 0.5
                # Edge alpha and color reflect structural tract type and biological activation
                if etype.startswith("PFL3_L") or (etype == "LAL_VNC" and pa.get("side") == "L"):
                    ecol = (0, int(190 * fog_e), int(255 * fog_e))
                elif etype.startswith("PFL3_R") or (etype == "LAL_VNC" and pa.get("side") == "R"):
                    ecol = (int(255 * fog_e), int(120 * fog_e), int(40 * fog_e))
                elif etype in ("PB_TRACT", "PB_BRIDGE"):
                    ecol = (int(247 * fog_e), int(37 * fog_e), int(133 * fog_e))
                elif etype in ("EB_RING", "EB_SPOKE", "EPG_PB"):
                    ecol = (int(0 * fog_e), int(240 * fog_e), int(212 * fog_e))
                elif etype in ("FB_LAYER", "FB_SHEET"):
                    ecol = (int(40 * fog_e), int(220 * fog_e), int(120 * fog_e))
                elif etype in ("AL_FB", "AL_MESH"):
                    ecol = (int(60 * fog_e), int(230 * fog_e), int(110 * fog_e))
                elif etype == "VNC_CORD":
                    is_left = pa.get("side") == "L" or pa["sx"] < center_x
                    if is_left:
                        ecol = (0, int(180 * fog_e), int(255 * fog_e))
                    else:
                        ecol = (int(255 * fog_e), int(130 * fog_e), int(50 * fog_e))
                elif etype == "VNC_COMMISSURE":
                    ecol = (int(45 * fog_e), int(65 * fog_e), int(95 * fog_e))
                else:
                    f = min(1.0, avg_hz / 120.0)
                    ecol = (
                        int((35 + 140 * f) * fog_e),
                        int((50 + 150 * f) * fog_e),
                        int((75 + 140 * f) * fog_e)
                    )

                proj_edges.append({
                    "x1": pa["sx"], "y1": pa["sy"],
                    "x2": pb["sx"], "y2": pb["sy"],
                    "depth": avg_depth,
                    "color": ecol,
                    "hz": avg_hz,
                    "type": etype,
                })

        # Compute key anatomical 3D anchor points for floating HUD callouts
        anchors = {}
        for target_reg in ["EB", "PB_L", "PB_R", "FB", "AL_L", "AL_R", "LAL_L", "LAL_R", "VNC_T1", "VNC_T2"]:
            reg_pts = [p for p in node_proj if p is not None and p["region"] == target_reg]
            if reg_pts:
                avg_sx = float(np.mean([p["sx"] for p in reg_pts]))
                avg_sy = float(np.mean([p["sy"] for p in reg_pts]))
                anchors[target_reg] = (avg_sx, avg_sy)

        # Sort nodes and edges back-to-front (highest depth first)
        valid_nodes = [p for p in node_proj if p is not None]
        valid_nodes.sort(key=lambda p: p["depth"], reverse=True)
        proj_edges.sort(key=lambda e: e["depth"], reverse=True)

        # Project synaptic action potential pulses
        proj_pulses = []
        for p in self.pulses:
            idx_a = p.get("node_a")
            idx_b = p.get("node_b")
            if idx_a is not None and idx_b is not None and idx_a < len(node_proj) and idx_b < len(node_proj):
                pa = node_proj[idx_a]
                pb = node_proj[idx_b]
                if pa is not None and pb is not None:
                    t = float(p.get("t", 0.0))
                    px = pa["sx"] + t * (pb["sx"] - pa["sx"])
                    py = pa["sy"] + t * (pb["sy"] - pa["sy"])
                    pdepth = pa["depth"] + t * (pb["depth"] - pa["depth"])
                    proj_pulses.append({
                        "x": px,
                        "y": py,
                        "depth": pdepth,
                        "color": p.get("color", (0, 245, 212)),
                    })
        proj_pulses.sort(key=lambda p: p["depth"], reverse=True)

        return valid_nodes, proj_edges, anchors, proj_pulses
