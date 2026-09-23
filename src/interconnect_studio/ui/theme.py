"""Application colour themes.

Dark is the default: instrument and EDA software is used for long sessions,
and coloured traces separate better against a dark surface. Light is a fully
stepped second theme, not an automatic inversion of the first.

The trace colours are a fixed categorical order, assigned by slot and never
cycled through a generator. Both sets pass colour-vision-deficiency
separation and normal-vision separation on their own surface. Three light
slots fall below 3:1 contrast against the light surface, so trace identity
must never rest on colour alone -- the plot legend names every trace.
"""

from dataclasses import dataclass
from enum import StrEnum

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


class Theme(StrEnum):
    """Selectable colour themes."""

    DARK = "dark"
    LIGHT = "light"


@dataclass(frozen=True, slots=True)
class Palette:
    """Colour tokens for one theme.

    Colour carries information, not decoration: ``trace_colors`` identifies
    series, while every piece of text uses ``text`` or ``muted_text``.
    """

    surface: str
    panel: str
    text: str
    muted_text: str
    border: str
    grid: str
    accent: str
    trace_colors: tuple[str, ...]


DARK = Palette(
    surface="#1a1a19",
    panel="#232322",
    text="#ffffff",
    muted_text="#c3c2b7",
    border="#3a3a38",
    grid="#3a3a38",
    accent="#3987e5",
    trace_colors=(
        "#3987e5",
        "#d95926",
        "#199e70",
        "#c98500",
        "#d55181",
        "#008300",
        "#9085e9",
        "#e66767",
    ),
)

LIGHT = Palette(
    surface="#fcfcfb",
    panel="#f2f2f0",
    text="#0b0b0b",
    muted_text="#52514e",
    border="#d5d4d0",
    grid="#d5d4d0",
    accent="#2a78d6",
    trace_colors=(
        "#2a78d6",
        "#eb6834",
        "#1baf7a",
        "#eda100",
        "#e87ba4",
        "#008300",
        "#4a3aa7",
        "#e34948",
    ),
)

_PALETTES: dict[Theme, Palette] = {Theme.DARK: DARK, Theme.LIGHT: LIGHT}

DEFAULT_THEME = Theme.LIGHT


def palette_for(theme: Theme) -> Palette:
    """Return the colour tokens for a theme."""

    return _PALETTES[theme]


def trace_color(palette: Palette, index: int) -> str:
    """Return the categorical colour for a trace index.

    Slots are assigned in fixed order. Beyond the eighth trace the order
    repeats, so plots carrying more than eight traces must rely on the
    legend rather than colour for identity.
    """

    return palette.trace_colors[index % len(palette.trace_colors)]


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Apply a theme to the whole application."""

    palette = palette_for(theme)
    qt_palette = QPalette()

    window = QColor(palette.panel)
    base = QColor(palette.surface)
    text = QColor(palette.text)
    muted = QColor(palette.muted_text)
    accent = QColor(palette.accent)

    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        qt_palette.setColor(group, QPalette.ColorRole.Window, window)
        qt_palette.setColor(group, QPalette.ColorRole.WindowText, text)
        qt_palette.setColor(group, QPalette.ColorRole.Base, base)
        qt_palette.setColor(group, QPalette.ColorRole.AlternateBase, window)
        qt_palette.setColor(group, QPalette.ColorRole.Text, text)
        qt_palette.setColor(group, QPalette.ColorRole.Button, window)
        qt_palette.setColor(group, QPalette.ColorRole.ButtonText, text)
        qt_palette.setColor(group, QPalette.ColorRole.ToolTipBase, window)
        qt_palette.setColor(group, QPalette.ColorRole.ToolTipText, text)
        qt_palette.setColor(group, QPalette.ColorRole.Highlight, accent)
        qt_palette.setColor(group, QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        qt_palette.setColor(group, QPalette.ColorRole.PlaceholderText, muted)

    disabled = QPalette.ColorGroup.Disabled
    qt_palette.setColor(disabled, QPalette.ColorRole.WindowText, muted)
    qt_palette.setColor(disabled, QPalette.ColorRole.Text, muted)
    qt_palette.setColor(disabled, QPalette.ColorRole.ButtonText, muted)

    app.setPalette(qt_palette)
    app.setStyleSheet(
        f"QMainWindow::separator {{ background: {palette.border}; width: 1px; height: 1px; }}"
        f"QDockWidget {{ titlebar-close-icon: none; color: {palette.text}; }}"
        f"QGroupBox {{ border: 1px solid {palette.border};"
        f" border-radius: 4px; margin-top: 8px; padding-top: 8px; }}"
        f"QGroupBox::title {{ subcontrol-origin: margin; left: 8px;"
        f" color: {palette.muted_text}; }}"
        f"QStatusBar {{ color: {palette.muted_text}; }}"
        f"QToolButton {{ border: 1px solid {palette.border}; border-radius: 3px;"
        f" padding: 3px 8px; }}"
        f"QToolButton:checked {{ background: {palette.accent}; color: #ffffff;"
        f" border-color: {palette.accent}; }}"
    )
