"""Input/output support for Interconnect Studio."""

from interconnect_studio.io.build_config import BuildConfig, BuildConfigEntry, read_build_config
from interconnect_studio.io.citifile import read_citifile
from interconnect_studio.io.importing import ImportFileType, guess_file_type, read_network
from interconnect_studio.io.template_file import (
    TEMPLATE_SUFFIX,
    read_template,
    write_template,
)
from interconnect_studio.io.text_network import read_text_network
from interconnect_studio.io.touchstone import read_touchstone, write_touchstone
from interconnect_studio.io.touchstone2 import read_touchstone2

__all__ = [
    "TEMPLATE_SUFFIX",
    "BuildConfig",
    "BuildConfigEntry",
    "ImportFileType",
    "guess_file_type",
    "read_build_config",
    "read_citifile",
    "read_network",
    "read_template",
    "read_text_network",
    "read_touchstone",
    "read_touchstone2",
    "write_template",
    "write_touchstone",
]
