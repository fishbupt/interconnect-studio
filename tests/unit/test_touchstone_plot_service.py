from pathlib import Path

import numpy as np

from interconnect_studio.core import PlotKind
from interconnect_studio.services import TouchstonePlotService

DATA_DIR = Path(__file__).parents[1] / "data" / "touchstone"


def test_touchstone_plot_service_builds_default_s11_s21_logmag_plot() -> None:
    loaded = TouchstonePlotService().load_s2p(DATA_DIR / "valid_2port_ri.s2p")

    assert loaded.network.n_ports == 2
    assert loaded.plot.kind is PlotKind.CARTESIAN
    assert loaded.plot.n_traces == 2
    assert loaded.plot.traces[0].name == "S11 Log Mag"
    assert loaded.plot.traces[1].name == "S21 Log Mag"
    assert loaded.plot.traces[0].y_unit == "dB"
    assert loaded.plot.traces[1].y_unit == "dB"

    expected_s11 = 20.0 * np.log10(np.abs(loaded.network.s_parameter(0, 0)))
    expected_s21 = 20.0 * np.log10(np.abs(loaded.network.s_parameter(1, 0)))
    np.testing.assert_allclose(loaded.plot.traces[0].y, expected_s11)
    np.testing.assert_allclose(loaded.plot.traces[1].y, expected_s21)
