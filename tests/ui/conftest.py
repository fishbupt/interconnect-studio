from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def template_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep UI tests away from the user's saved templates."""

    directory = tmp_path / "templates"
    monkeypatch.setattr(
        "interconnect_studio.ui.main_window.default_template_directory", lambda: directory
    )
    return directory
