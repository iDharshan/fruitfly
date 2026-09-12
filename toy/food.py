"""
Food System and Odor Concentration Fields for Drosophila Flight Arena.
Simulates discrete nutrient pellets, continuous radial odor dispersion,
analytical spatial gradient fields, eating collision detection, and visual effects.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import math
import random
import pygame

from .config import (
    COLOR_EPG_CYAN, COLOR_SUN_AMBER, PANEL_ARENA_RECT
)
from .circuit import wrap_angle, ang_dist


# Vibrant Cyberpunk Food Colors
COLOR_FOOD_EMERALD: Tuple[int, int, int] = (50, 235, 120)    # #32eb78 Fresh nutrient pellet
COLOR_FOOD_CORE: Tuple[int, int, int] = (200, 255, 220)       # Bright specular core
COLOR_ODOR_AURA: Tuple[int, int, int] = (40, 210, 110)        # Scent plume aura


@dataclass
class FoodPellet:
    """A discrete food pellet located in the 2D arena."""
    id: int
    x: float
    y: float
    radius: float = 7.0
    energy_value: float = 25.0
    pulse_phase: float = 0.0


@dataclass
class EatParticle:
    """A glowing sparkle particle emitted when food is eaten."""
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: Tuple[int, int, int]
    radius: float


@dataclass
class EatEffect:
    """Expanding bioluminescent ring and particle burst upon eating food."""
    x: float
    y: float
    age: float = 0.0
    max_age: float = 0.55
    particles: List[EatParticle] = field(default_factory=list)


@dataclass
class OdorReading:
    """Odor sensory metrics computed at the fly agent's position."""
    strength: float            # Normalized total concentration [0, 1]
    grad_x: float              # Spatial gradient dC/dx
    grad_y: float              # Spatial gradient dC/dy
    grad_mag: float            # Magnitude of gradient vector
    world_dir: float           # Allocentric angle towards highest concentration [-pi, pi)
    relative_bearing: float    # Egocentric angle relative to fly's heading [-pi, pi)
    nearest_dist: float        # Toroidal distance to closest food pellet (pixels)
    nearest_id: Optional[int]  # ID of nearest pellet


