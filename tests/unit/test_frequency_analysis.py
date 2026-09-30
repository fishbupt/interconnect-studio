"""Analytical measured-point checks, with no dependence on a GUI renderer."""

import csv
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.core import InputValidationError, Marker, PlotModel, Trace, TraceRecipe
from interconnect_studio.services.frequency_analysis import (
    add_marker,
    compare_trace,
    export_plot_csv,
    marker_reading,
    move_marker,
    remove_marker,
    rename_trace,
    reorder_trace,
    sample_index,
    search_marker,
    set_delta,
    step_marker,
)


def plot() -> PlotModel:
    return PlotModel(
        traces=(
            Trace(
                "S21",
                [1, 2, 4, 8],
                [-3, -1, -5, -2],
                x_unit="Hz",
                y_unit="dB",
                source_id="a",
                recipe=TraceRecipe(1, 0, "log_mag"),
            ),
            Trace(
                "S11",
                [1, 3, 7],
                [-10, -15, -12],
                x_unit="Hz",
                y_unit="dB",
                source_id="b",
                recipe=TraceRecipe(0, 0, "log_mag"),
            ),
        )
    )


@pytest.mark.parametrize("x,index", [(-100, 0), (1.5, 0), (1.6, 1), (3, 1), (100, 3)])
def test_nearest_sample_clamps_and_ties_choose_lower_frequency(x: float, index: int) -> None:
    assert sample_index(plot().traces[0], x) == index


@pytest.mark.parametrize("x", [math.nan, math.inf, -math.inf])
def test_invalid_marker_position_rejected(x: float) -> None:
    with pytest.raises(InputValidationError):
        add_marker(plot(), 0, x)


def test_marker_move_steps_and_delta_use_separate_measured_grids() -> None:
    original = plot()
    marked = add_marker(add_marker(original, 0, 2), 1, 3)
    marked = set_delta(marked, 2, 1)
    reading = marker_reading(marked, marked.markers[1])
    assert (reading.x, reading.y, reading.delta_x, reading.delta_y) == (3, -15, 1, -14)
    moved = move_marker(marked, 2, 100)
    assert moved.markers[1].x == 7
    assert step_marker(moved, 2, -100).markers[1].x == 1
    assert not original.markers
    np.testing.assert_array_equal(original.traces[0].y, [-3, -1, -5, -2])


@pytest.mark.parametrize(
    "kind,target,expected", [("min", None, 4), ("max", None, 2), ("target", -2.5, 1)]
)
def test_search_matches_hand_calculated_measured_results(
    kind: str, target: float | None, expected: float
) -> None:
    marked = add_marker(plot(), 0, 1)
    found = search_marker(marked, 1, kind, target=target)
    assert found.markers[0].x == expected


def test_visible_span_search_does_not_use_points_outside_range() -> None:
    marked = add_marker(plot(), 0, 1)
    found = search_marker(marked, 1, "min", span=(1, 3))
    assert found.markers[0].x == 1
    with pytest.raises(InputValidationError):
        search_marker(marked, 1, "max", span=(9, 10))


def test_search_skips_nonfinite_values_and_undefined_delta_is_not_zero() -> None:
    trace = Trace("null", [1, 2, 3], [-math.inf, math.nan, -4])
    marked = add_marker(add_marker(PlotModel(traces=(trace,)), 0, 1), 0, 1)
    marked = set_delta(marked, 2, 1)
    assert math.isnan(marker_reading(marked, marked.markers[1]).delta_y)
    assert search_marker(marked, 1, "min").markers[0].x == 3
    with pytest.raises(InputValidationError):
        search_marker(marked, 1, "max", span=(1, 2))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"number": 0, "trace_index": 0, "x": 1},
        {"number": True, "trace_index": 0, "x": 1},
        {"number": 1, "trace_index": -1, "x": 1},
        {"number": 1, "trace_index": 0, "x": math.nan},
        {"number": 1, "trace_index": 0, "x": 1, "reference_id": 1},
    ],
)
def test_marker_invariants(kwargs: dict[str, object]) -> None:
    with pytest.raises(InputValidationError):
        Marker(**kwargs)


def test_plot_rejects_missing_trace_out_of_span_duplicate_and_chained_delta() -> None:
    for markers in (
        (Marker(1, 2, 1),),
        (Marker(1, 0, 9),),
        (Marker(1, 0, 1), Marker(1, 1, 1)),
        (Marker(1, 0, 1, 2),),
    ):
        with pytest.raises(InputValidationError):
            replace(plot(), markers=markers)
    marked = add_marker(add_marker(add_marker(plot(), 0, 1), 0, 2), 1, 3)
    marked = set_delta(marked, 2, 1)
    with pytest.raises(InputValidationError):
        set_delta(marked, 3, 2)
    with pytest.raises(InputValidationError):
        set_delta(marked, 1, 2)


def test_delete_reorder_and_rename_keep_marker_attachments() -> None:
    marked = add_marker(add_marker(plot(), 0, 2), 1, 3)
    marked = set_delta(marked, 2, 1)
    renamed = rename_trace(marked, 0, "Channel A")
    reordered = reorder_trace(renamed, 0, 1)
    assert reordered.markers[0].trace_index == 1
    assert reordered.markers[1].trace_index == 0
    assert marker_reading(reordered, reordered.markers[1]).delta_y == -14
    deleted = reordered.remove_trace(1)
    assert len(deleted.markers) == 1
    assert deleted.markers[0].trace_index == 0 and deleted.markers[0].reference_id is None
    assert not remove_marker(deleted, 2).markers
    assert marked.traces[0].name == "S21"


def test_compare_preserves_source_and_unequal_frequency_grids() -> None:
    source = plot().traces[1]
    combined = compare_trace(PlotModel(traces=(plot().traces[0],)), source, "b", "测量 B")
    assert combined.traces[1].source_id == "b"
    assert combined.traces[1].name == "测量 B · S11"
    np.testing.assert_array_equal(combined.traces[1].x, [1, 3, 7])
    assert combined.traces[1].recipe == source.recipe
    bad = Trace("real", [1, 2], [0, 1], y_unit="dB", recipe=TraceRecipe(1, 0, "real"))
    with pytest.raises(InputValidationError):
        compare_trace(combined, bad, "c", "wrong format")


def test_trace_csv_roundtrip_preserves_values_units_names_sources_and_unequal_grids(
    tmp_path: Path,
) -> None:
    path = tmp_path / "traces.csv"
    export_plot_csv(plot(), path, {"a": "输入,测量", "b": "输出"})
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 7
    assert rows[0]["Source"] == "输入,测量"
    assert rows[0]["Source ID"] == "a"
    assert rows[-1]["X Unit"] == "Hz" and rows[-1]["Y Unit"] == "dB"
    assert [float(r["X"]) for r in rows[4:]] == [1, 3, 7]
    assert [float(r["Y"]) for r in rows[:4]] == [-3, -1, -5, -2]


def test_csv_write_failure_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "saved.csv"
    path.write_text("original")
    monkeypatch.setattr(
        "interconnect_studio.io.atomic.os.replace",
        lambda *_args: (_ for _ in ()).throw(OSError("disk full")),
    )
    with pytest.raises(OSError):
        export_plot_csv(plot(), path, {})
    assert path.read_text() == "original"
    assert list(tmp_path.iterdir()) == [path]
