"""Renormalisation against networks whose answer is known in closed form.

The reference cases are a one-port load, where the reflection coefficient
at any reference impedance is ``(z_load - z0) / (z_load + z0)`` by
definition, and a uniform transmission line, whose two-port is written out
from its characteristic impedance and electrical length. Neither goes
through the transform under test.
"""

import numpy as np
import pytest

from interconnect_studio.algorithms.network import (
    SParameterDefinition,
    check_passivity,
    check_reciprocity,
    renormalize,
)
from interconnect_studio.core import InputValidationError, Network

FREQUENCIES = [1.0e9, 2.0e9, 3.0e9]
Z_LOAD = 30.0 + 20.0j


def one_port(z_load: complex, z0: complex) -> Network:
    """A frequency-flat load, referenced to ``z0``."""

    gamma = (z_load - z0) / (z_load + z0)
    return Network(FREQUENCIES, np.full((len(FREQUENCIES), 1, 1), gamma), z0=z0)


def transmission_line(
    z_line: complex,
    theta: complex,
    z0: complex,
) -> Network:
    """A uniform line of impedance ``z_line`` and electrical length ``theta``."""

    sinh, cosh = np.sinh(theta), np.cosh(theta)
    denominator = 2.0 * z_line * z0 * cosh + (z_line**2 + z0**2) * sinh
    s11 = (z_line**2 - z0**2) * sinh / denominator
    s21 = 2.0 * z_line * z0 / denominator
    matrix = np.array([[s11, s21], [s21, s11]], dtype=np.complex128)
    return Network(FREQUENCIES, np.broadcast_to(matrix, (len(FREQUENCIES), 2, 2)), z0=z0)


def gamma_at(z_load: complex, z0: complex) -> complex:
    return (z_load - z0) / (z_load + z0)


def test_fifty_to_seventy_five_matches_the_reflection_definition() -> None:
    renormalized = renormalize(one_port(Z_LOAD, 50.0), 75.0)

    np.testing.assert_allclose(
        renormalized.s[:, 0, 0], gamma_at(Z_LOAD, 75.0), rtol=1e-12, atol=1e-14
    )
    assert renormalized.z0 == 75.0


def test_seventy_five_to_fifty_matches_the_reflection_definition() -> None:
    renormalized = renormalize(one_port(Z_LOAD, 75.0), 50.0)

    np.testing.assert_allclose(
        renormalized.s[:, 0, 0], gamma_at(Z_LOAD, 50.0), rtol=1e-12, atol=1e-14
    )


def test_a_matched_load_becomes_mismatched_at_a_new_reference() -> None:
    """50 ohm into 50 ohm reflects nothing; into 75 it reflects 0.2."""

    renormalized = renormalize(one_port(50.0, 50.0), 75.0)

    np.testing.assert_allclose(renormalized.s[:, 0, 0], -0.2, rtol=1e-12, atol=1e-14)


def test_round_trip_returns_the_original_matrix() -> None:
    network = transmission_line(60.0, 0.05 + 1.2j, 50.0)

    there = renormalize(network, 75.0)
    back = renormalize(there, 50.0)

    np.testing.assert_allclose(back.s, network.s, rtol=1e-12, atol=1e-14)
    assert back.z0 == 50.0


def test_renormalizing_to_the_same_impedance_changes_nothing() -> None:
    network = transmission_line(60.0, 0.05 + 1.2j, 50.0)

    np.testing.assert_allclose(renormalize(network, 50.0).s, network.s, atol=1e-15)


def test_a_line_matches_itself_at_its_own_impedance() -> None:
    """A 75 ohm line referenced to 75 ohm is reflectionless at any length."""

    network = transmission_line(75.0, 0.1 + 2.3j, 50.0)

    renormalized = renormalize(network, 75.0)

    assert np.abs(renormalized.s[:, 0, 0]).max() < 1e-12
    np.testing.assert_allclose(np.abs(renormalized.s[:, 1, 0]), np.exp(-0.1), rtol=1e-12)


def test_two_port_matches_the_line_written_at_the_new_reference() -> None:
    theta = 0.05 + 1.2j

    renormalized = renormalize(transmission_line(60.0, theta, 50.0), 75.0)

    np.testing.assert_allclose(
        renormalized.s, transmission_line(60.0, theta, 75.0).s, rtol=1e-12, atol=1e-14
    )


def test_complex_reference_follows_pseudo_waves_not_power_waves() -> None:
    """The only case where the wave definition is visible.

    Pseudo waves keep ``(z_load - z0) / (z_load + z0)``; power waves
    conjugate the numerator's reference. ALGORITHM_GUIDE.md §11 picks
    pseudo, and this is what pins that choice.
    """

    complex_z0 = 50.0 - 10.0j
    pseudo = gamma_at(Z_LOAD, complex_z0)
    power = (Z_LOAD - np.conj(complex_z0)) / (Z_LOAD + complex_z0)

    renormalized = renormalize(one_port(Z_LOAD, 50.0), complex_z0)

    np.testing.assert_allclose(renormalized.s[:, 0, 0], pseudo, rtol=1e-12, atol=1e-14)
    assert abs(pseudo - power) > 0.05
    assert renormalized.z0 == complex_z0


def test_round_trip_through_a_complex_reference() -> None:
    network = transmission_line(60.0, 0.05 + 1.2j, 50.0)

    back = renormalize(renormalize(network, 40.0 + 15.0j), 50.0)

    np.testing.assert_allclose(back.s, network.s, rtol=1e-12, atol=1e-14)


def test_renormalisation_moves_no_energy() -> None:
    """It is a change of reference, so passivity and reciprocity survive."""

    network = transmission_line(60.0, 0.05 + 1.2j, 50.0)

    renormalized = renormalize(network, 25.0)

    assert check_passivity(renormalized).passed is True
    assert check_reciprocity(renormalized).passed is True


def test_frequencies_and_port_names_survive() -> None:
    network = Network(
        FREQUENCIES,
        np.zeros((3, 2, 2), dtype=np.complex128),
        z0=50.0,
        port_names=("in", "out"),
    )

    renormalized = renormalize(network, 75.0)

    np.testing.assert_array_equal(renormalized.frequencies_hz, network.frequencies_hz)
    assert renormalized.port_names == ("in", "out")


def test_result_is_immutable_and_leaves_the_source_alone() -> None:
    network = one_port(Z_LOAD, 50.0)
    before = network.s.copy()

    renormalized = renormalize(network, 75.0)

    np.testing.assert_array_equal(network.s, before)
    with pytest.raises(ValueError, match="read-only"):
        renormalized.s[0, 0, 0] = 1.0


def test_power_waves_are_refused_rather_than_approximated() -> None:
    with pytest.raises(NotImplementedError, match="§11"):
        renormalize(one_port(Z_LOAD, 50.0), 75.0, s_def=SParameterDefinition.POWER)


@pytest.mark.parametrize("bad", [0.0, -50.0, -10.0 + 5.0j])
def test_reference_impedance_must_have_a_positive_real_part(bad: complex) -> None:
    with pytest.raises(InputValidationError, match="positive real part"):
        renormalize(one_port(Z_LOAD, 50.0), bad)


def test_reference_impedance_must_be_finite() -> None:
    with pytest.raises(InputValidationError, match="finite"):
        renormalize(one_port(Z_LOAD, 50.0), float("inf"))
