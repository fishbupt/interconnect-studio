import pytest

from interconnect_studio.core import InputValidationError, PlotKind, PlotModel, Trace


def real_trace(name: str = "S21", y_unit: str = "dB") -> Trace:
    return Trace(name, [1.0, 2.0], [1.0, 2.0], x_unit="Hz", y_unit=y_unit)


def complex_trace(name: str = "S11") -> Trace:
    return Trace(name, [1.0, 2.0], [0.1 + 0.2j, 0.2 + 0.3j], x_unit="Hz")


def test_plot_model_defaults_to_empty_cartesian_plot() -> None:
    plot = PlotModel()

    assert plot.kind is PlotKind.CARTESIAN
    assert plot.traces == ()
    assert plot.n_traces == 0


def test_plot_model_add_trace_returns_new_model() -> None:
    plot = PlotModel(title="Magnitude", x_label="Frequency", y_label="Magnitude")
    trace = real_trace()

    updated = plot.add_trace(trace)

    assert plot.n_traces == 0
    assert updated.n_traces == 1
    assert updated.traces[0] is trace
    assert updated.title == plot.title


def test_plot_model_remove_trace_returns_new_model() -> None:
    first = real_trace("S11")
    second = real_trace("S21")
    plot = PlotModel(traces=(first, second))

    updated = plot.remove_trace(0)

    assert plot.n_traces == 2
    assert updated.traces == (second,)


@pytest.mark.parametrize("kind", [PlotKind.POLAR, PlotKind.SMITH])
def test_complex_plot_kinds_accept_complex_traces(kind: PlotKind) -> None:
    plot = PlotModel(traces=(complex_trace(),), kind=kind)

    assert plot.n_traces == 1


def test_cartesian_plot_rejects_complex_trace() -> None:
    with pytest.raises(InputValidationError, match="real-valued"):
        PlotModel(traces=(complex_trace(),), kind=PlotKind.CARTESIAN)


@pytest.mark.parametrize("kind", [PlotKind.POLAR, PlotKind.SMITH])
def test_complex_plot_kinds_reject_real_trace(kind: PlotKind) -> None:
    with pytest.raises(InputValidationError, match="complex-valued"):
        PlotModel(traces=(real_trace(),), kind=kind)


def test_plot_model_rejects_mixed_x_units() -> None:
    first = real_trace("S11")
    second = Trace("S21", [1.0, 2.0], [1.0, 2.0], x_unit="s", y_unit="dB")

    with pytest.raises(InputValidationError, match="same x unit"):
        PlotModel(traces=(first, second))


def test_plot_model_rejects_mixed_y_units() -> None:
    """One plot carries one display format, so one y unit."""

    first = real_trace("S11")
    second = real_trace("S21 Phase", y_unit="degree")

    with pytest.raises(InputValidationError, match="same y unit"):
        PlotModel(traces=(first, second))


def test_plot_model_rejects_invalid_remove_index() -> None:
    plot = PlotModel(traces=(real_trace(),))

    with pytest.raises(InputValidationError, match="range"):
        plot.remove_trace(1)


def test_plot_model_is_immutable() -> None:
    plot = PlotModel(traces=(real_trace(),))

    with pytest.raises(AttributeError):
        plot.title = "new"  # type: ignore[misc]
