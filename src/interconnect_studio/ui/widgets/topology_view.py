"""Schematic of a DUT topology.

Drawn rather than shipped as images so it follows the theme and stays
readable at any size. Ports sit in ascending order on each side, so a
crossed topology shows its through paths actually crossing.
"""

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

from interconnect_studio.algorithms.mixed_mode import Topology
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme, palette_for

_MARGIN = 10.0
_PORT_RADIUS = 3.0
_LABEL_WIDTH = 34.0
_LINE_WIDTH = 2


class TopologyView(QWidget):
    """Draws one DUT topology: ports, the DUT body, and the through paths."""

    def __init__(
        self,
        topology: Topology,
        parent: QWidget | None = None,
        theme: Theme = DEFAULT_THEME,
    ) -> None:
        super().__init__(parent)
        self._topology = topology
        self._theme = theme
        self.setMinimumSize(QSize(170, 96))
        self.setToolTip(f"{topology.name}\n{topology.description}")

    @property
    def topology(self) -> Topology:
        """Topology being drawn."""

        return self._topology

    def set_topology(self, topology: Topology) -> None:
        """Draw a different topology."""

        self._topology = topology
        self.setToolTip(f"{topology.name}\n{topology.description}")
        self.update()

    def apply_theme(self, theme: Theme) -> None:
        """Redraw in another theme."""

        self._theme = theme
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        """Preferred size of the schematic."""

        return QSize(200, 110)

    def paintEvent(self, event: QPaintEvent | None) -> None:  # noqa: N802
        """Render the schematic."""

        palette = palette_for(self._theme)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        left_ports = sorted(path[0] for path in self._topology.through)
        right_ports = sorted(path[1] for path in self._topology.through)

        body = QRectF(
            _MARGIN + _LABEL_WIDTH,
            _MARGIN,
            self.width() - 2.0 * (_MARGIN + _LABEL_WIDTH),
            self.height() - 2.0 * _MARGIN,
        )
        painter.setPen(QPen(QColor(palette.border), 1))
        painter.drawRoundedRect(body, 4.0, 4.0)

        font = QFont(painter.font())
        font.setPointSizeF(max(7.0, font.pointSizeF() - 1.0))
        painter.setFont(font)

        positions = {
            **self._side_positions(left_ports, body.left(), body),
            **self._side_positions(right_ports, body.right(), body),
        }

        painter.setPen(QPen(QColor(palette.accent), _LINE_WIDTH))
        for near, far in self._topology.through:
            painter.drawLine(positions[near], positions[far])

        for port, point in positions.items():
            on_left = point.x() <= body.left()
            self._draw_port(painter, port, point, on_left, palette.accent, palette.text)

        painter.end()

    def _side_positions(
        self,
        ports: list[int],
        x: float,
        body: QRectF,
    ) -> dict[int, QPointF]:
        step = body.height() / (len(ports) + 1)
        return {
            port: QPointF(x, body.top() + step * (index + 1))
            for index, port in enumerate(ports)
        }

    def _draw_port(
        self,
        painter: QPainter,
        port: int,
        point: QPointF,
        on_left: bool,
        marker_color: str,
        text_color: str,
    ) -> None:
        painter.setPen(QPen(QColor(marker_color), _LINE_WIDTH))
        painter.setBrush(Qt.GlobalColor.transparent)
        painter.drawEllipse(point, _PORT_RADIUS, _PORT_RADIUS)

        label_left = point.x() - _LABEL_WIDTH - _PORT_RADIUS if on_left else point.x()
        rect = QRectF(label_left, point.y() - 9.0, _LABEL_WIDTH, 18.0)
        alignment = (
            Qt.AlignmentFlag.AlignRight if on_left else Qt.AlignmentFlag.AlignLeft
        ) | Qt.AlignmentFlag.AlignVCenter
        painter.setPen(QPen(QColor(text_color), 1))
        painter.drawText(rect, int(alignment), f" {port + 1} ")
