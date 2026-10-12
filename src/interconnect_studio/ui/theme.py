"""Shared engineering colour tokens and application-wide widget styling."""

from dataclasses import dataclass
from enum import StrEnum

from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PyQt6.QtWidgets import QApplication


class Theme(StrEnum):
    """Selectable colour themes."""

    DARK = "dark"
    LIGHT = "light"


@dataclass(frozen=True, slots=True)
class Palette:
    """Colour tokens for one theme.

    ``trace_colors`` identifies sources in legacy multi-source plots;
    single-source plots use the first colour consistently across parameters.
    """

    surface: str
    panel: str
    text: str
    muted_text: str
    border: str
    grid: str
    accent: str
    trace_colors: tuple[str, ...]
    background: str = "#1a1a19"
    disabled: str = "#858580"
    selection: str = "#334963"


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
    surface="#ffffff",
    panel="#ffffff",
    text="#24344a",
    muted_text="#64748b",
    border="#cbd5e1",
    grid="#e7ecf3",
    accent="#2563eb",
    trace_colors=(
        "#2563eb",
        "#d97706",
        "#199e70",
        "#c98500",
        "#d55181",
        "#008300",
        "#9085e9",
        "#e66767",
    ),
    background="#f3f6fa",
    disabled="#94a3b8",
    selection="#dbeafe",
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

    window = QColor(palette.background)
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
        qt_palette.setColor(group, QPalette.ColorRole.Button, base)
        qt_palette.setColor(group, QPalette.ColorRole.ButtonText, text)
        qt_palette.setColor(group, QPalette.ColorRole.ToolTipBase, window)
        qt_palette.setColor(group, QPalette.ColorRole.ToolTipText, text)
        qt_palette.setColor(group, QPalette.ColorRole.Highlight, accent)
        qt_palette.setColor(group, QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        qt_palette.setColor(group, QPalette.ColorRole.PlaceholderText, muted)

    disabled = QPalette.ColorGroup.Disabled
    qt_palette.setColor(disabled, QPalette.ColorRole.WindowText, QColor(palette.disabled))
    qt_palette.setColor(disabled, QPalette.ColorRole.Text, QColor(palette.disabled))
    qt_palette.setColor(disabled, QPalette.ColorRole.ButtonText, QColor(palette.disabled))

    app.setPalette(qt_palette)
    families = QFontDatabase.families()
    family = next(
        (name for name in ("Microsoft YaHei", "Noto Sans CJK SC", "Segoe UI") if name in families),
        app.font().family(),
    )
    app.setFont(QFont(family, 10))
    app.setStyleSheet(_stylesheet(palette))


def _stylesheet(p: Palette) -> str:
    # Explicit menu states avoid native styles retaining black text in dark mode.
    return f"""
    QWidget {{ color: {p.text}; }}
    QWidget:disabled {{ color: {p.disabled}; }}
    QMainWindow, QDialog, QWidget#analysisWorkspace {{ background: {p.background}; }}
    QWidget#summaryCard, QWidget#configPanel, QWidget#analysisView {{ background: {p.panel};
        border: 1px solid {p.grid}; border-radius: 6px; }}
    QLabel#pageTitle {{ font-size: 17pt; font-weight: bold; }}
    QLabel#secondaryText {{ color: {p.muted_text}; }}
    QLabel#errorText {{ color: {"#b91c1c" if p is LIGHT else "#e66767"}; }}
    QLabel#warningBanner {{ background: {"#fff7e6" if p is LIGHT else "#3b3020"};
        color: {"#92400e" if p is LIGHT else "#edba78"}; padding: 8px;
        border-radius: 4px; }}
    QDockWidget {{ color: {p.text}; }}
    QDockWidget::title {{ background: {p.background}; padding: 6px 8px; }}
    QMainWindow::separator {{ background: {p.grid}; width: 5px; height: 5px; }}
    QGroupBox {{ background: {p.panel}; border: 1px solid {p.grid};
        border-radius: 6px; margin-top: 12px; padding: 12px 8px 8px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; color: {p.muted_text}; }}
    QTreeView, QListWidget, QTableView, QTextEdit, QPlainTextEdit {{ background: {p.surface};
        border: 1px solid {p.grid}; border-radius: 4px;
        selection-background-color: {p.selection}; selection-color: {p.text}; }}
    QTreeView::item, QListWidget::item {{ padding: 3px 2px; }}
    QHeaderView::section {{ background: {p.background}; color: {p.muted_text};
        border: 0; border-right: 1px solid {p.grid}; padding: 6px; }}
    QScrollArea {{ border: none; background: {p.background}; }}
    QScrollBar:vertical {{ width: 12px; background: {p.background}; }}
    QScrollBar::handle:vertical {{ background: {p.border}; min-height: 24px; border-radius: 4px; }}
    QPushButton {{ background: {p.panel}; border: 1px solid {p.border};
        border-radius: 5px; padding: 6px 10px; min-height: 20px; }}
    QPushButton:hover, QToolButton:hover {{ background: {p.selection}; }}
    QPushButton:disabled {{ color: {p.disabled}; background: {p.background}; }}
    QPushButton#primary {{ background: {p.accent}; color: #ffffff; border-color: {p.accent}; }}
    QPushButton#primary:hover {{ background: {p.accent}; border-color: {p.text}; }}
    QPushButton#primary:disabled {{ background: {p.border}; color: {p.muted_text};
        border-color: {p.border}; }}
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{ background: {p.surface};
        border: 1px solid {p.border}; border-radius: 4px; padding: 4px; min-height: 20px; }}
    QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background: {p.background}; color: {p.disabled}; }}
    QComboBox QAbstractItemView {{ background: {p.surface}; color: {p.text};
        selection-background-color: {p.selection}; selection-color: {p.text}; }}
    QTabWidget::pane {{ background: {p.panel}; border: 1px solid {p.grid}; border-radius: 4px; }}
    QTabBar::tab {{ padding: 8px 18px; background: {p.background}; color: {p.muted_text}; }}
    QTabBar::tab:selected {{ background: {p.panel}; color: {p.accent}; }}
    QMenuBar, QMenu {{ background: {p.panel}; color: {p.text}; }}
    QMenuBar::item {{ background: transparent; color: {p.text}; padding: 6px 10px; }}
    QMenu {{ border: 1px solid {p.border}; }}
    QMenu::item {{ color: {p.text}; padding: 5px 24px; }}
    QMenuBar::item:selected, QMenuBar::item:pressed, QMenu::item:selected {{
        background: {p.accent}; color: #ffffff; }}
    QMenuBar::item:disabled, QMenu::item:disabled {{ color: {p.disabled}; }}
    QMenu::separator {{ background: {p.grid}; height: 1px; margin: 4px 8px; }}
    QToolBar {{ background: {p.panel}; border-bottom: 1px solid {p.grid};
        spacing: 6px; padding: 4px; }}
    QToolButton {{ background: {p.panel}; border: 1px solid {p.border}; border-radius: 4px;
        padding: 4px 8px; }}
    QToolButton:checked {{ background: {p.accent}; color: #ffffff; border-color: {p.accent}; }}
    QStatusBar {{ background: {p.background}; color: {p.muted_text}; }}
    QSplitter::handle {{ background: {p.grid}; }}
    QProgressBar {{ background: {p.surface}; border: 1px solid {p.grid}; border-radius: 4px;
        text-align: center; }}
    QProgressBar::chunk {{ background: {p.accent}; }}
    """
