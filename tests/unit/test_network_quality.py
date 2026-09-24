"""Data-quality checks on networks whose physics is known by construction."""

import numpy as np
import pytest

from interconnect_studio.algorithms.network import (
    ARITHMETIC_TOLERANCE,
    PASSIVITY,
    RECIPROCITY,
    check_network,
    check_passivity,
    check_reciprocity,
)
from interconnect_studio.core import InputValidationError, Network

FREQUENCIES = [1.0e9, 2.0e9, 3.0e9]


def two_port(s11: complex, s12: complex, s21: complex, s22: complex) -> Network:
    """A frequency-flat two-port, so every point carries the same physics."""

    matrix = np.array([[s11, s12], [s21, s22]], dtype=np.complex128)
    return Network(FREQUENCIES, np.broadcast_to(matrix, (len(FREQUENCIES), 2, 2)), z0=50.0)


def matched_attenuator(transmission: complex) -> Network:
    return two_port(0.0, transmission, transmission, 0.0)


def test_lossless_through_line_sits_exactly_on_the_passivity_limit() -> None:
    result = check_passivity(matched_attenuator(1.0))

    assert result.passed is True
    assert result.worst_metric == pytest.approx(1.0, abs=1e-12)


def test_attenuator_is_passive_with_margin() -> None:
    result = check_passivity(matched_attenuator(0.5))

    assert result.passed is True
    np.testing.assert_allclose(result.metric, 0.5, atol=1e-12)
    assert result.excess.max() < -0.4


def test_amplifier_fails_passivity_at_every_frequency() -> None:
    result = check_passivity(matched_attenuator(2.0))

    assert result.passed is False
    np.testing.assert_array_equal(result.violations, np.arange(len(FREQUENCIES)))
    assert result.worst_metric == pytest.approx(2.0)


def test_passivity_covers_excitations_no_single_parameter_shows() -> None:
    """Every |S[i, j]| < 1 yet the two-port is active.

    Driving both ports in phase adds the four 0.8 terms coherently, so the
    largest singular value is 1.6. Scanning individual parameters misses
    it; that is why the check uses singular values.
    """

    network = two_port(0.8, 0.8, 0.8, 0.8)

    assert np.abs(network.s).max() < 1.0
    result = check_passivity(network)
    assert result.passed is False
    assert result.worst_metric == pytest.approx(1.6)


def test_passivity_reports_the_worst_frequency() -> None:
    s = np.zeros((3, 1, 1), dtype=np.complex128)
    s[:, 0, 0] = [0.2, 0.9, 0.4]

    result = check_passivity(Network(FREQUENCIES, s, z0=50.0))

    assert result.worst_frequency_hz == 2.0e9
    assert result.worst_index == 1


def test_isolator_is_passive_but_not_reciprocal() -> None:
    """The case that makes the two checks worth keeping apart."""

    isolator = two_port(0.0, 0.0, 1.0, 0.0)

    assert check_passivity(isolator).passed is True
    assert check_reciprocity(isolator).passed is False


def test_reciprocal_network_has_zero_asymmetry() -> None:
    result = check_reciprocity(matched_attenuator(0.5))

    assert result.passed is True
    np.testing.assert_allclose(result.metric, 0.0, atol=1e-15)


def test_reciprocity_metric_is_the_largest_asymmetry() -> None:
    result = check_reciprocity(two_port(0.1, 0.4, 0.7, 0.2))

    np.testing.assert_allclose(result.metric, 0.3, atol=1e-12)


def test_one_port_is_reciprocal_by_construction() -> None:
    s = np.full((3, 1, 1), 0.3, dtype=np.complex128)

    result = check_reciprocity(Network(FREQUENCIES, s, z0=50.0))

    assert result.passed is True
    np.testing.assert_array_equal(result.metric, np.zeros(3))


def test_tolerance_decides_the_verdict_not_the_metric() -> None:
    barely_active = matched_attenuator(1.0 + 1.0e-6)

    assert check_passivity(barely_active).passed is False
    assert check_passivity(barely_active, tolerance=1.0e-3).passed is True
    assert check_passivity(barely_active, tolerance=1.0e-3).worst_metric > 1.0


def test_checks_reject_a_negative_tolerance() -> None:
    with pytest.raises(InputValidationError, match="non-negative"):
        check_passivity(matched_attenuator(0.5), tolerance=-1.0e-9)


def test_checks_reject_a_non_finite_tolerance() -> None:
    with pytest.raises(InputValidationError, match="finite"):
        check_reciprocity(matched_attenuator(0.5), tolerance=float("nan"))


def test_checks_leave_the_network_untouched() -> None:
    network = matched_attenuator(0.5)
    before = network.s.copy()

    check_network(network)

    np.testing.assert_array_equal(network.s, before)
    assert network.s.flags.writeable is False


def test_check_network_runs_both_checks_in_order() -> None:
    results = check_network(matched_attenuator(0.5))

    assert [result.name for result in results] == [PASSIVITY, RECIPROCITY]
    assert all(result.tolerance == ARITHMETIC_TOLERANCE for result in results)


def test_summary_names_the_outcome_and_where() -> None:
    summary = check_passivity(matched_attenuator(2.0)).summary()

    assert "passivity" in summary
    assert "failed at 3 points" in summary
    assert "1e+09 Hz" in summary
