"""A/B overlays retain original samples and source identities."""

import numpy as np
import pytest

from interconnect_studio.algorithms.network import SParameterFormat
from interconnect_studio.core import DataFile, InputValidationError, Network
from interconnect_studio.services.comparison_view_service import comparison_layout


def data_file(key: str, frequencies: list[float]) -> DataFile:
    matrix = np.array([[[0.1, 0.2], [0.3, 0.4]]] * len(frequencies), dtype=complex)
    return DataFile(key, "same.s2p", Network(frequencies, matrix, 75))


def test_overlay_keeps_different_original_grids_and_matrix_mapping() -> None:
    a, b = data_file("A", [1e9, 3e9]), data_file("B", [2e9, 4e9, 5e9])
    layout = comparison_layout(a, b, SParameterFormat.LOG_MAG)
    assert (layout.rows, layout.cols) == (2, 2)
    assert [plot.title for plot in layout.plots] == ["S11", "S12", "S21", "S22"]
    for index, plot in enumerate(layout.plots):
        np.testing.assert_array_equal(plot.traces[0].x, a.network.frequencies_hz)
        np.testing.assert_array_equal(plot.traces[1].x, b.network.frequencies_hz)
        assert [trace.source_id for trace in plot.traces] == ["A", "B"]
        assert plot.traces[0].recipe.response_port == index // 2
        assert plot.traces[0].recipe.source_port == index % 2
        assert all(trace.y_unit == "dB" for trace in plot.traces)


def test_same_instance_rejected_but_same_named_distinct_files_allowed() -> None:
    a = data_file("A", [1e9])
    with pytest.raises(InputValidationError, match="不同"):
        comparison_layout(a, a, SParameterFormat.PHASE)
    b = data_file("B", [1e9])
    layout = comparison_layout(a, b, SParameterFormat.PHASE, (1, 0))
    assert layout.n_cells == 1
    assert all(trace.y_unit == "degree" for trace in layout.plots[0].traces)
