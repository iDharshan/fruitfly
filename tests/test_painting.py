"""
Unit tests for painting mechanics in Fruitfly V2: Canvas, Brush, Paint Pots, and Targets.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from painting.canvas import Canvas
from painting.brush import Brush
from painting.paint_pot import PaintPot, PotManager
from painting.target import PaintingTarget
from painting.world import PaintingWorld


def test_canvas_initialization_and_downsampling():
    """Verify Canvas buffers, area downsampling, and initial similarity."""
    canvas = Canvas(center_x=500.0, center_y=500.0, size=256, eval_size=32)
    assert canvas.buffer.shape == (256, 256, 3)
    assert np.allclose(canvas.buffer, 1.0)  # White

    eval_grid = canvas.get_evaluation_grid()
    assert eval_grid.shape == (32, 32, 3)
    assert np.allclose(eval_grid, 1.0)

    policy_grid = canvas.get_policy_grid()
    assert policy_grid.shape == (16, 16, 3)
    assert np.allclose(policy_grid, 1.0)


def test_canvas_deposition_and_similarity():
    """Verify that depositing red pigment changes canvas and updates similarity."""
    canvas = Canvas(center_x=500.0, center_y=500.0, size=256, eval_size=32)
    target = PaintingTarget.create_solid_square(color_rgb=(1.0, 0.0, 0.0))

    initial_sim = canvas.compute_similarity(target.eval_grid)

    # Deposit red pigment at center (500, 500)
    deposited = canvas.deposit_pigment(
        world_x=500.0,
        world_y=500.0,
        color_rgb=(1.0, 0.0, 0.0),
        pressure=1.0,
        delta_v=0.1,
        sigma_brush=8.0,
    )
    assert deposited > 0.0

    # Center pixel should now be red
    u_x, u_y = canvas.world_to_canvas(500.0, 500.0)
    cx, cy = int(u_x), int(u_y)
    center_color = canvas.buffer[cy, cx]
    assert center_color[0] > 0.8  # Red
    assert center_color[1] < 0.5  # Green decreased
    assert center_color[2] < 0.5  # Blue decreased

    # Similarity to red square target must have increased
    new_sim = canvas.compute_similarity(target.eval_grid)
    assert new_sim > initial_sim


def test_brush_altitude_and_contact():
    """Verify Brush altitude dynamics, contact criteria, and pigment reload."""
    brush = Brush(z_cruise=30.0, z_contact=2.0)
    assert brush.altitude == 30.0
    assert not brush.in_contact

    # Command descent to 0.0
    for _ in range(40):
        brush.update_altitude(target_z=0.0, dt=0.016)

    assert brush.altitude <= 2.0
    brush.is_down = True
    assert brush.in_contact

    # Test reload
    brush.reload(color_id=0, color_rgb=(1.0, 0.0, 0.0), volume=1.0)
    assert brush.pigment_volume == 1.0
    assert brush.color_id == 0


def test_spill_detection():
    """Verify that pen down outside canvas registers as spill without painting canvas."""
    canvas = Canvas(center_x=500.0, center_y=500.0, size=256)
    brush = Brush(z_cruise=30.0, z_contact=2.0)
    brush.altitude = 0.0
    brush.reload(color_id=0, color_rgb=(1.0, 0.0, 0.0), volume=1.0)

    # Step brush outside canvas bounds (e.g. world_x=100.0, world_y=100.0)
    dep_v, on_canvas, is_spill = brush.step(
        dt=0.1,
        world_x=100.0,
        world_y=100.0,
        canvas=canvas,
        z_target=0.0,
        pen_down=True,
        pressure=1.0,
    )
    assert is_spill
    assert not on_canvas
    assert np.allclose(canvas.buffer, 1.0)  # Canvas remains clean white


def test_pot_manager_and_reload():
    """Verify that pots are placed properly and detect reload only when landed."""
    pot_manager = PotManager()
    assert len(pot_manager) == 4

    pot_red = pot_manager.get_pot_by_id(0)
    assert pot_red is not None

    # Flying above pot: no reload
    r1 = pot_manager.check_reload(pot_red.x, pot_red.y, altitude=30.0)
    assert r1 is None

    # Landed inside pot basin: reload confirmed
    r2 = pot_manager.check_reload(pot_red.x, pot_red.y, altitude=1.0)
    assert r2 is not None
    assert r2.pot_id == 0


if __name__ == "__main__":
    test_canvas_initialization_and_downsampling()
    test_canvas_deposition_and_similarity()
    test_brush_altitude_and_contact()
    test_spill_detection()
    test_pot_manager_and_reload()
    print("All painting tests passed successfully!")
