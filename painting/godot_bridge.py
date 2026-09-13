"""
High-Throughput UDP Telemetry Bridge between Fruitfly V2 and Godot 4.7+ 3D Embodiment Layer.
Streams real-time fly flight 3D transform, brush pressure, canvas updates, and neural telemetry.
"""

import socket
import json
import time
from typing import Optional, Dict, Any
import numpy as np

from painting.world import PaintingWorld
from biology.interfaces import CompassState


class GodotTelemetryBridge:
    """
    UDP sender transmitting simulation state to Godot 4.7+ 3D engine.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8999):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)

    def send_telemetry(
        self,
        world: PaintingWorld,
        compass_state: Optional[CompassState] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Packs and sends binary JSON telemetry packet.
        """
        # Convert 2D arena coordinates [0, 1000] to Godot 3D tabletop space [-5.0, 5.0]
        # Arena width: 1000 -> 10.0m (-5.0 to +5.0)
        # Altitude: [0, 50] -> [0.0, 2.5]
        gx = (world.fly_x - 500.0) / 100.0
        gy = world.brush.altitude / 20.0
        gz = (world.fly_y - 500.0) / 100.0

        packet = {
            "fly_pos": [round(gx, 3), round(gy, 3), round(gz, 3)],
            "fly_theta": round(float(world.fly_theta), 3),
            "fly_v": round(float(world.fly_v), 2),
            "fly_omega": round(float(world.fly_omega), 3),
            "brush_in_contact": bool(world.brush.in_contact),
            "brush_pressure": round(float(world.brush.pressure), 3),
            "brush_pigment": round(float(world.brush.pigment_volume), 3),
            "brush_color": [round(float(c), 2) for c in world.brush.color_rgb],
            "similarity": round(float(world.current_similarity), 4),
            "reloads": int(world.reloads_count),
        }

        if compass_state is not None:
            packet["compass"] = {
                "heading": round(float(compass_state.heading), 3),
                "coherence": round(float(compass_state.coherence), 3),
                "torque": round(float(compass_state.torque), 3),
                "pfl3_bias": round(float(compass_state.pfl3_bias), 3),
            }

        if extra_data:
            packet.update(extra_data)

        try:
            data = json.dumps(packet).encode("utf-8")
            self.sock.sendto(data, (self.host, self.port))
        except Exception:
            pass  # Non-blocking, drop packet if socket buffer full

    def close(self):
        self.sock.close()
