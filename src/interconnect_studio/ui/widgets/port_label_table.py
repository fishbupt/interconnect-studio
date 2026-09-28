"""Editable labels for a DUT's physical ports.

PLTS uses port labels in place of its ``<<<<`` / ``>>>>`` arrows, so they
describe the DUT rather than the file. Each row also shows which logical
port the physical port belongs to and, for a differential pair, which
conductor it is: labelling a four-port pair is guesswork otherwise.

Labels belong to the DUT, not to the topology chosen for it, so this widget
keeps them across changes of configuration and only re-reads the logical
port column.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.core import DutConfiguration

_VISIBLE_ROWS = 8


class PortLabelTable(QWidget):
    """One editable label per physical port, 1-based in the display."""

    labels_changed = pyqtSignal()

    def __init__(self, n_ports: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._n_ports = n_ports
        self.editors: list[QLineEdit] = []
        self._logical_labels: list[QLabel] = []

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        for port in range(n_ports):
            editor = QLineEdit(self)
            editor.setPlaceholderText("Label required")
            editor.textChanged.connect(self.labels_changed)
            logical = QLabel("", self)
            self.editors.append(editor)
            self._logical_labels.append(logical)
            grid.addWidget(QLabel(f"Port {port + 1}", self), port, 0)
            grid.addWidget(editor, port, 1)
            grid.addWidget(logical, port, 2)
        # Keep the rows together at the top instead of spreading them over
        # whatever height the dialog happens to have.
        grid.setRowStretch(n_ports, 1)

        rows = QWidget(self)
        rows.setLayout(grid)
        # A 32-port DUT would otherwise make the dialog taller than the
        # screen; a short DUT still sizes to its rows.
        area = QScrollArea(self)
        area.setWidget(rows)
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        if n_ports > _VISIBLE_ROWS:
            area.setMinimumHeight(rows.sizeHint().height() * _VISIBLE_ROWS // n_ports)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(area)

        self.set_labels(DutConfiguration.default_labels(n_ports))

    def labels(self) -> tuple[str, ...]:
        """Current labels, in physical port order."""

        return tuple(editor.text().strip() for editor in self.editors)

    def set_labels(self, labels: tuple[str, ...]) -> None:
        """Replace every label without emitting a change per keystroke."""

        for editor, label in zip(self.editors, labels, strict=True):
            editor.blockSignals(True)
            editor.setText(label)
            editor.blockSignals(False)
        self.labels_changed.emit()

    def is_valid(self) -> bool:
        """Whether every label is non-blank, which the domain model requires."""

        return all(label for label in self.labels())

    def show_logical_ports(self, configuration: DutConfiguration) -> None:
        """Re-read which logical port each physical port now belongs to."""

        for port, label in enumerate(self._logical_labels):
            logical = configuration.logical_port_of(port)
            if logical.is_differential:
                polarity = "+" if port == logical.dut_ports[0] else "−"
                label.setText(f"L{logical.number} {polarity}")
            else:
                label.setText(f"L{logical.number}")
