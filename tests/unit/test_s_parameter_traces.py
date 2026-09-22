import numpy as np

from interconnect_studio.algorithms.network import (
    SParameterFormat,
    create_s_parameter_trace,
    plot_kind_for_s_parameter_format,
)
from interconnect_studio.core import Network, PlotKind


def make_network() -> Network:
    s = np.zeros((2, 2, 2), dtype=np.complex128)
    s[:, 1, 0] = [1.0 + 0.0j, 0.1 + 0.0j]
    s[:, 0, 0] = [0.2 + 0.1j, 0.3 + 0.2j]
    return Network([1.0e9, 2.0e9], s, z0=50.0)


def test_create_s_parameter_trace_builds_name_units_and_values() -> None:
    trace = create_s_parameter_trace(make_network(), 1, 0, SParameterFormat.LOG_MAG)

    assert trace.name == "S21 Log Mag"
    assert trace.x_unit == "Hz"
    assert trace.y_unit == "dB"
    np.testing.assert_allclose(trace.x, [1.0e9, 2.0e9])
    np.testing.assert_allclose(trace.y, [0.0, -20.0], atol=1e-12)


def test_create_s_parameter_trace_uses_engineering_one_based_name() -> None:
    trace = create_s_parameter_trace(make_network(), 0, 0, "phase")

    assert trace.name == "S11 Phase"
    assert trace.y_unit == "degree"


def test_create_s_parameter_trace_supports_complex_smith_data() -> None:
    trace = create_s_parameter_trace(make_network(), 0, 0, "smith")

    assert trace.name == "S11 Smith"
    assert trace.is_complex is True
    assert trace.y_unit == ""


def test_plot_kind_for_standard_formats_is_cartesian() -> None:
    assert plot_kind_for_s_parameter_format("log_mag") is PlotKind.CARTESIAN
    assert plot_kind_for_s_parameter_format("group_delay") is PlotKind.CARTESIAN


def test_plot_kind_for_polar_and_smith() -> None:
    assert plot_kind_for_s_parameter_format("polar") is PlotKind.POLAR
    assert plot_kind_for_s_parameter_format("smith") is PlotKind.SMITH
