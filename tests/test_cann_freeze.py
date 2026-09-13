import sys
import os
from dataclasses import FrozenInstanceError
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        def raises(exc_cls):
            class _Context:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    if exc_type is None:
                        raise AssertionError(f"Expected exception {exc_cls.__name__} was not raised")
                    return issubclass(exc_type, exc_cls)
            return _Context()
    pytest = _MockPytest()

from biology.cann import FrozenDualRingAttractor
from biology.interfaces import CompassState, BiologyConfig
from toy.circuit import DualRingAttractor


def test_cann_weight_immutability():
    """Verify that synaptic matrices cannot be mutated during stepping."""
    frozen_cann = FrozenDualRingAttractor()
    initial_fp = frozen_cann.fingerprint

    # Perform 500 integration steps with dynamic motor inputs
    for i in range(500):
        omega = 2.0 * np.sin(i * 0.05)
        frozen_cann.step(dt=0.016, omega=omega)
        frozen_cann.step_pfl3(odor_reading=None, dt=0.016)

    assert frozen_cann.verify_immutability()
    assert frozen_cann.fingerprint == initial_fp


def test_cann_write_protection():
    """Verify that directly attempting to assign into synaptic arrays raises an error."""
    frozen_cann = FrozenDualRingAttractor()

    with pytest.raises(ValueError):
        frozen_cann._circuit.W_ee[0, 0] = 999.0

    with pytest.raises(ValueError):
        frozen_cann._circuit.W_ep_l[0, 0] = 999.0

    with pytest.raises(ValueError):
        frozen_cann._circuit.W_pe_l[0, 0] = 999.0


def test_compass_state_immutability():
    """Verify that the emitted CompassState snapshot is strictly immutable."""
    frozen_cann = FrozenDualRingAttractor()
    state = frozen_cann.get_state()

    assert isinstance(state, CompassState)
    assert -np.pi <= state.heading <= np.pi
    assert 0.0 <= state.coherence <= 1.0

    # Test dataclass freeze
    with pytest.raises(FrozenInstanceError):
        state.heading = 1.23

    with pytest.raises(FrozenInstanceError):
        state.coherence = 0.5

    # Test array read-only flag
    with pytest.raises(ValueError):
        state.epg_activity[0] = 10.0


def test_cann_heading_tracking():
    """Verify that FrozenDualRingAttractor correctly tracks angular velocity."""
    frozen_cann = FrozenDualRingAttractor()
    frozen_cann.reset(initial_heading=0.0)

    # 1 second of right turn at 1.0 rad/s
    dt = 0.016
    for _ in range(60):
        frozen_cann.step_frame(dt_frame=dt, omega=1.0)

    state = frozen_cann.get_state()
    # Heading should have moved positively (clockwise turn)
    assert state.heading > 0.3
    assert state.coherence > 0.4


def test_scrambled_cann_condition_d():
    """Verify that scrambled CANN produces an altered fingerprint for ablation."""
    cann_normal = FrozenDualRingAttractor(scramble_weights=False)
    cann_scrambled = FrozenDualRingAttractor(scramble_weights=True, scramble_seed=123)

    assert cann_normal.fingerprint != cann_scrambled.fingerprint
    assert cann_scrambled.verify_immutability()


if __name__ == "__main__":
    test_cann_weight_immutability()
    test_cann_write_protection()
    test_compass_state_immutability()
    test_cann_heading_tracking()
    test_scrambled_cann_condition_d()
    print("All CANN freeze tests passed successfully!")
