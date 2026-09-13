"""
Unit test suite for biological sensory systems: Olfactory (ORN & AL) and Visual (VPN & bearings).
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from biology.olfactory import OlfactorySystem, OdorReading
from biology.visual import VisualSystem
from biology.interfaces import SensoryState, BiologyConfig
from painting.canvas import Canvas
from painting.paint_pot import PotManager


def test_olfactory_isolation_and_no_crosstalk():
    """Verify that being at Pot Red activates Glomerulus Red without activating distant pots."""
    pot_manager = PotManager()
    olfactory = OlfactorySystem(pot_manager=pot_manager, sigma_odor=100.0)

    pot_red = pot_manager.get_pot_by_id(0)
    pot_blue = pot_manager.get_pot_by_id(2)

    # Position fly directly over Pot Red (150, 150)
    conc = olfactory.compute_concentrations(pot_red.x, pot_red.y)
    al = olfactory.compute_al_glomeruli(conc)

    # Glomerulus Red (channel 0) should be near maximal
    assert conc[0] > 0.95
    assert al[0] > 0.95

    # Glomerulus Blue (channel 2 at 850, 850) should be virtually zero
    assert conc[2] < 1e-4
    assert al[2] < 1e-4


def test_odor_gradient_direction():
    """Verify that the analytical odor gradient points toward the pot center."""
    pot_manager = PotManager()
    olfactory = OlfactorySystem(pot_manager=pot_manager)
    pot_red = pot_manager.get_pot_by_id(0)  # (150, 150)

    # Fly at (200, 200) -> gradient should point in (-x, -y) direction
    gx, gy = olfactory.compute_gradient(pot_id=0, world_x=200.0, world_y=200.0)
    assert gx < 0.0
    assert gy < 0.0

    # Fly at (100, 100) -> gradient should point in (+x, +y) direction
    gx2, gy2 = olfactory.compute_gradient(pot_id=0, world_x=100.0, world_y=100.0)
    assert gx2 > 0.0
    assert gy2 > 0.0


def test_visual_bearings_and_sensory_state():
    """Verify that visual system generates correct egocentric bearings and SensoryState."""
    canvas = Canvas(center_x=500.0, center_y=500.0)
    pot_manager = PotManager()
    olfactory = OlfactorySystem(pot_manager=pot_manager)
    visual = VisualSystem(canvas=canvas, pot_manager=pot_manager, olfactory=olfactory)

    # Fly at (500, 700) facing North (heading = -pi/2), looking directly at canvas (500, 500)
    state = visual.compute_sensory_state(
        fly_x=500.0,
        fly_y=700.0,
        fly_heading=-np.pi / 2.0,
        fly_altitude=30.0,
    )

    assert isinstance(state, SensoryState)
    # Bearing to canvas should be 0.0 (dead ahead)
    assert abs(state.canvas_bearing) < 0.01

    sens_vec = state.to_sensory_vector()
    assert sens_vec.shape == (8,)
    assert np.all(sens_vec >= -1.0) and np.all(sens_vec <= 1.0)

    odor_vec = state.to_odor_vector()
    assert odor_vec.shape == (4,)
    assert np.all(odor_vec >= 0.0) and np.all(odor_vec <= 1.0)


def test_retinotopic_vpn_activation():
    """Verify that visual projection neurons activate properly."""
    canvas = Canvas(center_x=500.0, center_y=500.0)
    pot_manager = PotManager()
    olfactory = OlfactorySystem(pot_manager=pot_manager)
    visual = VisualSystem(canvas=canvas, pot_manager=pot_manager, olfactory=olfactory)

    vpn = visual.compute_retinotopic_receptive_fields(
        fly_x=500.0,
        fly_y=700.0,
        fly_heading=-np.pi / 2.0,
    )
    assert vpn.shape == (16,)
    assert np.max(vpn) > 0.5


if __name__ == "__main__":
    test_olfactory_isolation_and_no_crosstalk()
    test_odor_gradient_direction()
    test_visual_bearings_and_sensory_state()
    test_retinotopic_vpn_activation()
    print("All sensory tests passed successfully!")
