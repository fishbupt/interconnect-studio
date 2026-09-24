"""Quality checks on the coupled-pair golden cases.

The model is a passive, reciprocal interconnect by construction: it is
built from an open-circuit impedance matrix of lossy transmission lines,
with no source and no non-reciprocal medium. So these are two-sided tests.
They check the checks, and they check the model — an active or asymmetric
result here would mean the generator's impedance-to-S conversion is wrong,
which the mixed-mode comparison alone would not catch.
"""

from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.algorithms.mixed_mode import to_mixed_mode, topology_by_id
from interconnect_studio.algorithms.network import check_passivity, check_reciprocity
from interconnect_studio.io.touchstone import read_touchstone

GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "golden_data" / "mixed_mode"

CASES = ("Case001_coupled_pair", "Case002_coupled_pair_skew")


def golden_network(case: str) -> object:
    (input_path,) = (GOLDEN_ROOT / case / "input").glob("*.s4p")
    return read_touchstone(input_path)


@pytest.mark.parametrize("case", CASES)
def test_the_coupled_pair_is_passive(case: str) -> None:
    result = check_passivity(golden_network(case))

    assert result.passed is True, result.summary()
    # A 6 inch lossy pair cannot approach unity except at the low end.
    assert 0.9 < result.worst_metric <= 1.0


@pytest.mark.parametrize("case", CASES)
def test_the_coupled_pair_is_reciprocal(case: str) -> None:
    result = check_reciprocity(golden_network(case))

    assert result.passed is True, result.summary()
    assert result.worst_metric < 1.0e-12


def test_the_passivity_margin_widens_with_loss_but_ripples() -> None:
    """sigma_max trends down with loss, yet it is not the loss.

    It is the worst case over every excitation, so the pair's standing
    waves ripple it: it falls 0.98 to 0.56 across the band while rising
    locally. Asserting monotonicity here would be asserting a physics
    claim the data does not make.
    """

    metric = check_passivity(golden_network("Case001_coupled_pair")).metric
    frequencies_ghz = np.arange(1, 201) * 0.1

    slope, _ = np.polyfit(frequencies_ghz, metric, 1)

    assert slope < 0.0
    assert metric[-1] < 0.7 * metric[0]
    assert np.any(np.diff(metric) > 0.0)


def test_the_mixed_mode_transform_preserves_the_singular_values() -> None:
    """The 1/sqrt(2) transform is orthogonal, so passivity carries over.

    This is the invariance claimed in check_passivity's docstring. It is
    what lets a mixed-mode result be judged by the single-ended check.
    """

    network = golden_network("Case001_coupled_pair")
    mixed = to_mixed_mode(network, topology_by_id("through_1_2_3_4").port_group)

    single_ended = np.linalg.svd(network.s, compute_uv=False)
    mixed_mode = np.linalg.svd(mixed.s, compute_uv=False)

    np.testing.assert_allclose(mixed_mode, single_ended, atol=1.0e-14)
