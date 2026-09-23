"""Frequency-domain file types of the PLTS Import dialogs, and one reader entry point."""

from enum import Enum
from pathlib import Path

from interconnect_studio.core import DataFormatError, Network
from interconnect_studio.io.citifile import read_citifile
from interconnect_studio.io.text_network import read_text_network
from interconnect_studio.io.touchstone import read_touchstone
from interconnect_studio.io.touchstone2 import read_touchstone2


class ImportFileType(Enum):
    """File types offered by the PLTS Import dialogs, in PLTS order.

    ``label`` is the text of the File Type list; ``pattern`` is the file
    dialog filter.
    """

    CITIFILE = ("Citifile (*.cti)", "*.cti *.cit")
    TOUCHSTONE = ("Touchstone (*.sNp)", "*.s*p")
    TOUCHSTONE_2 = ("Touchstone 2.0 (*.ts)", "*.ts")
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

    file_path = Path(path)
    if not file_path.is_file():
        raise DataFormatError(f"File not found: {file_path}")
    if file_type is ImportFileType.CITIFILE:
        return read_citifile(file_path)
    if file_type is ImportFileType.TOUCHSTONE:
        return read_touchstone(file_path)
    if file_type is ImportFileType.TOUCHSTONE_2:
        return read_touchstone2(file_path)
    if file_type is ImportFileType.TEXT_TAB:
        return read_text_network(file_path, "tab")
    return read_text_network(file_path, "comma")


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
