"""'Limit Data Range to Import' group shared by the import dialogs.

Matches the PLTS group: All / Subset, Start, Stop, Points, Step, Interpolate
and Reset. Only the range can be narrowed; Points and Step show what the
measured data gives inside the range and cannot be edited, and Interpolate
stays off, because Interconnect Studio never resamples imported data.
Frequencies are shown in MHz, as in PLTS, and converted to Hz here.
"""

from typing import Final

import numpy as np
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QRadioButton,
    QWidget,
)

from interconnect_studio.algorithms.network import subset_point_count
from interconnect_studio.core import Network
from interconnect_studio.services import FrequencyRange

_HZ_PER_MHZ: Final[float] = 1.0e6
_NO_RESAMPLING: Final[str] = (
    "Changing points or step needs interpolation, which Interconnect Studio does not do."
)


class FrequencyRangeBox(QGroupBox):
    """All / Subset selector for a network's measured frequency range."""

    changed = pyqtSignal()

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._network: Network | None = None

        self.all_radio = QRadioButton("All", self)
        self.subset_radio = QRadioButton("Subset", self)
        self.all_radio.setChecked(True)
        self.interpolate_check = QCheckBox("Interpolate", self)
        self.interpolate_check.setEnabled(False)
        self.interpolate_check.setToolTip(_NO_RESAMPLING)

        self.start_spin = self._frequency_spin()
        self.stop_spin = self._frequency_spin()
        self.points_value = QLabel("-", self)
        self.step_value = QLabel("-", self)
        self.points_value.setToolTip(_NO_RESAMPLING)
        self.step_value.setToolTip(_NO_RESAMPLING)
        self.reset_button = QPushButton("Reset", self)

        grid = QGridLayout(self)
        grid.addWidget(self.all_radio, 0, 0)
        grid.addWidget(self.subset_radio, 0, 1)
        grid.addWidget(self.interpolate_check, 0, 2)
        grid.addWidget(QLabel("Start (MHz)", self), 1, 0)
        grid.addWidget(QLabel("Points", self), 1, 1)
        grid.addWidget(self.start_spin, 2, 0)
        grid.addWidget(self.points_value, 2, 1)
        grid.addWidget(QLabel("Stop (MHz)", self), 3, 0)
        grid.addWidget(QLabel("Step (MHz)", self), 3, 1)
        grid.addWidget(self.stop_spin, 4, 0)
        grid.addWidget(self.step_value, 4, 1)
        grid.addWidget(self.reset_button, 4, 2)

        self.all_radio.toggled.connect(self._refresh)
        self.start_spin.valueChanged.connect(self._refresh)
        self.stop_spin.valueChanged.connect(self._refresh)
        self.reset_button.clicked.connect(self.reset)
        self.set_network(None)

    def set_network(self, network: Network | None) -> None:
        """Show the range of a network, or disable the group without one."""

        self._network = network
        self.setEnabled(network is not None)
        if network is not None:
            low = float(network.frequencies_hz[0]) / _HZ_PER_MHZ
            high = float(network.frequencies_hz[-1]) / _HZ_PER_MHZ
            for spin in (self.start_spin, self.stop_spin):
                spin.blockSignals(True)
                spin.setRange(low, high)
                spin.blockSignals(False)
        self.reset()

    def reset(self) -> None:
        """Return Start and Stop to the full measured range."""

        if self._network is not None:
            self.start_spin.setValue(self.start_spin.minimum())
            self.stop_spin.setValue(self.stop_spin.maximum())
        self._refresh()

    def frequency_range(self) -> FrequencyRange | None:
        """Selected range in Hz, or None for All."""

        if self.all_radio.isChecked() or self._network is None:
            return None
        return FrequencyRange(
            start_hz=self._to_hz(self.start_spin.value(), is_start=True),
            stop_hz=self._to_hz(self.stop_spin.value(), is_start=False),
        )

    def point_count(self) -> int:
        """Points the current selection keeps."""

        if self._network is None:
            return 0
        selected = self.frequency_range()
        if selected is None:
            return self._network.n_freq
        return subset_point_count(self._network, selected.start_hz, selected.stop_hz)

    def _to_hz(self, value_mhz: float, *, is_start: bool) -> float:
        # The spin boxes round to their decimals; snap the box limits back to
        # the exact measured end points so "full range" never drops a point.
        if self._network is None:
            return value_mhz * _HZ_PER_MHZ
        frequencies = self._network.frequencies_hz
        if is_start and value_mhz <= self.start_spin.minimum():
            return float(frequencies[0])
        if not is_start and value_mhz >= self.stop_spin.maximum():
            return float(frequencies[-1])
        return value_mhz * _HZ_PER_MHZ

    def _refresh(self) -> None:
        subset = self.subset_radio.isChecked() and self._network is not None
        self.start_spin.setEnabled(subset)
        self.stop_spin.setEnabled(subset)
        self.reset_button.setEnabled(subset)
        count = self.point_count()
        self.points_value.setText(str(count) if self._network is not None else "-")
        self.step_value.setText(self._step_text())
        self.changed.emit()

    def _step_text(self) -> str:
        if self._network is None:
            return "-"
        selected = self.frequency_range()
        frequencies = self._network.frequencies_hz
        if selected is not None:
            frequencies = frequencies[
                (frequencies >= selected.start_hz) & (frequencies <= selected.stop_hz)
            ]
        if frequencies.size < 2:
            return "-"
        steps = np.diff(frequencies)
        if np.allclose(steps, steps[0], rtol=1e-6):
            return f"{steps[0] / _HZ_PER_MHZ:g}"
        return "non-uniform"

    def _frequency_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox(self)
        spin.setDecimals(6)
        spin.setKeyboardTracking(False)
        return spin
