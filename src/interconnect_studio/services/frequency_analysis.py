"""Measured-point marker and trace operations; no GUI or resampling."""

import csv
import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

import numpy as np

from interconnect_studio.core import InputValidationError, Marker, PlotModel, Trace
from interconnect_studio.io.atomic import atomic_destination


@dataclass(frozen=True, slots=True)
class MarkerReading:
    """Actual measured point and optional delta, in the trace's axis units."""

    x: float
    y: float
    delta_x: float | None = None
    delta_y: float | None = None


def sample_index(trace: Trace, x: float) -> int:
    """Nearest measured x, clamped to span; equal distance selects the lower point."""

    if not math.isfinite(x):
        raise InputValidationError("Marker position must be finite.")
    index = int(np.searchsorted(trace.x, x))
    if index == trace.n_points:
        return index - 1
    if index > 0 and x - trace.x[index - 1] <= trace.x[index] - x:
        return index - 1
    return index


def marker_reading(plot: PlotModel, marker: Marker) -> MarkerReading:
    """Read a real-valued trace at the nearest sample, with no interpolation.

    Nonfinite absolute y values are retained. An undefined delta is NaN and
    must be displayed as unavailable, never silently replaced by zero.
    """

    trace = plot.traces[marker.trace_index]
    if trace.is_complex:
        raise InputValidationError("Frequency markers currently require a Cartesian trace.")
    index = sample_index(trace, marker.x)
    x, y = float(trace.x[index]), float(trace.y[index])
    if marker.reference_id is None:
        return MarkerReading(x, y)
    reference = next(m for m in plot.markers if m.number == marker.reference_id)
    base = marker_reading(plot, reference)
    delta_y = y - base.y if math.isfinite(y) and math.isfinite(base.y) else math.nan
    return MarkerReading(x, y, x - base.x, delta_y)


def add_marker(plot: PlotModel, trace_index: int, x: float) -> PlotModel:
    """Add an absolute marker at a measured point, assigning the next free number."""

    trace = _trace(plot, trace_index)
    if trace.is_complex:
        raise InputValidationError("Markers require a real-valued trace.")
    number = max((m.number for m in plot.markers), default=0) + 1
    marker = Marker(number, trace_index, float(trace.x[sample_index(trace, x)]))
    return replace(plot, markers=(*plot.markers, marker))


def move_marker(plot: PlotModel, number: int, x: float) -> PlotModel:
    """Snap a marker to a measured point and preserve its delta reference."""

    marker = _marker(plot, number)
    trace = plot.traces[marker.trace_index]
    moved = replace(marker, x=float(trace.x[sample_index(trace, x)]))
    return replace(plot, markers=tuple(moved if m.number == number else m for m in plot.markers))


def step_marker(plot: PlotModel, number: int, step: int) -> PlotModel:
    """Move by measured samples, clamping at either endpoint."""

    marker = _marker(plot, number)
    trace = plot.traces[marker.trace_index]
    index = min(max(sample_index(trace, marker.x) + step, 0), trace.n_points - 1)
    return move_marker(plot, number, float(trace.x[index]))


def remove_marker(plot: PlotModel, number: int) -> PlotModel:
    """Remove a marker and return dependants to absolute readout."""

    _marker(plot, number)
    return replace(
        plot,
        markers=tuple(
            replace(m, reference_id=None) if m.reference_id == number else m
            for m in plot.markers
            if m.number != number
        ),
    )


def set_delta(plot: PlotModel, number: int, reference_id: int | None) -> PlotModel:
    """Set a delta reference; PlotModel rejects chains, cycles and missing references."""

    marker = replace(_marker(plot, number), reference_id=reference_id)
    return replace(plot, markers=tuple(marker if m.number == number else m for m in plot.markers))


