"""
Telemetry, Metrics Tracking, and Real-Time State History.
Collects and aggregates biological CANN metrics for dashboard visualization.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Tuple
import math
import numpy as np


@dataclass
class TelemetryFrame:
    timestamp: float
    heading_deg: float
    angular_vel_deg: float
    bump_amplitude: float
    bump_coherence: float
    pen_left_activity: float
    pen_right_activity: float
    agent_speed: float
    landmark_active: bool
    landmark_bearing_deg: float = 0.0


class TelemetryTracker:
    """
    Maintains rolling history buffers for high-speed waveform rendering
    and live dashboard telemetry computation.
    """

    def __init__(self, history_len: int = 180):
        self.history_len = history_len
        self.history: Deque[TelemetryFrame] = deque(maxlen=history_len)
        self.total_frames: int = 0
        self.sim_time: float = 0.0

        # Peak stats
        self.max_pen_left: float = 0.0
        self.max_pen_right: float = 0.0
        self.max_speed: float = 0.0

    def record(
        self,
        dt: float,
        heading_rad: float,
        angular_vel_rad: float,
        amplitude: float,
        coherence: float,
        pen_left: float,
        pen_right: float,
        speed: float,
        landmark_active: bool,
        landmark_bearing_rad: float = 0.0,
    ):
        """Records a single simulation frame snapshot."""
        self.sim_time += dt
        self.total_frames += 1

        heading_deg = (math.degrees(heading_rad) + 360.0) % 360.0
        omega_deg = math.degrees(angular_vel_rad)
        bearing_deg = math.degrees(landmark_bearing_rad)

        self.max_pen_left = max(self.max_pen_left, pen_left)
        self.max_pen_right = max(self.max_pen_right, pen_right)
        self.max_speed = max(self.max_speed, speed)

        frame = TelemetryFrame(
            timestamp=self.sim_time,
            heading_deg=heading_deg,
            angular_vel_deg=omega_deg,
            bump_amplitude=amplitude,
            bump_coherence=coherence,
            pen_left_activity=pen_left,
            pen_right_activity=pen_right,
            agent_speed=speed,
            landmark_active=landmark_active,
            landmark_bearing_deg=bearing_deg,
        )
        self.history.append(frame)

    def get_latest(self) -> TelemetryFrame:
        """Returns the most recent telemetry frame."""
        if self.history:
            return self.history[-1]
        return TelemetryFrame(
            timestamp=0.0,
            heading_deg=0.0,
            angular_vel_deg=0.0,
            bump_amplitude=0.0,
            bump_coherence=0.0,
            pen_left_activity=0.0,
            pen_right_activity=0.0,
            agent_speed=0.0,
            landmark_active=False,
        )

    def get_time_series(self, metric: str) -> List[float]:
        """Returns array of historic values for the specified metric name."""
        return [getattr(f, metric) for f in self.history]
