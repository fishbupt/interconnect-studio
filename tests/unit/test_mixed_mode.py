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
    cartesian_formats_for_mixed_mode,
    create_mixed_mode_trace,
    format_mixed_mode_parameter,
    is_mixed_mode_reflection,
    mixed_mode_parameter_name,
    to_mixed_mode,
    topology_by_id,
)
from interconnect_studio.algorithms.mixed_mode.transform import _transform_matrix
from interconnect_studio.algorithms.network import SParameterFormat
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


def mixed() -> MixedModeNetwork:
    return to_mixed_mode(two_line_network((0, 1), (2, 3)), DEFAULT_FOUR_PORT_TOPOLOGY.port_group)


@pytest.mark.parametrize(
    ("response_mode", "source_mode", "response_port", "source_port", "expected"),
    [
        (D, D, 1, 0, "SDD21"),
        (D, C, 0, 0, "SDC11"),
        (C, D, 1, 1, "SCD22"),
        (C, C, 0, 1, "SCC12"),
    ],
)
def test_parameter_names_are_engineering_names(
    response_mode: Mode,
    source_mode: Mode,
    response_port: int,
    source_port: int,
    expected: str,
) -> None:
    assert (
        mixed_mode_parameter_name(response_mode, source_mode, response_port, source_port)
        == expected
    )


def test_same_mode_same_port_is_a_reflection() -> None:
    assert is_mixed_mode_reflection(D, D, 0, 0) is True
    assert is_mixed_mode_reflection(C, C, 1, 1) is True


def test_mode_conversion_on_one_port_is_not_a_reflection() -> None:
    """SDC11 relates two modes, so no single reference impedance describes it."""

    assert is_mixed_mode_reflection(D, C, 0, 0) is False


def test_transmission_is_not_a_reflection() -> None:
    assert is_mixed_mode_reflection(D, D, 1, 0) is False


def test_reflection_offers_impedance_formats() -> None:
    formats = cartesian_formats_for_mixed_mode(D, D, 0, 0)

    assert SParameterFormat.SWR in formats


def test_mode_conversion_hides_impedance_formats() -> None:
    formats = cartesian_formats_for_mixed_mode(D, C, 0, 0)

    assert SParameterFormat.SWR not in formats


def test_log_mag_matches_the_coefficient() -> None:
    network = mixed()
    expected = 20.0 * np.log10(np.abs(network.mode_parameter(D, D, 1, 0)))

    values = format_mixed_mode_parameter(network, D, D, 1, 0, SParameterFormat.LOG_MAG)

    np.testing.assert_allclose(values, expected)


def test_differential_reflection_uses_the_differential_impedance() -> None:
    """SDD11 impedance must reference 2*z0, not the single-ended z0."""

    network = mixed()
    gamma = network.mode_parameter(D, D, 0, 0)
    expected = (network.z0_differential * (1.0 + gamma) / (1.0 - gamma)).real

    values = format_mixed_mode_parameter(
        network, D, D, 0, 0, SParameterFormat.IMPEDANCE_REAL
    )

    np.testing.assert_allclose(values, expected)


def test_common_reflection_uses_the_common_impedance() -> None:
    network = mixed()
    gamma = network.mode_parameter(C, C, 0, 0)
    expected = (network.z0_common * (1.0 + gamma) / (1.0 - gamma)).real

    values = format_mixed_mode_parameter(
        network, C, C, 0, 0, SParameterFormat.IMPEDANCE_REAL
    )

    np.testing.assert_allclose(values, expected)


def test_impedance_format_is_rejected_for_mode_conversion() -> None:
    with pytest.raises(InputValidationError, match="reflection parameters"):
        format_mixed_mode_parameter(mixed(), D, C, 0, 0, SParameterFormat.IMPEDANCE_REAL)


def test_trace_is_named_and_has_units() -> None:
    trace = create_mixed_mode_trace(mixed(), D, D, 1, 0, SParameterFormat.LOG_MAG)

    assert trace.name == "SDD21 Log Mag"
    assert trace.x_unit == "Hz"
    assert trace.y_unit == "dB"
    assert trace.n_points == len(FREQUENCIES)
