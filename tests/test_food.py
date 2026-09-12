"""
Unit verification test for FoodSystem and Odor Dynamics in food.py.
Verifies food pellet spawning, continuous odor field evaluation,
collision eating mechanics, and particle effect updates.
"""

import sys
import os
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from toy.config import PANEL_ARENA_RECT
from toy.food import FoodSystem
from toy.agent import FlyAgent


def test_food_system():
    print("==================================================")
    print("Testing FoodSystem Odor Dynamics & Eating Logic")
    print("==================================================")

    food_sys = FoodSystem(PANEL_ARENA_RECT, num_pellets=1)
    agent = FlyAgent(arena_rect=PANEL_ARENA_RECT)

    # 1. Spawning verification
    print(f"[1] Spawning count: {len(food_sys.pellets)} pellet(s)")
    assert len(food_sys.pellets) == 1, "Must spawn exactly 1 pellet by default"
    p = food_sys.pellets[0]
    assert food_sys.min_x <= p.x <= food_sys.max_x
    assert food_sys.min_y <= p.y <= food_sys.max_y

    # 2. Odor field calculation
    agent.x = p.x
    agent.y = p.y + 100.0  # 100px south of pellet
    agent.heading = -math.pi / 2  # Facing north (towards pellet)

    odor = food_sys.get_odor_at(agent.x, agent.y, agent.heading)
    print(f"[2] Odor reading at 100px: strength={odor.strength:.3f}, Ψ={math.degrees(odor.relative_bearing):.1f}°")
    assert odor.strength > 0.0, "Odor strength must be positive near pellet"
    assert abs(odor.relative_bearing) < 0.1, "Odor bearing should be ~0° when facing pellet"
    assert abs(odor.nearest_dist - 100.0) < 1.0, "Nearest distance should be ~100px"

    # 3. Eating collision detection
    initial_score = agent.score
    initial_energy = agent.energy
    agent.x = p.x
    agent.y = p.y
    old_id = p.id

    n_eaten, energy_gain = food_sys.check_eating(agent.x, agent.y, agent.heading)
    print(f"[3] Eating collision: {n_eaten} eaten, {energy_gain:.1f} energy gained")
    assert n_eaten == 1, "Pellet should be consumed"
    agent.eat_food(energy_gain, count=n_eaten)

    assert agent.score == initial_score + 1, "Score must increment by 1"
    assert len(food_sys.pellets) == 1, "A replacement pellet must be respawned"
    assert food_sys.pellets[0].id != old_id, "New pellet must have a new id"
    assert len(food_sys.effects) == 1, "Eat effect must be created"

    # 4. Effect animation update
    food_sys.update(0.1)
    assert food_sys.effects[0].age >= 0.1, "Effect age must advance"
    print("[4] Eat visual effect animation stepped successfully")

    print("\n>>> ALL FOOD SYSTEM & ODOR TESTS PASSED SUCCESSFULLY! <<<\n")


if __name__ == "__main__":
    test_food_system()