def search_marker(
    plot: PlotModel,
    number: int,
    kind: Literal["min", "max", "target"],
    *,
    target: float | None = None,
    span: tuple[float, float] | None = None,
) -> PlotModel:
    """Find a finite measured minimum/maximum or closest measured y to target.

    Full trace or inclusive x span; ties select lowest frequency. This is a
    sampled target search, not an interpolated crossing or 3-dB bandwidth.
    """

    marker = _marker(plot, number)
    trace = plot.traces[marker.trace_index]
    if trace.is_complex:
        raise InputValidationError("Marker search requires a real-valued trace.")
    valid = np.isfinite(trace.y)
    if span is not None:
        if not all(math.isfinite(v) for v in span) or span[0] > span[1]:
            raise InputValidationError("Search span must be finite and increasing.")
        valid &= (trace.x >= span[0]) & (trace.x <= span[1])
    indices = np.flatnonzero(valid)
    if not indices.size:
        raise InputValidationError("Search span contains no finite measured values.")
    values = trace.y[indices]
    if kind == "min":
        selected = int(np.argmin(values))
    elif kind == "max":
        selected = int(np.argmax(values))
    elif kind == "target":
        if target is None or not math.isfinite(target):
            raise InputValidationError("Target must be finite.")
        selected = int(np.argmin(np.abs(values - target)))
    else:
        raise InputValidationError("Unknown marker search.")
    return move_marker(plot, number, float(trace.x[indices[selected]]))


def renamed_trace(trace: Trace, name: str, source_id: str | None = None) -> Trace:
    """Copy a trace with a new display name/provenance, preserving its recipe."""

    return Trace(
        name,
        trace.x,
        trace.y,
        x_unit=trace.x_unit,
        y_unit=trace.y_unit,
        source_id=trace.source_id if source_id is None else source_id,
        recipe=trace.recipe,
    )


def rename_trace(plot: PlotModel, index: int, name: str) -> PlotModel:
    """Rename a trace without invalidating its index-based markers."""

    traces = list(plot.traces)
    traces[index] = renamed_trace(_trace(plot, index), name)
    return replace(plot, traces=tuple(traces))


def reorder_trace(plot: PlotModel, index: int, destination: int) -> PlotModel:
    """Change legend/drawing order and keep every marker attached to its trace."""

    _trace(plot, index)
    _trace(plot, destination)
    order = list(range(len(plot.traces)))
    order.insert(destination, order.pop(index))
    markers = tuple(replace(m, trace_index=order.index(m.trace_index)) for m in plot.markers)
    return replace(plot, traces=tuple(plot.traces[i] for i in order), markers=markers)


def compare_trace(plot: PlotModel, trace: Trace, source_id: str, source_name: str) -> PlotModel:
    """Overlay an existing trace from an open source, preserving its original grid.

    Require identical display format when recipes exist. For older mixed-mode
    traces without recipes, axis labels supplied by the caller must also match.
    """

    for current in plot.traces:
        if current.recipe is not None and trace.recipe is not None:
            if current.recipe.data_format != trace.recipe.data_format:
                raise InputValidationError("请选择相同显示格式的曲线进行对比。")
    copied = renamed_trace(trace, f"{source_name} · {trace.name}", source_id)
    return plot.add_trace(copied)


def export_plot_csv(plot: PlotModel, path: str | Path, sources: Mapping[str, str]) -> None:
    """Atomically write all trace samples as long-form UTF-8 CSV.

    Separate x/y per trace preserve unequal frequency grids; axis units,
    source IDs and display names are explicit. This exports displayed values,
    not a reconstructed S matrix. Complex y is rejected.
    """

    if any(trace.is_complex for trace in plot.traces):
        raise InputValidationError("Trace CSV currently requires Cartesian data.")
    if not plot.traces:
        raise InputValidationError("There are no traces to export.")
    with (
        atomic_destination(Path(path)) as temporary,
        temporary.open("w", encoding="utf-8-sig", newline="") as stream,
    ):
        writer = csv.writer(stream)
        writer.writerow(["Trace", "Source ID", "Source", "X", "X Unit", "Y", "Y Unit"])
        for trace in plot.traces:
            for x, y in zip(trace.x, trace.y, strict=True):
                writer.writerow(
                    [
                        trace.name,
                        trace.source_id,
                        sources.get(trace.source_id, ""),
                        format(float(x), ".17g"),
                        trace.x_unit,
                        format(float(y), ".17g"),
                        trace.y_unit,
                    ]
                )


def _trace(plot: PlotModel, index: int) -> Trace:
    if type(index) is not int or not 0 <= index < len(plot.traces):
        raise InputValidationError("请选择一条曲线。")
    return plot.traces[index]


def _marker(plot: PlotModel, number: int) -> Marker:
    for marker in plot.markers:
        if marker.number == number:
            return marker
    raise InputValidationError("请选择一个 Marker。")
