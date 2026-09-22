import numpy as np
import pytest

from interconnect_studio.algorithms.network.formats import (
    SParameterFormat,
    format_s_parameter,
)
from interconnect_studio.core import InputValidationError, Network


def make_two_port(
    frequencies_hz: list[float],
    s11: list[complex],
    s21: list[complex] | None = None,
) -> Network:
    n_freq = len(frequencies_hz)
    s = np.zeros((n_freq, 2, 2), dtype=np.complex128)
    s[:, 0, 0] = s11
    if s21 is not None:
        s[:, 1, 0] = s21
    return Network(frequencies_hz, s, z0=50.0)


def test_log_mag() -> None:
    network = make_two_port([1.0, 2.0], [1.0 + 0j, 0.1 + 0j])
    result = format_s_parameter(network, 0, 0, SParameterFormat.LOG_MAG)
    np.testing.assert_allclose(result, [0.0, -20.0], atol=1e-12)


def test_log_mag_zero_returns_negative_infinity() -> None:
    network = make_two_port([1.0], [0.0 + 0j])
    result = format_s_parameter(network, 0, 0, "log_mag")
    assert np.isneginf(result[0])


def test_linear_mag() -> None:
    network = make_two_port([1.0], [3.0 + 4.0j])
    result = format_s_parameter(network, 0, 0, "linear_mag")
    np.testing.assert_allclose(result, [5.0])


def test_phase_is_wrapped_degrees() -> None:
    trace = np.exp(1j * np.deg2rad([170.0, -170.0]))
    network = make_two_port([1.0, 2.0], list(trace))
    result = format_s_parameter(network, 0, 0, "phase")
    np.testing.assert_allclose(result, [170.0, -170.0], atol=1e-12)


def test_unwrapped_phase_is_continuous_degrees() -> None:
    trace = np.exp(1j * np.deg2rad([170.0, -170.0, -150.0]))
    network = make_two_port([1.0, 2.0, 3.0], list(trace))
    result = format_s_parameter(network, 0, 0, "unwrapped_phase")
    np.testing.assert_allclose(result, [170.0, 190.0, 210.0], atol=1e-12)


def test_group_delay_for_linear_phase() -> None:
    delay_s = 0.25e-9
    frequencies_hz = np.array([1.0e9, 1.2e9, 1.7e9, 2.0e9])
    trace = np.exp(-1j * 2.0 * np.pi * frequencies_hz * delay_s)
    network = make_two_port(frequencies_hz.tolist(), [0j] * 4, list(trace))
    result = format_s_parameter(network, 1, 0, "group_delay")
    np.testing.assert_allclose(result, delay_s, rtol=1e-10, atol=1e-18)


def test_group_delay_requires_two_points() -> None:
    network = make_two_port([1.0], [0.0 + 0j], [1.0 + 0j])
    with pytest.raises(InputValidationError, match="at least two"):
        format_s_parameter(network, 1, 0, "group_delay")


def test_real_and_imaginary() -> None:
    network = make_two_port([1.0], [1.5 - 2.25j])
    real = format_s_parameter(network, 0, 0, "real")
    imaginary = format_s_parameter(network, 0, 0, "imaginary")
    np.testing.assert_allclose(real, [1.5])
    np.testing.assert_allclose(imaginary, [-2.25])


@pytest.mark.parametrize("data_format", ["smith", "polar"])
def test_smith_and_polar_preserve_complex_coefficient(data_format: str) -> None:
    network = make_two_port([1.0], [0.2 + 0.3j])
    result = format_s_parameter(network, 0, 0, data_format)
    np.testing.assert_allclose(result, [0.2 + 0.3j])
    assert np.iscomplexobj(result)


def test_swr() -> None:
    network = make_two_port([1.0], [0.5 + 0.0j])
    result = format_s_parameter(network, 0, 0, "swr")
    np.testing.assert_allclose(result, [3.0])


def test_impedance_formats() -> None:
    network = make_two_port([1.0], [0.2 + 0.0j])
    np.testing.assert_allclose(format_s_parameter(network, 0, 0, "impedance_real"), [75.0])
    np.testing.assert_allclose(format_s_parameter(network, 0, 0, "impedance_imaginary"), [0.0])
    np.testing.assert_allclose(format_s_parameter(network, 0, 0, "impedance_magnitude"), [75.0])
    np.testing.assert_allclose(
        format_s_parameter(network, 0, 0, "impedance_imaginary_magnitude"),
        [0.0],
    )
    np.testing.assert_allclose(format_s_parameter(network, 0, 0, "impedance_angle"), [0.0])


def test_quality_and_dissipation_factor_are_reciprocal() -> None:
    z = 50.0 + 100.0j
    gamma = (z - 50.0) / (z + 50.0)
    network = make_two_port([1.0], [gamma])
    q = format_s_parameter(network, 0, 0, "quality_factor")
    d = format_s_parameter(network, 0, 0, "dissipation_factor")
    np.testing.assert_allclose(q, [2.0], atol=1e-12)
    np.testing.assert_allclose(d, [0.5], atol=1e-12)


@pytest.mark.parametrize(
    "data_format",
    [
        "swr",
        "impedance_real",
        "impedance_imaginary",
        "impedance_magnitude",
        "impedance_imaginary_magnitude",
        "impedance_angle",
        "quality_factor",
        "dissipation_factor",
    ],
)
def test_reflection_only_formats_reject_transmission(data_format: str) -> None:
    network = make_two_port([1.0], [0.0 + 0j], [0.5 + 0j])
    with pytest.raises(InputValidationError, match="reflection"):
        format_s_parameter(network, 1, 0, data_format)


def test_invalid_format_is_rejected() -> None:
    network = make_two_port([1.0], [0.0 + 0j])
    with pytest.raises(InputValidationError, match="Unsupported"):
        format_s_parameter(network, 0, 0, "not-a-format")
