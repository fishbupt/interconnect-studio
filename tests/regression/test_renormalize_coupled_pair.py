"""Renormalisation on the coupled-pair golden case.

The unit tests pin the algebra on one- and two-ports with closed-form
answers. This adds the thing they cannot: a real 4-port matrix, read off
disk, where the batched solve has to handle non-commuting matrices.
"""

from pathlib import Path

import numpy as np

from interconnect_studio.algorithms.mixed_mode import to_mixed_mode, topology_by_id
from interconnect_studio.algorithms.network import (
    check_passivity,
    check_reciprocity,
    renormalize,
)
from interconnect_studio.core import Mode, Network
from interconnect_studio.io.touchstone import read_touchstone

GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "golden_data" / "mixed_mode"

# From Case001's config.json: the pair's odd-mode characteristic impedance.
Z_ODD_OHM = 46.0


def coupled_pair() -> Network:
    return read_touchstone(
        GOLDEN_ROOT / "Case001_coupled_pair" / "input" / "coupled_pair.s4p"
    )


def test_round_trip_on_a_four_port_returns_the_original() -> None:
    network = coupled_pair()

    back = renormalize(renormalize(network, 100.0), 50.0)

    np.testing.assert_allclose(back.s, network.s, rtol=1e-11, atol=1e-13)


def test_renormalisation_keeps_the_pair_passive_and_reciprocal() -> None:
    renormalized = renormalize(coupled_pair(), 100.0)

    assert check_passivity(renormalized).passed is True
    assert check_reciprocity(renormalized).passed is True


def test_referencing_the_odd_mode_impedance_removes_differential_reflection() -> None:
    """The physical check that ties renormalisation to mixed mode.

    The differential port references twice the single-ended impedance, so
    referencing the pair to its own odd-mode impedance puts the
    differential port at the line's differential impedance. A uniform line
    seen at its own characteristic impedance reflects nothing, at any
    length or loss, so SDD11 must collapse.
    """

    group = topology_by_id("through_1_2_3_4").port_group
    at_fifty = to_mixed_mode(coupled_pair(), group)
    matched = to_mixed_mode(renormalize(coupled_pair(), Z_ODD_OHM), group)

    assert matched.z0_differential == 2.0 * Z_ODD_OHM
    # At 50 ohm the 92 ohm pair rings against the 100 ohm reference. The
    # comparison is between peaks: the standing-wave nulls reach 0.008 on
    # their own, so the floor says nothing about the match.
    assert np.abs(at_fifty.mode_parameter(Mode.DIFFERENTIAL, Mode.DIFFERENTIAL, 0, 0)).max() > 0.07
    assert np.abs(matched.mode_parameter(Mode.DIFFERENTIAL, Mode.DIFFERENTIAL, 0, 0)).max() < 1e-12
