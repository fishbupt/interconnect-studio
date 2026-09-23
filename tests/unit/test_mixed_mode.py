"""Mixed-mode conversion against analytically known networks.

The reference case is two ideal, uncoupled transmission lines. For identical
lines the differential and common responses both equal the line's own
transmission and there is no mode conversion. Making the lines unequal
produces mode conversion with a closed-form answer, which is what pins the
1/sqrt(2) normalisation and the block ordering.
"""

import numpy as np
import pytest

from interconnect_studio.algorithms.mixed_mode import (
    DEFAULT_FOUR_PORT_TOPOLOGY,
    FOUR_PORT_TOPOLOGIES,
    Topology,
    to_mixed_mode,
    topology_by_id,
)
from interconnect_studio.algorithms.mixed_mode.transform import _transform_matrix
from interconnect_studio.core import (
    InputValidationError,
    Line,
    MixedModeNetwork,
    Mode,
    Network,
    PortGroup,
)

FREQUENCIES = [1.0e9, 2.0e9]
T_A = 0.8 - 0.3j
T_B = 0.5 + 0.2j

D = Mode.DIFFERENTIAL
C = Mode.COMMON


def two_line_network(
    line_a: tuple[int, int],
    line_b: tuple[int, int],
    t_a: complex = T_A,
    t_b: complex = T_B,
) -> Network:
    """Two ideal, uncoupled, matched through lines in a 4-port network."""

    s = np.zeros((len(FREQUENCIES), 4, 4), dtype=np.complex128)
    for (near, far), t in ((line_a, t_a), (line_b, t_b)):
        s[:, far, near] = t
        s[:, near, far] = t
    return Network(FREQUENCIES, s, z0=50.0)


def test_transform_matrix_is_orthogonal() -> None:
    group = PortGroup(lines=(Line(name="Pair 1", near=(0, 2), far=(1, 3)),))

    transform = _transform_matrix(group, 4)

    np.testing.assert_allclose(transform @ transform.T, np.eye(4), atol=1e-15)


def test_identical_lines_give_no_mode_conversion() -> None:
    network = two_line_network((0, 1), (2, 3), t_a=T_A, t_b=T_A)

    mixed = to_mixed_mode(network, DEFAULT_FOUR_PORT_TOPOLOGY.port_group)

    np.testing.assert_allclose(mixed.mode_parameter(D, D, 1, 0), T_A, atol=1e-12)
    np.testing.assert_allclose(mixed.mode_parameter(C, C, 1, 0), T_A, atol=1e-12)
    np.testing.assert_allclose(mixed.mode_parameter(D, C, 1, 0), 0.0, atol=1e-12)
    np.testing.assert_allclose(mixed.mode_parameter(C, D, 1, 0), 0.0, atol=1e-12)


def test_matched_lines_have_no_differential_reflection() -> None:
    network = two_line_network((0, 1), (2, 3), t_a=T_A, t_b=T_A)

    mixed = to_mixed_mode(network, DEFAULT_FOUR_PORT_TOPOLOGY.port_group)

    np.testing.assert_allclose(mixed.mode_parameter(D, D, 0, 0), 0.0, atol=1e-12)


def test_unequal_lines_convert_between_modes() -> None:
    """Sdd21 = (ta + tb)/2 and Scd21 = (ta - tb)/2 for uncoupled lines."""

    network = two_line_network((0, 1), (2, 3))

    mixed = to_mixed_mode(network, DEFAULT_FOUR_PORT_TOPOLOGY.port_group)

    np.testing.assert_allclose(mixed.mode_parameter(D, D, 1, 0), (T_A + T_B) / 2, atol=1e-12)
    np.testing.assert_allclose(mixed.mode_parameter(C, C, 1, 0), (T_A + T_B) / 2, atol=1e-12)
    np.testing.assert_allclose(mixed.mode_parameter(C, D, 1, 0), (T_A - T_B) / 2, atol=1e-12)
    np.testing.assert_allclose(mixed.mode_parameter(D, C, 1, 0), (T_A - T_B) / 2, atol=1e-12)


def test_round_trip_recovers_the_single_ended_matrix() -> None:
    network = two_line_network((0, 1), (2, 3))
    group = DEFAULT_FOUR_PORT_TOPOLOGY.port_group
    transform = _transform_matrix(group, 4)

    mixed = to_mixed_mode(network, group)
    recovered = transform.T @ mixed.s @ transform

    np.testing.assert_allclose(recovered, network.s, atol=1e-12)


