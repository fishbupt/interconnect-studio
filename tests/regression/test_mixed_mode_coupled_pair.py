"""Mixed-mode regression against the coupled-pair golden cases.

The input files are a physically shaped differential interconnect: two
coupled transmission lines with loss, dispersion and unequal even/odd
velocities. The references are closed-form modal two-port results, derived
in ``scripts/generate_golden_mixed_mode.py`` without using the transform
under test. The whole read path is exercised, so a Touchstone ordering
regression fails here too.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from interconnect_studio.algorithms.mixed_mode import to_mixed_mode, topology_by_id
from interconnect_studio.core import Mode
from interconnect_studio.io.touchstone import read_touchstone

GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "golden_data" / "mixed_mode"

CASES = ("Case001_coupled_pair", "Case002_coupled_pair_skew")

D = Mode.DIFFERENTIAL
C = Mode.COMMON

# Reference key -> (response mode, source mode, response port, source port).
PARAMETERS = {
    "sdd11": (D, D, 0, 0),
    "sdd21": (D, D, 1, 0),
    "scc11": (C, C, 0, 0),
    "scc21": (C, C, 1, 0),
    "scd21": (C, D, 1, 0),
    "sdc21": (D, C, 1, 0),
}


def load_case(case: str) -> tuple[dict[str, object], dict[str, NDArray[np.complex128]], Path]:
    directory = GOLDEN_ROOT / case
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    reference = dict(np.load(directory / "reference" / "result.npz"))
    (input_path,) = (directory / "input").glob("*.s4p")
    return config, reference, input_path


def measured(case: str) -> tuple[dict[str, object], dict[str, NDArray[np.complex128]], object]:
    config, reference, input_path = load_case(case)
    network = read_touchstone(input_path)
    topology = topology_by_id(str(config["topology"]))
    mixed = to_mixed_mode(network, topology.port_group)
    return config, reference, mixed


@pytest.mark.parametrize("case", CASES)
def test_frequency_grid_survives_the_round_trip(case: str) -> None:
    config, reference, mixed = measured(case)

    np.testing.assert_allclose(
        mixed.frequencies_hz,
        reference["frequencies_hz"].real,
        rtol=1.0e-12,
        atol=0.0,
    )


@pytest.mark.parametrize("case", CASES)
def test_mixed_mode_matches_the_analytical_reference(case: str) -> None:
    config, reference, mixed = measured(case)
    tolerance = config["tolerance"]

    for key, (response_mode, source_mode, response_port, source_port) in PARAMETERS.items():
        actual = mixed.mode_parameter(response_mode, source_mode, response_port, source_port)
        np.testing.assert_allclose(
            actual,
            reference[key],
            rtol=tolerance["rtol"],
            atol=tolerance["atol"],
            err_msg=f"{case}: {key}",
        )


@pytest.mark.parametrize("case", CASES)
def test_reference_impedances_follow_the_pair(case: str) -> None:
    _, _, mixed = measured(case)

    assert mixed.z0_differential == 100.0
    assert mixed.z0_common == 25.0


def test_symmetric_pair_converts_no_energy_between_modes() -> None:
    """A balanced pair has no mechanism to convert; skew is what breaks it."""

    _, _, mixed = measured("Case001_coupled_pair")

    assert np.abs(mixed.mode_parameter(C, D, 1, 0)).max() < 1.0e-12
    assert np.abs(mixed.mode_parameter(D, C, 1, 0)).max() < 1.0e-12


def test_skew_converts_differential_into_common_mode() -> None:
    """2 ps of intra-pair skew, rising with frequency as tan(pi f tau)."""

    config, _, mixed = measured("Case002_coupled_pair_skew")
    skew_s = float(config["parameters"]["skew_s"])

    sdd21 = mixed.mode_parameter(D, D, 1, 0)
    scd21 = mixed.mode_parameter(C, D, 1, 0)
    expected_ratio = np.abs(np.tan(np.pi * mixed.frequencies_hz * skew_s))

    np.testing.assert_allclose(np.abs(scd21 / sdd21), expected_ratio, rtol=1.0e-9)
    assert np.abs(scd21).max() < 0.2 * np.abs(sdd21).max()


def test_differential_insertion_loss_is_monotonic_and_physical() -> None:
    """SDD21 is a lossy line's transmission, not a resonance or a null."""

    _, _, mixed = measured("Case001_coupled_pair")

    loss_db = 20.0 * np.log10(np.abs(mixed.mode_parameter(D, D, 1, 0)))

    assert loss_db.max() < 0.0
    assert np.all(np.diff(loss_db) < 0.0)
    assert -8.0 < loss_db[-1] < -5.0


def test_the_wrong_topology_breaks_the_insertion_loss_shape() -> None:
    """Crossed wiring keeps the magnitude plausible but destroys the shape.

    On this symmetric pair the crossed pairing is still a symmetry axis, so
    mode conversion stays at zero and nothing looks obviously broken; only
    SDD21 gives it away, with resonant nulls instead of a lossy line's
    monotonic roll-off. That is why the topology is asked for, not guessed.
    """

    _, reference, input_path = load_case("Case001_coupled_pair")
    crossed = to_mixed_mode(
        read_touchstone(input_path), topology_by_id("through_1_3_2_4").port_group
    )

    sdd21 = crossed.mode_parameter(D, D, 1, 0)
    loss_db = 20.0 * np.log10(np.abs(sdd21))

    assert np.abs(sdd21 - reference["sdd21"]).max() > 0.5
    assert not np.all(np.diff(loss_db) < 0.0)
    assert loss_db.min() < -30.0
