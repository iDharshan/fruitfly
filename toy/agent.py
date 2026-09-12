"""
2D Fly Agent Kinematics, Sensory Feedback, and Particle Wake.
Translates decoded neural compass heading into physical movement in the expanded arena.
"""

from dataclasses import dataclass
from typing import Tuple, List, Optional
import math
import random
import numpy as np

from .config import AgentConfig, AGENT_CFG, PANEL_ARENA_RECT
from .circuit import wrap_angle


@dataclass
class Particle:
    """A glowing bioluminescent exhaust particle emitted by the fly."""
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    radius: float
    color_type: str = "cyan"  # 'cyan' or 'amber'


class FlyAgent:
    """
    Simulates the physical fruit fly agent moving in the 2-D arena:
      - Closed-loop steering locked to decoded central complex attractor heading
      - Throttle control (accelerate / brake)
      - Retinotopic visual feedback relative to active landmark
      - Optional phototaxis beacon steering mode
      - Bioluminescent particle wake trail
    """

    def __init__(self, cfg: AgentConfig = AGENT_CFG, arena_rect: Tuple[int, int, int, int] = PANEL_ARENA_RECT):
        self.cfg = cfg
        self.arena_rect = arena_rect

        # Arena bounds
        pad = cfg.arena_padding
        self.min_x = float(arena_rect[0] + pad)
        self.max_x = float(arena_rect[0] + arena_rect[2] - pad)
        self.min_y = float(arena_rect[1] + pad)
        self.max_y = float(arena_rect[1] + arena_rect[3] - pad)

        # Agent state
        self.x: float = (self.min_x + self.max_x) / 2.0
        self.y: float = (self.min_y + self.max_y) / 2.0
        self.heading: float = 0.0  # Radians
        self.v: float = cfg.v_base
        self.target_v: float = cfg.v_base

        # Visual landmark state (World coordinates)
        self.landmark_x: Optional[float] = None
        self.landmark_y: Optional[float] = None
        self.landmark_active: bool = False
        self.phototaxis_active: bool = False  # Optional auto-seek mode (T key)

        # Particle wake
        self.particles: List[Particle] = []

        # Wing animation phase
        self.wing_phase: float = 0.0

    def reset(self, initial_heading: float = 0.0):
        """Resets the fly to arena center with initial heading and clear particles."""
        self.x = (self.min_x + self.max_x) / 2.0
        self.y = (self.min_y + self.max_y) / 2.0
        self.heading = initial_heading
        self.v = self.cfg.v_base
        self.target_v = self.cfg.v_base
        self.particles.clear()
        self.wing_phase = 0.0

    def set_landmark(self, x: float, y: float):
        """Places or moves the visual landmark in the arena."""
        clamped_x = max(self.min_x, min(self.max_x, x))
        clamped_y = max(self.min_y, min(self.max_y, y))
        self.landmark_x = clamped_x
        self.landmark_y = clamped_y
        self.landmark_active = True

    def toggle_landmark(self):
        """Toggles active status of landmark."""
        if self.landmark_x is not None:
            self.landmark_active = not self.landmark_active

    def toggle_phototaxis(self):
        """Toggles phototaxis attraction mode (auto-flying towards sun beacon)."""
        self.phototaxis_active = not self.phototaxis_active
        return self.phototaxis_active

    def clear_landmark(self):
        """Removes the landmark completely."""
        self.landmark_x = None
        self.landmark_y = None
        self.landmark_active = False
        self.phototaxis_active = False

    def get_landmark_world_angle(self) -> Optional[float]:
        """Returns the allocentric world angle to the landmark from the fly."""
        if not self.landmark_active or self.landmark_x is None or self.landmark_y is None:
            return None
        dx = self.landmark_x - self.x
        dy = self.landmark_y - self.y
        return float(math.atan2(dy, dx))

    def get_landmark_bearing(self) -> Optional[float]:
        """
        Computes the relative bearing (in radians) of the landmark
        in the fly's egocentric head coordinate frame:
          psi = wrap(atan2(y_mark - y_fly, x_mark - x_fly) - heading)
        Returns None if landmark is inactive.
        """
        world_angle = self.get_landmark_world_angle()
        if world_angle is None:
            return None
        return float(wrap_angle(world_angle - self.heading))

    def compute_phototaxis_steering(self) -> float:
        """
        Computes smooth steering omega towards landmark if phototaxis mode is active.
        Slows down near target to prevent revolving/orbiting.
        """
        if not self.phototaxis_active or not self.landmark_active or self.landmark_x is None:
            return 0.0

        dx = self.landmark_x - self.x
        dy = self.landmark_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 30.0:
            # Reached beacon: hover/slow down
            self.target_v = 15.0
            return 0.0

        bearing = self.get_landmark_bearing()
        if bearing is None:
            return 0.0

        # Proportional steering with speed reduction near cue
        steer_gain = 3.0
        return float(np.clip(steer_gain * bearing, -self.cfg.turn_rate, self.cfg.turn_rate))

    def update_velocity(self, accel_dir: float, dt: float):
        """Updates target velocity based on user input."""
        if accel_dir > 0:
            self.target_v = min(self.cfg.v_max, self.target_v + self.cfg.accel * dt)
        elif accel_dir < 0:
            self.target_v = max(self.cfg.v_min, self.target_v - self.cfg.accel * dt)
        else:
            if not self.phototaxis_active:
                # Gradually relax towards base velocity
                if self.target_v > self.cfg.v_base:
                    self.target_v = max(self.cfg.v_base, self.target_v - 60.0 * dt)
                elif self.target_v < self.cfg.v_base:
                    self.target_v = min(self.cfg.v_base, self.target_v + 60.0 * dt)

        self.v += (self.target_v - self.v) * min(1.0, 10.0 * dt)

    def update_kinematics(self, decoded_heading: float, dt: float):
        """Steps physical kinematics of the agent."""
        self.heading = decoded_heading

        # Advance position along heading vector
        self.x += self.v * math.cos(self.heading) * dt
        self.y += self.v * math.sin(self.heading) * dt

        # Periodic torus wrapping with seamless padding
        span_x = self.max_x - self.min_x
        span_y = self.max_y - self.min_y

        if self.x < self.min_x:
            self.x += span_x
        elif self.x > self.max_x:
            self.x -= span_x

        if self.y < self.min_y:
            self.y += span_y
        elif self.y > self.max_y:
            self.y -= span_y

        # Update wing flap phase
        wing_speed = 35.0 + (self.v / self.cfg.v_max) * 45.0
        self.wing_phase = (self.wing_phase + wing_speed * dt) % (2.0 * math.pi)

        # Emit wake particles if moving
        if self.v > 10.0 and len(self.particles) < self.cfg.max_particles:
            tail_dist = self.cfg.body_length * 0.65
            emit_x = self.x - tail_dist * math.cos(self.heading)
            emit_y = self.y - tail_dist * math.sin(self.heading)

            jitter_angle = self.heading + math.pi + random.uniform(-0.4, 0.4)
            speed = random.uniform(15.0, 45.0)
            vx = speed * math.cos(jitter_angle)
            vy = speed * math.sin(jitter_angle)
            lifetime = random.uniform(0.4, self.cfg.particle_lifetime)
            color_type = "amber" if random.random() < 0.25 else "cyan"

            self.particles.append(Particle(
                x=emit_x,
                y=emit_y,
                vx=vx,
                vy=vy,
                life=lifetime,
                max_life=lifetime,
                radius=random.uniform(2.0, 4.5),
                color_type=color_type
            ))

        # Update and cull existing particles
        surviving = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving
