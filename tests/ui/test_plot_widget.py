import pytest
from PyQt6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from interconnect_studio.core import PlotKind, PlotModel, Trace
from interconnect_studio.ui.theme import Theme, palette_for
from interconnect_studio.ui.widgets import CartesianPlotWidget


def magnitude() -> Trace:
    return Trace("S21 Log Mag", [1.0, 2.0], [-10.0, -20.0], x_unit="Hz", y_unit="dB")


def test_cartesian_plot_widget_accepts_plot_model(qtbot: QtBot) -> None:
    widget = CartesianPlotWidget()
    qtbot.addWidget(widget)
    model = PlotModel(
        traces=(magnitude(),),
        title="Example",
        x_label="Frequency",
        y_label="Magnitude",
    )

    widget.set_plot_model(model)

    assert isinstance(widget, QWidget)
    assert widget.model is model


def test_cartesian_plot_widget_rejects_non_cartesian_model(qtbot: QtBot) -> None:
    widget = CartesianPlotWidget()
    qtbot.addWidget(widget)
    complex_trace = Trace("S11", [1.0, 2.0], [0.1 + 0.2j, 0.2 + 0.3j], x_unit="Hz")
    model = PlotModel(traces=(complex_trace,), kind=PlotKind.SMITH)

    with pytest.raises(ValueError, match="only supports Cartesian"):
        widget.set_plot_model(model)


def test_plot_has_a_single_y_axis(qtbot: QtBot) -> None:
    widget = CartesianPlotWidget()
    qtbot.addWidget(widget)

    widget.set_plot_model(PlotModel(traces=(magnitude(),)))

    assert widget._plot_item.getAxis("right").isVisible() is False


def test_axis_units_are_set_for_si_prefix_scaling(qtbot: QtBot) -> None:
    widget = CartesianPlotWidget()
    qtbot.addWidget(widget)
    model = PlotModel(
        traces=(magnitude(),),
        x_label="Frequency",
        y_label="Log Magnitude",
    )

    widget.set_plot_model(model)

    assert widget._plot_item.getAxis("bottom").labelUnits == "Hz"
    assert widget._plot_item.getAxis("left").labelUnits == "dB"


def test_widget_defaults_to_light_theme(qtbot: QtBot) -> None:
    widget = CartesianPlotWidget()
    qtbot.addWidget(widget)

    assert widget.theme is Theme.LIGHT


def test_apply_theme_switches_background(qtbot: QtBot) -> None:
    widget = CartesianPlotWidget()
    qtbot.addWidget(widget)
    widget.set_plot_model(PlotModel(traces=(magnitude(),)))

    widget.apply_theme(Theme.DARK)

    assert widget.theme is Theme.DARK
    expected = palette_for(Theme.DARK).surface
    assert widget.plot_widget.backgroundBrush().color().name() == expected


def test_apply_theme_keeps_plot_model(qtbot: QtBot) -> None:
    widget = CartesianPlotWidget()
    qtbot.addWidget(widget)
    model = PlotModel(traces=(magnitude(),))
    widget.set_plot_model(model)

    widget.apply_theme(Theme.DARK)

    assert widget.model is model
