from PyQt6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from interconnect_studio.core import PlotModel, Trace
from interconnect_studio.ui.widgets import CartesianPlotWidget


def test_cartesian_plot_widget_accepts_plot_model(qtbot: QtBot) -> None:
    widget = CartesianPlotWidget()
    qtbot.addWidget(widget)
    trace = Trace("S21 Log Mag", [1.0, 2.0], [-10.0, -20.0], x_unit="Hz", y_unit="dB")
    model = PlotModel(traces=(trace,), title="Example", x_label="Frequency", y_label="Magnitude")

    widget.set_plot_model(model)

    assert isinstance(widget, QWidget)
    assert widget.model is model