def test_default_topology_is_the_plts_through_1_2_3_4() -> None:
    assert DEFAULT_FOUR_PORT_TOPOLOGY.through == ((0, 1), (2, 3))
    assert DEFAULT_FOUR_PORT_TOPOLOGY.port_group.lines[0].near == (0, 2)
    assert DEFAULT_FOUR_PORT_TOPOLOGY.port_group.lines[0].far == (1, 3)


def test_alternate_topology_gives_the_1_2_3_4_pairing() -> None:
    topology = topology_by_id("through_1_3_2_4")

    assert topology.port_group.lines[0].near == (0, 1)
    assert topology.port_group.lines[0].far == (2, 3)


@pytest.mark.parametrize("topology", FOUR_PORT_TOPOLOGIES, ids=lambda t: t.id)
def test_every_topology_recovers_its_own_lines(topology: Topology) -> None:
    """Each topology finds full differential transmission on its own wiring."""

    network = two_line_network(topology.through[0], topology.through[1], t_a=T_A, t_b=T_A)

    mixed = to_mixed_mode(network, topology.port_group)

    np.testing.assert_allclose(mixed.mode_parameter(D, D, 1, 0), T_A, atol=1e-12)
    np.testing.assert_allclose(mixed.mode_parameter(C, D, 1, 0), 0.0, atol=1e-12)


def test_wrong_topology_destroys_differential_transmission() -> None:
    """Picking the wrong wiring is silently wrong, which is why it is explicit."""

    network = two_line_network((0, 1), (2, 3), t_a=T_A, t_b=T_A)

    mixed = to_mixed_mode(network, topology_by_id("through_1_3_2_4").port_group)

    assert not np.allclose(mixed.mode_parameter(D, D, 1, 0), T_A, atol=1e-6)


def test_mixed_mode_reference_impedances() -> None:
    network = two_line_network((0, 1), (2, 3))

    mixed = to_mixed_mode(network, DEFAULT_FOUR_PORT_TOPOLOGY.port_group)

    assert mixed.z0_differential == 100.0
    assert mixed.z0_common == 25.0


def test_mixed_mode_matrix_is_block_ordered() -> None:
    network = two_line_network((0, 1), (2, 3))

    mixed = to_mixed_mode(network, DEFAULT_FOUR_PORT_TOPOLOGY.port_group)

    assert mixed.n_mode_ports == 2
    np.testing.assert_allclose(mixed.s[:, 1, 0], mixed.mode_parameter(D, D, 1, 0))
    np.testing.assert_allclose(mixed.s[:, 3, 2], mixed.mode_parameter(C, C, 1, 0))


def test_transform_rejects_a_single_ended_group() -> None:
    network = two_line_network((0, 1), (2, 3))
    group = PortGroup(
        lines=(
            Line(name="Line 1", near=(0,), far=(1,)),
            Line(name="Line 2", near=(2,), far=(3,)),
        )
    )

    with pytest.raises(InputValidationError, match="differential"):
        to_mixed_mode(network, group)


def test_transform_rejects_a_group_that_misses_ports() -> None:
    network = two_line_network((0, 1), (2, 3))
    group = PortGroup(lines=(Line(name="Pair 1", near=(0, 2), far=(1, 7)),))

    with pytest.raises(InputValidationError, match="cover exactly"):
        to_mixed_mode(network, group)


def test_mixed_mode_network_is_immutable() -> None:
    mixed = to_mixed_mode(two_line_network((0, 1), (2, 3)), DEFAULT_FOUR_PORT_TOPOLOGY.port_group)

    with pytest.raises(ValueError, match="read-only"):
        mixed.s[0, 0, 0] = 1.0


def test_mode_parameter_rejects_out_of_range_ports() -> None:
    mixed = to_mixed_mode(two_line_network((0, 1), (2, 3)), DEFAULT_FOUR_PORT_TOPOLOGY.port_group)

    with pytest.raises(InputValidationError, match="response port"):
        mixed.mode_parameter(D, D, 2, 0)


def test_mixed_mode_network_rejects_a_non_differential_group() -> None:
    group = PortGroup(lines=(Line(name="Line 1", near=(0,), far=(1,)),))

    with pytest.raises(InputValidationError, match="differential"):
        MixedModeNetwork(
            frequencies_hz=FREQUENCIES,
            s=np.zeros((2, 2, 2), dtype=np.complex128),
            z0_differential=100.0,
            z0_common=25.0,
            port_group=group,
        )


def test_topology_rejects_an_incomplete_port_set() -> None:
    with pytest.raises(InputValidationError, match="ports 0..3"):
        Topology(id="bad", name="Bad", description="", through=((0, 1), (2, 2)))


def test_topology_label_uses_one_based_ports() -> None:
    assert DEFAULT_FOUR_PORT_TOPOLOGY.label() == "1→2 , 3→4"
