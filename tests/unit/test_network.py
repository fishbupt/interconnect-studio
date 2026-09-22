import numpy as np
import pytest

from interconnect_studio.core import InputValidationError, Network


def make_s(n_freq: int, n_ports: int) -> np.ndarray:
    return np.zeros((n_freq, n_ports, n_ports), dtype=np.complex128)


@pytest.mark.parametrize("n_ports", [1, 2, 4])
def test_network_accepts_valid_port_counts(n_ports: int) -> None:
    frequencies_hz = np.array([1.0e6, 2.0e6, 3.0e6])

    network = Network(frequencies_hz, make_s(3, n_ports), z0=50.0)

    assert network.n_freq == 3
    assert network.n_ports == n_ports
    assert network.z0 == 50.0 + 0.0j


def test_network_accepts_dc_as_first_frequency() -> None:
    network = Network([0.0, 1.0e6], make_s(2, 1), z0=50.0)

    np.testing.assert_array_equal(network.frequencies_hz, [0.0, 1.0e6])


def test_network_converts_numeric_input_to_canonical_dtypes() -> None:
    network = Network([1, 2], np.zeros((2, 1, 1), dtype=np.float32), z0=75)

    assert network.frequencies_hz.dtype == np.float64
    assert network.s.dtype == np.complex128
    assert isinstance(network.z0, complex)


def test_network_owns_input_arrays() -> None:
    frequencies_hz = np.array([1.0, 2.0])
    s = make_s(2, 1)

    network = Network(frequencies_hz, s, z0=50.0)

    frequencies_hz[0] = 10.0
    s[0, 0, 0] = 1.0

    assert network.frequencies_hz[0] == 1.0
    assert network.s[0, 0, 0] == 0.0


def test_network_internal_arrays_are_read_only() -> None:
    network = Network([1.0, 2.0], make_s(2, 1), z0=50.0)

    with pytest.raises(ValueError):
        network.frequencies_hz[0] = 10.0
    with pytest.raises(ValueError):
        network.s[0, 0, 0] = 1.0


def test_network_rejects_non_one_dimensional_frequencies() -> None:
    with pytest.raises(InputValidationError, match="one-dimensional"):
        Network([[1.0, 2.0]], make_s(2, 1), z0=50.0)


def test_network_rejects_empty_frequencies() -> None:
    with pytest.raises(InputValidationError, match="at least one point"):
        Network([], make_s(0, 1), z0=50.0)


@pytest.mark.parametrize(
    "frequencies_hz",
    [
        [1.0, 1.0],
        [2.0, 1.0],
        [1.0, np.nan],
        [-1.0, 1.0],
    ],
)
def test_network_rejects_invalid_frequency_axis(frequencies_hz: list[float]) -> None:
    with pytest.raises(InputValidationError):
        Network(frequencies_hz, make_s(2, 1), z0=50.0)


def test_network_rejects_frequency_count_mismatch() -> None:
    with pytest.raises(InputValidationError, match="frequency dimension"):
        Network([1.0, 2.0], make_s(3, 1), z0=50.0)


def test_network_rejects_non_square_s_matrix() -> None:
    with pytest.raises(InputValidationError, match="square"):
        Network([1.0, 2.0], np.zeros((2, 1, 2)), z0=50.0)


def test_network_rejects_non_three_dimensional_s() -> None:
    with pytest.raises(InputValidationError, match="shape"):
        Network([1.0, 2.0], np.zeros((2, 1)), z0=50.0)


def test_network_rejects_non_finite_s_values() -> None:
    s = make_s(2, 1)
    s[0, 0, 0] = np.nan

    with pytest.raises(InputValidationError, match="finite"):
        Network([1.0, 2.0], s, z0=50.0)


@pytest.mark.parametrize("z0", [0.0, np.nan, np.inf])
def test_network_rejects_invalid_z0(z0: float) -> None:
    with pytest.raises(InputValidationError):
        Network([1.0], make_s(1, 1), z0=z0)


def test_network_rejects_array_z0() -> None:
    with pytest.raises(InputValidationError, match="scalar"):
        Network([1.0], make_s(1, 1), z0=np.array([50.0, 50.0]))


def test_network_accepts_complex_scalar_z0() -> None:
    network = Network([1.0], make_s(1, 1), z0=50.0 + 2.0j)

    assert network.z0 == 50.0 + 2.0j


def test_network_accepts_valid_port_names() -> None:
    network = Network(
        [1.0],
        make_s(1, 2),
        z0=50.0,
        port_names=("Input", "Output"),
    )

    assert network.port_names == ("Input", "Output")


@pytest.mark.parametrize(
    "port_names",
    [
        ("Only one",),
        ("", "Port 2"),
        ("Port", "Port"),
    ],
)
def test_network_rejects_invalid_port_names(port_names: tuple[str, ...]) -> None:
    with pytest.raises(InputValidationError):
        Network([1.0], make_s(1, 2), z0=50.0, port_names=port_names)


def test_network_rejects_non_tuple_port_names() -> None:
    port_names = ["A", "B"]
    with pytest.raises(InputValidationError, match="tuple"):
        Network([1.0], make_s(1, 2), z0=50.0, port_names=port_names)  # type: ignore[arg-type]
