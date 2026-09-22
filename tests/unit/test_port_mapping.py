import numpy as np
import pytest

from interconnect_studio.algorithms.network import remap_ports
from interconnect_studio.core import InputValidationError, Network


def make_labeled_network(n_ports: int = 4) -> Network:
    s = np.empty((2, n_ports, n_ports), dtype=np.complex128)
    for freq_index in range(2):
        for row in range(n_ports):
            for column in range(n_ports):
                s[freq_index, row, column] = (
                    100 * freq_index + 10 * (row + 1) + (column + 1)
                )

    return Network(
        frequencies_hz=[1.0e9, 2.0e9],
        s=s,
        z0=50.0,
        port_names=tuple(f"P{index + 1}" for index in range(n_ports)),
    )


def test_remap_ports_reorders_both_s_matrix_axes() -> None:
    network = make_labeled_network()
    order = (2, 0, 3, 1)

    mapped = remap_ports(network, order)

    for freq_index in range(network.n_freq):
        for new_row, old_row in enumerate(order):
            for new_column, old_column in enumerate(order):
                assert mapped.s[freq_index, new_row, new_column] == (
                    network.s[freq_index, old_row, old_column]
                )


def test_remap_ports_preserves_frequency_axis_and_z0() -> None:
    network = make_labeled_network()

    mapped = remap_ports(network, (1, 0, 3, 2))

    np.testing.assert_array_equal(mapped.frequencies_hz, network.frequencies_hz)
    assert mapped.z0 == network.z0


def test_remap_ports_reorders_port_names() -> None:
    network = make_labeled_network()

    mapped = remap_ports(network, (2, 0, 3, 1))

    assert mapped.port_names == ("P3", "P1", "P4", "P2")


def test_remap_ports_keeps_none_port_names() -> None:
    source = make_labeled_network()
    network = Network(source.frequencies_hz, source.s, z0=source.z0)

    mapped = remap_ports(network, (3, 2, 1, 0))

    assert mapped.port_names is None


def test_remap_ports_identity_returns_equal_data_but_new_network() -> None:
    network = make_labeled_network()

    mapped = remap_ports(network, (0, 1, 2, 3))

    assert mapped is not network
    np.testing.assert_array_equal(mapped.frequencies_hz, network.frequencies_hz)
    np.testing.assert_array_equal(mapped.s, network.s)
    assert mapped.port_names == network.port_names


def test_remap_ports_does_not_modify_source_network() -> None:
    network = make_labeled_network()
    original_s = network.s.copy()

    remap_ports(network, (3, 2, 1, 0))

    np.testing.assert_array_equal(network.s, original_s)
    assert network.port_names == ("P1", "P2", "P3", "P4")


@pytest.mark.parametrize(
    ("port_order", "message"),
    [
        ((0, 1, 2), "exactly 4 entries"),
        ((0, 1, 2, 2), "each port exactly once"),
        ((0, 1, 2, 4), "range"),
        ((0, 1, 2, -1), "range"),
        ((0, 1, 2, True), "integer port indices"),
    ],
)
def test_remap_ports_rejects_invalid_mapping(
    port_order: tuple[int, ...],
    message: str,
) -> None:
    network = make_labeled_network()

    with pytest.raises(InputValidationError, match=message):
        remap_ports(network, port_order)


def test_remap_ports_rejects_string_mapping() -> None:
    network = make_labeled_network()

    with pytest.raises(InputValidationError, match="sequence"):
        remap_ports(network, "0123")