class FoodSystem:
    """
    Manages food pellet spawning, continuous odor concentration fields,
    eating collision detection, and eat particle visual effects.
    """

    def __init__(
        self,
        arena_rect: Tuple[int, int, int, int] = PANEL_ARENA_RECT,
        num_pellets: int = 1,
        arena_padding: int = 36,
        odor_sigma: float = 130.0,
        eat_radius: float = 22.0,
    ):
        self.arena_rect = arena_rect
        self.num_pellets = num_pellets
        self.odor_sigma = odor_sigma
        self.eat_radius = eat_radius

        # Safe bounds within arena for food spawning
        self.min_x = float(arena_rect[0] + arena_padding)
        self.max_x = float(arena_rect[0] + arena_rect[2] - arena_padding)
        self.min_y = float(arena_rect[1] + arena_padding + 16)  # Extra padding for header
        self.max_y = float(arena_rect[1] + arena_rect[3] - arena_padding)

        self.span_x = self.max_x - self.min_x
        self.span_y = self.max_y - self.min_y

        self.pellets: List[FoodPellet] = []
        self.effects: List[EatEffect] = []
        self.next_id: int = 1

        # Spawn initial food pellets
        self.spawn_initial_pellets()

    def set_arena_rect(self, arena_rect: Tuple[int, int, int, int], arena_padding: int = 36):
        """Updates the food spawning boundaries when arena size changes."""
        self.arena_rect = arena_rect
        self.min_x = float(arena_rect[0] + arena_padding)
        self.max_x = float(arena_rect[0] + arena_rect[2] - arena_padding)
        self.min_y = float(arena_rect[1] + arena_padding + 16)
        self.max_y = float(arena_rect[1] + arena_rect[3] - arena_padding)
        self.span_x = self.max_x - self.min_x
        self.span_y = self.max_y - self.min_y
        for p in self.pellets:
            p.x = max(self.min_x, min(self.max_x, p.x))
            p.y = max(self.min_y, min(self.max_y, p.y))

    def spawn_initial_pellets(self):
        """Spawns the initial set of food pellets spaced throughout the arena."""
        self.pellets.clear()
        for _ in range(self.num_pellets):
            pellet = self._create_random_pellet()
            self.pellets.append(pellet)

    def _create_random_pellet(self, avoid_x: Optional[float] = None, avoid_y: Optional[float] = None, min_avoid_dist: float = 120.0) -> FoodPellet:
        """Generates a food pellet at a random valid location, optionally avoiding a point (e.g. the fly)."""
        best_x = random.uniform(self.min_x, self.max_x)
        best_y = random.uniform(self.min_y, self.max_y)

        # Attempt up to 20 times to find a position well-separated from avoid point and other pellets
        for _ in range(20):
            cand_x = random.uniform(self.min_x, self.max_x)
            cand_y = random.uniform(self.min_y, self.max_y)

            # Avoid specified point
            if avoid_x is not None and avoid_y is not None:
                d = self.torus_dist(cand_x, cand_y, avoid_x, avoid_y)
                if d < min_avoid_dist:
                    continue

            # Avoid existing pellets
            too_close = False
            for p in self.pellets:
                if self.torus_dist(cand_x, cand_y, p.x, p.y) < 60.0:
                    too_close = True
                    break

            if not too_close:
                best_x, best_y = cand_x, cand_y
                break

        pellet = FoodPellet(
            id=self.next_id,
            x=best_x,
            y=best_y,
            radius=7.0,
            pulse_phase=random.uniform(0.0, 2.0 * math.pi),
        )
        self.next_id += 1
        return pellet

    def torus_delta(self, x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
        """
        Computes the minimal displacement vector (x2 - x1, y2 - y1) taking
        toroidal boundary wrapping into account.
        """
        dx = x2 - x1
        if dx > self.span_x * 0.5:
            dx -= self.span_x
        elif dx < -self.span_x * 0.5:
            dx += self.span_x

        dy = y2 - y1
        if dy > self.span_y * 0.5:
            dy -= self.span_y
        elif dy < -self.span_y * 0.5:
            dy += self.span_y

        return dx, dy

    def torus_dist(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Computes minimal Euclidean distance on torus."""
        dx, dy = self.torus_delta(x1, y1, x2, y2)
        return math.hypot(dx, dy)

    def get_odor_at(self, fly_x: float, fly_y: float, fly_heading: float) -> OdorReading:
        """
        Calculates the local continuous odor field at the fly's location:
          - Total concentration: C_total = sum(exp(-d_i^2 / (2 * sigma^2)))
          - Spatial gradient: grad(C) = sum( (v_i / sigma^2) * C_i )
          - Preferred allocentric direction: atan2(grad_y, grad_x)
          - Preferred egocentric bearing: wrap(preferred_dir - heading)
        """
        if not self.pellets:
            return OdorReading(
                strength=0.0,
                grad_x=0.0,
                grad_y=0.0,
                grad_mag=0.0,
                world_dir=fly_heading,
                relative_bearing=0.0,
                nearest_dist=9999.0,
                nearest_id=None,
            )

        two_sig_sq = 2.0 * (self.odor_sigma ** 2)
        inv_sig_sq = 1.0 / (self.odor_sigma ** 2)

        tot_c = 0.0
        tot_gx = 0.0
        tot_gy = 0.0

        min_dist = 999999.0
        nearest_id = None

        for p in self.pellets:
            # Vector from fly to pellet
            dx, dy = self.torus_delta(fly_x, fly_y, p.x, p.y)
            d = math.hypot(dx, dy)

            if d < min_dist:
                min_dist = d
                nearest_id = p.id

            # Gaussian concentration profile
            c_i = math.exp(-(d ** 2) / two_sig_sq)
            tot_c += c_i

            # Spatial gradient pointing along displacement vector towards pellet
            tot_gx += dx * inv_sig_sq * c_i
            tot_gy += dy * inv_sig_sq * c_i

        grad_mag = math.hypot(tot_gx, tot_gy)

        if grad_mag > 1e-7:
            world_dir = math.atan2(tot_gy, tot_gx)
        else:
            # If gradients cancel out or are negligible, default along fly heading
            world_dir = fly_heading

        relative_bearing = float(wrap_angle(world_dir - fly_heading))

        # Normalize strength to [0.0, 1.0]
        norm_strength = min(1.0, tot_c)

        return OdorReading(
            strength=norm_strength,
            grad_x=tot_gx,
            grad_y=tot_gy,
            grad_mag=grad_mag,
            world_dir=world_dir,
            relative_bearing=relative_bearing,
            nearest_dist=min_dist,
            nearest_id=nearest_id,
        )

    def check_eating(self, fly_x: float, fly_y: float, fly_heading: float) -> Tuple[int, float]:
        """
        Checks if the fly has approached close enough to eat any pellet.
        Tests both the fly center and the forward mouth/head position.
        Returns: (num_eaten, total_energy_gained)
        """
        # Mouth position slightly forward from center
        mouth_dist = 10.0
        mouth_x = fly_x + mouth_dist * math.cos(fly_heading)
        mouth_y = fly_y + mouth_dist * math.sin(fly_heading)

        eaten_indices = []
        energy_gained = 0.0

        for idx, p in enumerate(self.pellets):
            d_center = self.torus_dist(fly_x, fly_y, p.x, p.y)
            d_mouth = self.torus_dist(mouth_x, mouth_y, p.x, p.y)

            if d_center <= self.eat_radius or d_mouth <= (self.eat_radius * 0.85):
                eaten_indices.append(idx)
                energy_gained += p.energy_value
                # Spawn eat visual effect at pellet position
                self._trigger_eat_effect(p.x, p.y)

        if eaten_indices:
            # Remove eaten pellets in reverse order and respawn new ones
            for idx in sorted(eaten_indices, reverse=True):
                self.pellets.pop(idx)
                new_p = self._create_random_pellet(avoid_x=fly_x, avoid_y=fly_y, min_avoid_dist=140.0)
                self.pellets.append(new_p)

        return len(eaten_indices), energy_gained

    def _trigger_eat_effect(self, x: float, y: float):
        """Creates expanding ring and sparkling particles upon eating."""
        particles = []
        n_sparks = 14
        for _ in range(n_sparks):
            ang = random.uniform(0.0, 2.0 * math.pi)
            speed = random.uniform(40.0, 110.0)
            vx = speed * math.cos(ang)
            vy = speed * math.sin(ang)
            life = random.uniform(0.3, 0.55)
            col = random.choice([
                COLOR_FOOD_EMERALD,
                COLOR_FOOD_CORE,
                (255, 235, 100),  # Golden sparkle
                COLOR_EPG_CYAN,
            ])
            particles.append(EatParticle(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                life=life,
                max_life=life,
                color=col,
                radius=random.uniform(2.0, 4.0),
            ))

        effect = EatEffect(x=x, y=y, age=0.0, max_age=0.55, particles=particles)
        self.effects.append(effect)

    def update(self, dt: float):
        """Updates animation pulse of pellets and steps active visual effects."""
        # Pulse food pellet animation
        for p in self.pellets:
            p.pulse_phase = (p.pulse_phase + 4.0 * dt) % (2.0 * math.pi)

        # Update eat visual effects
        surviving_effects = []
        for eff in self.effects:
            eff.age += dt
            if eff.age < eff.max_age:
                # Step particles
                for part in eff.particles:
                    part.x += part.vx * dt
                    part.y += part.vy * dt
                    part.life -= dt
                    part.vx *= 0.94
                    part.vy *= 0.94
                eff.particles = [pt for pt in eff.particles if pt.life > 0]
                surviving_effects.append(eff)
        self.effects = surviving_effects

    def reset(self):
        """Resets all pellets and clears effects."""
        self.effects.clear()
        self.spawn_initial_pellets()
