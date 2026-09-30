"""Frequency-domain file types of the PLTS Import dialogs, and one reader entry point."""

from enum import Enum
from pathlib import Path

from interconnect_studio.core import DataFormatError, Network, PortGroup
from interconnect_studio.io.citifile import read_citifile
from interconnect_studio.io.text_network import read_text_network
from interconnect_studio.io.touchstone import read_touchstone
from interconnect_studio.io.touchstone2 import read_touchstone2_with_pairs


class ImportFileType(Enum):
    """File types offered by the Import dialogs, in display order.

    Touchstone 1.0, Touchstone 2.0 and CITIfile come first, then text.
    ``label`` is the text of the File Type list; the second value is the file
    dialog pattern.
    """

    TOUCHSTONE = ("Touchstone 1.0 (*.sNp)", "*.s*p")
    TOUCHSTONE_2 = ("Touchstone 2.0 (*.ts)", "*.ts")
    CITIFILE = ("Citifile (*.cti)", "*.cti *.cit")
    TEXT_TAB = ("Text (tab delimited) (*.txt)", "*.txt")
    TEXT_COMMA = ("Text (comma delimited) (*.txt)", "*.txt *.csv")

    @property
    def label(self) -> str:
        """Text shown in the File Type list."""

        label: str = self.value[0]
        return label

    @property
    def file_filter(self) -> str:
        """Qt file dialog filter for this type."""

        return f"{self.label.split(' (*')[0]} ({self.value[1]})"


def read_network(path: str | Path, file_type: ImportFileType) -> Network:
    """Read a frequency-domain S-parameter file of the given type."""

    network, _ = read_network_with_pairs(path, file_type)
    return network


def read_network_with_pairs(
    path: str | Path,
    file_type: ImportFileType,
) -> tuple[Network, PortGroup | None]:
    """Read a file, reporting any pairing the file itself declared.

    Only Touchstone 2.0 can state one, through ``[Mixed-Mode Order]``. Every
    other format describes single-ended ports and returns ``None``, leaving
    the DUT configuration to the user.
    """

    file_path = Path(path)
    if not file_path.is_file():
        raise DataFormatError(f"File not found: {file_path}")
    if file_type is ImportFileType.TOUCHSTONE_2:
        return read_touchstone2_with_pairs(file_path)
    if file_type is ImportFileType.CITIFILE:
        return read_citifile(file_path), None
    if file_type is ImportFileType.TOUCHSTONE:
        return read_touchstone(file_path), None
    if file_type is ImportFileType.TEXT_TAB:
        return read_text_network(file_path, "tab"), None
    return read_text_network(file_path, "comma"), None


def guess_file_type(path: str | Path) -> ImportFileType | None:
    """File type implied by a file name, or None when the name is ambiguous."""

    suffix = Path(path).suffix.lower()
    if suffix in {".cti", ".cit"}:
        return ImportFileType.CITIFILE
    if suffix == ".ts":
        return ImportFileType.TOUCHSTONE_2
    if suffix == ".csv":
        return ImportFileType.TEXT_COMMA
    if len(suffix) > 3 and suffix.startswith(".s") and suffix.endswith("p"):
        return ImportFileType.TOUCHSTONE if suffix[2:-1].isdigit() else None
    return None


def detect_file_type(path: str | Path) -> ImportFileType:
    """Resolve .txt delimiter from its header for recent-file reopening.

    Other formats use suffix detection. This reads only the first header,
    leaving numeric parsing and validation to the existing readers.
    """

    file_path = Path(path)
    guessed = guess_file_type(file_path)
    if guessed is not None:
        return guessed
    if file_path.suffix.lower() == ".txt":
        try:
            with file_path.open(encoding="utf-8-sig") as stream:
                for _ in range(1024):
                    line = stream.readline(65536).strip()
                    if not line:
                        continue
                    if line.startswith("!") or line.upper() in {"BEGIN", "END"}:
                        continue
                    return ImportFileType.TEXT_TAB if "\t" in line else ImportFileType.TEXT_COMMA
        except (OSError, UnicodeError) as exc:
            raise DataFormatError(f"Cannot identify text file: {file_path}") from exc
    raise DataFormatError(f"Cannot identify the file type: {file_path.name}")
