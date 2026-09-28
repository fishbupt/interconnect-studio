"""Schematic of a DUT configuration.

Drawn rather than shipped as images so it follows the theme and stays
readable at any size. Ports sit in ascending order on each side, so a
crossed topology shows its through paths actually crossing.

A differential end is drawn as its two ports joined by a bracket: one
logical port made of two conductors. A line with no far end -- a
reflection-only DUT, or a port with no through partner asserted -- gets a
stub into the DUT body instead of a path across it.
"""

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

from interconnect_studio.core import DutConfiguration
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme, palette_for

_MARGIN = 10.0
_PORT_RADIUS = 3.0
_LABEL_WIDTH = 22.0
_LINE_WIDTH = 2
# The bracket sits between the port and its label, so the label has to
# clear it; otherwise the digits paint over the grouping mark.
_BRACKET_OFFSET = 9.0
_BRACKET_TICK = 4.0
_LABEL_GAP = _BRACKET_OFFSET + 5.0
_STUB_LENGTH = 14.0


class DutConfigurationView(QWidget):
    """Draws one DUT configuration: ports, the DUT body, and its paths."""

    def __init__(
        self,
        configuration: DutConfiguration,
        parent: QWidget | None = None,
        theme: Theme = DEFAULT_THEME,
    ) -> None:
        super().__init__(parent)
        self._configuration = configuration
        self._theme = theme
        self.setMinimumSize(QSize(170, 96))
        self.setToolTip(self._tooltip())

    @property
    def configuration(self) -> DutConfiguration:
        """Configuration being drawn."""

        return self._configuration

    def set_configuration(self, configuration: DutConfiguration) -> None:
        """Draw a different configuration."""

        self._configuration = configuration
        self.setToolTip(self._tooltip())
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

        side = _LABEL_WIDTH + _LABEL_GAP
        body = QRectF(
            _MARGIN + side,
            _MARGIN,
            self.width() - 2.0 * (_MARGIN + side),
            self.height() - 2.0 * _MARGIN,
        )
        painter.setPen(QPen(QColor(palette.border), 1))
        painter.drawRoundedRect(body, 4.0, 4.0)

        font = QFont(painter.font())
        font.setPointSizeF(max(7.0, font.pointSizeF() - 1.0))
        painter.setFont(font)

        left_ends = [line.near for line in self._configuration.port_group.lines]
        right_ends = [line.far for line in self._configuration.port_group.lines if line.far]
        positions = {
            **self._side_positions(left_ends, body.left(), body),
            **self._side_positions(right_ends, body.right(), body),
        }

        painter.setPen(QPen(QColor(palette.accent), _LINE_WIDTH))
        for line in self._configuration.port_group.lines:
            for near_port, far_port in _conductors(line.near, line.far):
                painter.drawLine(positions[near_port], positions[far_port])
            if not line.far:
                # No through partner: show the path entering the DUT and
                # stopping, rather than implying a connection that was never
                # claimed.
                for port in line.near:
                    stub = positions[port]
                    painter.drawLine(stub, QPointF(stub.x() + _STUB_LENGTH, stub.y()))

        for line in self._configuration.port_group.lines:
            for end in line.ends:
                on_left = end is line.near
                if len(end) == 2:
                    self._draw_bracket(painter, positions, end, on_left, palette.accent)
                for port in end:
                    self._draw_port(
                        painter, port, positions[port], on_left, palette.accent, palette.text
                    )

        painter.end()

    def _tooltip(self) -> str:
        return f"{self._configuration.name}\n{self._configuration.topology_summary}"

    def _side_positions(
        self,
        ends: list[tuple[int, ...]],
        x: float,
        body: QRectF,
    ) -> dict[int, QPointF]:
        """Place one side's ports, ascending, with pairs kept adjacent."""

        ports = sorted(port for end in ends for port in end)
        step = body.height() / (len(ports) + 1)
        return {
            port: QPointF(x, body.top() + step * (index + 1))
            for index, port in enumerate(ports)
        }

    def _draw_bracket(
        self,
        painter: QPainter,
        positions: dict[int, QPointF],
        end: tuple[int, ...],
        on_left: bool,
        color: str,
    ) -> None:
        """Join a differential end's two conductors into one logical port."""

        first, second = (positions[port] for port in end)
        offset = -_BRACKET_OFFSET if on_left else _BRACKET_OFFSET
        tick = _BRACKET_TICK if on_left else -_BRACKET_TICK
        x = first.x() + offset
        painter.setPen(QPen(QColor(color), 1))
        painter.drawLine(QPointF(x, first.y()), QPointF(x, second.y()))
        for point in (first, second):
            painter.drawLine(QPointF(x, point.y()), QPointF(x + tick, point.y()))

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

        label_left = (
            point.x() - _LABEL_WIDTH - _LABEL_GAP if on_left else point.x() + _LABEL_GAP
        )
        rect = QRectF(label_left, point.y() - 9.0, _LABEL_WIDTH, 18.0)
        alignment = (
            Qt.AlignmentFlag.AlignRight if on_left else Qt.AlignmentFlag.AlignLeft
        ) | Qt.AlignmentFlag.AlignVCenter
        painter.setPen(QPen(QColor(text_color), 1))
        painter.drawText(rect, int(alignment), str(port + 1))


def _conductors(
    near: tuple[int, ...],
    far: tuple[int, ...],
) -> tuple[tuple[int, int], ...]:
    """Which near port connects to which far port.

    Ends of equal size join conductor to conductor, positive to positive.
    Ends of different size are a mode converter -- a balun -- where every
    conductor meets the single one on the other side.
    """

    if not far:
        return ()
    if len(near) == len(far):
        return tuple(zip(near, far, strict=True))
    return tuple((start, end) for start in near for end in far)
