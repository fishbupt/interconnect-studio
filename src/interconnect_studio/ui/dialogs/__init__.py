"""Application dialogs."""

from interconnect_studio.ui.dialogs.add_trace_dialog import AddTraceDialog, TraceSelection
from interconnect_studio.ui.dialogs.build_config_dialog import BuildConfigDialog
from interconnect_studio.ui.dialogs.frequency_range_box import FrequencyRangeBox
from interconnect_studio.ui.dialogs.import_multiple_dialog import ImportMultipleFilesDialog
from interconnect_studio.ui.dialogs.import_single_dialog import ImportSingleFileDialog
from interconnect_studio.ui.dialogs.select_analysis_view_dialog import SelectAnalysisViewDialog

__all__ = [
    "AddTraceDialog",
    "BuildConfigDialog",
    "FrequencyRangeBox",
    "ImportMultipleFilesDialog",
    "ImportSingleFileDialog",
    "SelectAnalysisViewDialog",
    "TraceSelection",
]
