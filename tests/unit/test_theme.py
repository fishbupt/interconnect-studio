import pytest

from interconnect_studio.ui.theme import DEFAULT_THEME, Theme, palette_for, trace_color


def test_light_is_the_default_theme() -> None:
    assert DEFAULT_THEME is Theme.LIGHT


@pytest.mark.parametrize("theme", list(Theme))
def test_every_theme_defines_eight_trace_colors(theme: Theme) -> None:
    assert len(palette_for(theme).trace_colors) == 8


@pytest.mark.parametrize("theme", list(Theme))
def test_trace_colors_are_distinct(theme: Theme) -> None:
    colors = palette_for(theme).trace_colors

    assert len(set(colors)) == len(colors)


@pytest.mark.parametrize("theme", list(Theme))
def test_trace_colors_are_hex(theme: Theme) -> None:
    for color in palette_for(theme).trace_colors:
        assert color.startswith("#")
        assert len(color) == 7
        int(color[1:], 16)


@pytest.mark.parametrize("theme", list(Theme))
def test_trace_color_assigns_slots_in_fixed_order(theme: Theme) -> None:
    palette = palette_for(theme)

    assert trace_color(palette, 0) == palette.trace_colors[0]
    assert trace_color(palette, 2) == palette.trace_colors[2]


@pytest.mark.parametrize("theme", list(Theme))
def test_trace_color_wraps_past_the_last_slot(theme: Theme) -> None:
    palette = palette_for(theme)

    assert trace_color(palette, 8) == palette.trace_colors[0]


def test_themes_use_different_surfaces() -> None:
    assert palette_for(Theme.DARK).surface != palette_for(Theme.LIGHT).surface
