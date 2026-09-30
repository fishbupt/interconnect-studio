from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox

from interconnect_studio.ui.settings import SettingsStore


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests away from user preferences; allow teardown to discard test work."""

    monkeypatch.setattr(
        "interconnect_studio.ui.file_workflow.SettingsStore",
        lambda: SettingsStore(
            QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
        ),
    )
    original = QMessageBox.question

    def question(*args: object, **kwargs: object) -> object:
        if len(args) > 1 and args[1] == "未保存的工程":
            return QMessageBox.StandardButton.Discard
        return original(*args, **kwargs)

    monkeypatch.setattr(QMessageBox, "question", question)


@pytest.fixture(autouse=True)
def template_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep UI tests away from the user's saved templates."""

    directory = tmp_path / "templates"
    monkeypatch.setattr(
        "interconnect_studio.ui.main_window.default_template_directory", lambda: directory
    )
    return directory
