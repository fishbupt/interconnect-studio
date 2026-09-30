"""Per-user preferences and a four-entry recent-file list."""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from PyQt6.QtCore import QSettings

from interconnect_studio.core import DataFormatError, InputValidationError
from interconnect_studio.io.atomic import atomic_destination
from interconnect_studio.services.export_service import ExportFileType
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Preferences:
    """Common file/plot defaults; no measurement data is stored here."""

    theme: str = DEFAULT_THEME.value
    import_directory: str = ""
    export_directory: str = ""
    export_type: str = ExportFileType.TOUCHSTONE.value
    frequency_unit: str = "hz"
    line_width: int = 2
    remember_layout: bool = True

    def __post_init__(self) -> None:
        try:
            Theme(self.theme)
            ExportFileType(self.export_type)
        except (ValueError, TypeError) as exc:
            raise InputValidationError("Invalid preference theme or export type.") from exc
        if self.frequency_unit not in {"hz", "khz", "mhz", "ghz"}:
            raise InputValidationError("Invalid preference frequency unit.")
        if type(self.line_width) is not int or not 1 <= self.line_width <= 8:
            raise InputValidationError("Trace line width must be between 1 and 8.")
        if type(self.remember_layout) is not bool:
            raise InputValidationError("Remember layout must be a boolean.")
        if not isinstance(self.import_directory, str) or not isinstance(self.export_directory, str):
            raise InputValidationError("Preference directories must be strings.")


class SettingsStore:
    """Injectable QSettings backend; invalid stored preferences fall back to defaults."""

    def __init__(self, backend: QSettings | None = None) -> None:
        self.backend = backend or QSettings("InterconnectStudio", "InterconnectStudio")

    def preferences(self) -> Preferences:
        """Load validated preferences without crashing startup on damaged settings."""

        try:
            return Preferences(**json.loads(str(self.backend.value("preferences", "{}"))))
        except (ValueError, TypeError) as exc:
            logger.warning("Ignoring malformed preferences: %s", exc)
            return Preferences()

    def save_preferences(self, preferences: Preferences) -> None:
        """Persist the full preferences document."""

        self.backend.setValue("preferences", json.dumps(asdict(preferences)))
        self.backend.sync()

    def recent_files(self) -> tuple[Path, ...]:
        """Four most recently opened measurements or projects, newest first."""

        value = self.backend.value("recent_files", [])
        if not isinstance(value, list):
            return ()
        return tuple(Path(item) for item in value[:4] if isinstance(item, str))

    def add_recent(self, path: Path) -> None:
        """Move a successful open/save to the front, with duplicates removed."""

        canonical = path.resolve()
        others = [item for item in self.recent_files() if item != canonical]
        self.backend.setValue("recent_files", [str(item) for item in [canonical, *others][:4]])
        self.backend.sync()

    def remove_recent(self, path: Path) -> None:
        """Remove a stale path after an explicit open attempt."""

        self.backend.setValue(
            "recent_files", [str(item) for item in self.recent_files() if item != path]
        )
        self.backend.sync()

    def clear_recent(self) -> None:
        """Clear history without deleting any files."""

        self.backend.remove("recent_files")
        self.backend.sync()


def write_preferences(preferences: Preferences, path: Path) -> None:
    """Export a named preferences file for reuse on another machine."""

    document = {
        "format": "interconnect-studio-preferences",
        "version": 1,
        "preferences": asdict(preferences),
    }
    with atomic_destination(path) as temporary:
        temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")


def read_preferences(path: Path) -> Preferences:
    """Read and validate a named preferences file before applying it."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(document, dict)
            or document.get("format") != "interconnect-studio-preferences"
        ):
            raise DataFormatError("Not an Interconnect Studio preferences file.")
        if type(document.get("version")) is not int or document["version"] != 1:
            raise DataFormatError("Unsupported preferences version.")
        return Preferences(**document["preferences"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise DataFormatError(f"Cannot load preferences: {exc}") from exc
