import pytest

from interconnect_studio.core import (
    InputValidationError,
    PlotKind,
    PlotModel,
    PlotTrace,
    Trace,
    YAxis,
)


def real_trace(name: str = "S21", y_unit: str = "dB") -> Trace:
    return Trace(name, [1.0, 2.0], [1.0, 2.0], x_unit="Hz", y_unit=y_unit)


def complex_trace(name: str = "S11") -> Trace:
    return Trace(name, [1.0, 2.0], [0.1 + 0.2j, 0.2 + 0.3j], x_unit="Hz")


def entries(*traces: Trace) -> tuple[PlotTrace, ...]:
    return tuple(PlotTrace(trace) for trace in traces)


def test_plot_model_defaults_to_empty_cartesian_plot() -> None:
    plot = PlotModel()

    assert plot.kind is PlotKind.CARTESIAN
    assert plot.traces == ()
    assert plot.n_traces == 0


def test_plot_model_add_trace_returns_new_model() -> None:
    plot = PlotModel(title="Magnitude", x_label="Frequency", y_label_left="Magnitude")
    trace = real_trace()

    updated = plot.add_trace(trace)

    assert plot.n_traces == 0
    assert updated.n_traces == 1
    assert updated.traces[0] is trace
    assert updated.title == plot.title


def test_plot_model_remove_trace_returns_new_model() -> None:
    first = real_trace("S11")
    second = real_trace("S21")
    plot = PlotModel(entries=entries(first, second))

    updated = plot.remove_trace(0)

    assert plot.n_traces == 2
    assert updated.traces == (second,)


@pytest.mark.parametrize("kind", [PlotKind.POLAR, PlotKind.SMITH])
def test_complex_plot_kinds_accept_complex_traces(kind: PlotKind) -> None:
    plot = PlotModel(entries=entries(complex_trace()), kind=kind)

    assert plot.n_traces == 1


def test_cartesian_plot_rejects_complex_trace() -> None:
    with pytest.raises(InputValidationError, match="real-valued"):
        PlotModel(entries=entries(complex_trace()), kind=PlotKind.CARTESIAN)


@pytest.mark.parametrize("kind", [PlotKind.POLAR, PlotKind.SMITH])
def test_complex_plot_kinds_reject_real_trace(kind: PlotKind) -> None:
    with pytest.raises(InputValidationError, match="complex-valued"):
        PlotModel(entries=entries(real_trace()), kind=kind)


def test_plot_model_rejects_mixed_x_units() -> None:
    first = real_trace("S11")
    second = Trace("S21", [1.0, 2.0], [1.0, 2.0], x_unit="s", y_unit="dB")

    with pytest.raises(InputValidationError, match="same x unit"):
        PlotModel(entries=entries(first, second))


def test_plot_model_rejects_mixed_y_units_on_same_axis() -> None:
    first = real_trace("S11")
    second = real_trace("S21", y_unit="degree")

    with pytest.raises(InputValidationError, match="left y axis"):
        PlotModel(entries=entries(first, second))


def test_plot_model_allows_different_y_units_across_axes() -> None:
    magnitude = real_trace("S21", y_unit="dB")
    phase = real_trace("S21 Phase", y_unit="degree")

    plot = PlotModel(
        entries=(PlotTrace(magnitude, YAxis.LEFT), PlotTrace(phase, YAxis.RIGHT)),
        y_label_left="Log Magnitude",
        y_label_right="Phase",
    )

    assert plot.traces_on(YAxis.LEFT) == (magnitude,)
    assert plot.traces_on(YAxis.RIGHT) == (phase,)


def test_plot_model_rejects_mixed_y_units_on_right_axis() -> None:
    left = real_trace("S11")
    first_right = real_trace("S21 Phase", y_unit="degree")
    second_right = real_trace("S21 Delay", y_unit="s")

    with pytest.raises(InputValidationError, match="right y axis"):
        PlotModel(
            entries=(
                PlotTrace(left, YAxis.LEFT),
                PlotTrace(first_right, YAxis.RIGHT),
                PlotTrace(second_right, YAxis.RIGHT),
            )
        )


def test_add_trace_places_trace_on_requested_axis() -> None:
    plot = PlotModel(entries=entries(real_trace("S11")))

    updated = plot.add_trace(real_trace("S21 Phase", y_unit="degree"), YAxis.RIGHT)

    assert updated.traces_on(YAxis.LEFT)[0].name == "S11"
    assert updated.traces_on(YAxis.RIGHT)[0].name == "S21 Phase"


def test_add_trace_defaults_to_left_axis() -> None:
    plot = PlotModel().add_trace(real_trace())

    assert plot.entries[0].y_axis is YAxis.LEFT


def test_remove_trace_keeps_axis_assignment_of_remaining_traces() -> None:
    plot = PlotModel(
        entries=(
            PlotTrace(real_trace("S11"), YAxis.LEFT),
            PlotTrace(real_trace("S21 Phase", y_unit="degree"), YAxis.RIGHT),
        )
    )

    updated = plot.remove_trace(0)

    assert updated.entries[0].y_axis is YAxis.RIGHT


def test_plot_model_rejects_invalid_remove_index() -> None:
    plot = PlotModel(entries=entries(real_trace()))

    with pytest.raises(InputValidationError, match="range"):
        plot.remove_trace(1)


def test_plot_model_is_immutable() -> None:
    plot = PlotModel(entries=entries(real_trace()))

    with pytest.raises(AttributeError):
        plot.title = "new"  # type: ignore[misc]


def test_plot_trace_rejects_non_trace() -> None:
    with pytest.raises(InputValidationError, match="must be a Trace"):
        PlotTrace("not a trace")  # type: ignore[arg-type]
