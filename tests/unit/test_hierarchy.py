from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from interconnect_studio.core import (
    BrowserCategory,
    DataBrowserTree,
    DataFile,
    InputValidationError,
    Network,
    ViewType,
    ViewWindow,
)


def network() -> Network:
    return Network([1.0e9, 2.0e9], np.zeros((2, 2, 2), dtype=np.complex128), z0=50.0)


def data_file(file_id: str = "f1", name: str = "DUT") -> DataFile:
    return DataFile(id=file_id, name=name, network=network())


def test_data_file_keeps_source_metadata() -> None:
    imported = datetime(2026, 1, 1, 12, 0, 0)
    item = DataFile(
        id="f1",
        name="DUT",
        network=network(),
        source_path=Path("dut.s2p"),
        imported_at=imported,
    )

    assert item.source_path == Path("dut.s2p")
    assert item.imported_at == imported


def test_data_file_allows_missing_source_for_algorithm_results() -> None:
    item = data_file()

    assert item.source_path is None


@pytest.mark.parametrize("bad_name", ["", "   "])
def test_data_file_rejects_empty_identifiers(bad_name: str) -> None:
    with pytest.raises(InputValidationError, match="non-empty"):
        DataFile(id=bad_name, name="DUT", network=network())


def test_data_file_strips_surrounding_whitespace() -> None:
    item = DataFile(id="  f1  ", name="  DUT  ", network=network())

    assert item.id == "f1"
    assert item.name == "DUT"


def test_data_file_rejects_non_network() -> None:
    with pytest.raises(InputValidationError, match="must be a Network"):
        DataFile(id="f1", name="DUT", network="not a network")  # type: ignore[arg-type]


def test_categories_follow_plts_order() -> None:
    assert [category.label for category in BrowserCategory] == [
        "Data Analysis",
        "RLCG",
        "Calibration",
        "Template View",
    ]


def test_view_types_under_each_category_follow_plts() -> None:
    labels = {
        category: [view.label for view in category.view_types] for category in BrowserCategory
    }

    assert labels[BrowserCategory.DATA_ANALYSIS] == [
        "Time Domain (Differential)",
        "Time Domain (Single-Ended)",
        "Frequency Domain (Balanced)",
        "Frequency Domain (Single-Ended)",
        "Eye Diagram (Differential)",
        "Eye Diagram (Single-Ended)",
    ]
    assert labels[BrowserCategory.RLCG] == [
        "RLCG (Differential)",
        "RLCG (Common)",
        "RLCG (W-Element)",
        "RLCG (Self/Mutual)",
    ]
    assert labels[BrowserCategory.CALIBRATION] == ["Error Terms", "Measured Standards"]
    assert labels[BrowserCategory.TEMPLATE_VIEW] == ["Create New", "Create New for Multi-data"]


def test_every_view_type_belongs_to_exactly_one_category() -> None:
    listed = [view for category in BrowserCategory for view in category.view_types]

    assert sorted(listed, key=lambda view: view.name) == sorted(
        ViewType, key=lambda view: view.name
    )


def test_window_label_shows_file_name_and_number() -> None:
    window = ViewWindow(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, data_file(name="dut.s2p"), 3)

    assert window.label == "dut.s2p : 3"


@pytest.mark.parametrize("bad_number", [0, -1, True])
def test_window_rejects_non_positive_numbers(bad_number: int) -> None:
    with pytest.raises(InputValidationError, match="positive integer"):
        ViewWindow(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, data_file(), bad_number)


def test_window_rejects_non_view_type() -> None:
    with pytest.raises(InputValidationError, match="ViewType"):
        ViewWindow("Frequency Domain", data_file(), 1)  # type: ignore[arg-type]


def test_empty_tree_numbers_windows_from_one() -> None:
    tree, window = DataBrowserTree().open(ViewType.TIME_DOMAIN_DIFFERENTIAL, data_file())

    assert window.number == 1
    assert tree.windows == (window,)


def test_open_numbers_windows_across_view_types() -> None:
    tree, first = DataBrowserTree().open(ViewType.TIME_DOMAIN_DIFFERENTIAL, data_file())
    tree, second = tree.open(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, data_file())

    assert (first.number, second.number) == (1, 2)
    assert tree.windows_of(ViewType.TIME_DOMAIN_DIFFERENTIAL) == (first,)
    assert tree.windows_of(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED) == (second,)
    assert tree.windows_of(ViewType.ERROR_TERMS) == ()


def test_same_file_can_open_in_several_view_types() -> None:
    item = data_file()
    tree, _ = DataBrowserTree().open(ViewType.TIME_DOMAIN_SINGLE_ENDED, item)
    tree, _ = tree.open(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, item)

    assert [window.data_file for window in tree.windows] == [item, item]


def test_tree_rejects_duplicate_window_numbers() -> None:
    first = ViewWindow(ViewType.TIME_DOMAIN_SINGLE_ENDED, data_file(), 1)
    second = ViewWindow(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, data_file(), 1)

    with pytest.raises(InputValidationError, match="unique"):
        DataBrowserTree(windows=(first, second))


def test_tree_is_immutable() -> None:
    tree = DataBrowserTree()

    with pytest.raises(AttributeError):
        tree.windows = ()  # type: ignore[misc]


def browser_with_two_files() -> DataBrowserTree:
    first, second = data_file("f1", "a.s2p"), data_file("f2", "b.s2p")
    tree, _ = DataBrowserTree().open(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, first)
    tree, _ = tree.open(ViewType.TIME_DOMAIN_SINGLE_ENDED, first)
    tree, _ = tree.open(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, second)
    return tree


def test_close_window_removes_only_that_window() -> None:
    tree = browser_with_two_files().close_window(2)

    assert [w.number for w in tree.windows] == [1, 3]


def test_close_window_keeps_numbering_increasing() -> None:
    tree = browser_with_two_files().close_window(3)

    assert tree.next_number == 3


def test_close_file_removes_every_window_of_the_file() -> None:
    tree = browser_with_two_files().close_file("f1")

    assert [w.number for w in tree.windows] == [3]


def test_rename_file_renames_it_in_every_window() -> None:
    tree = browser_with_two_files().rename_file("f1", "renamed.s2p")

    assert [w.label for w in tree.windows] == [
        "renamed.s2p : 1",
        "renamed.s2p : 2",
        "b.s2p : 3",
    ]
    assert tree.windows[0].data_file.id == "f1"


def test_rename_file_rejects_an_empty_name() -> None:
    with pytest.raises(InputValidationError, match="non-empty"):
        browser_with_two_files().rename_file("f1", "  ")


@pytest.mark.parametrize(
    "action",
    [
        lambda tree: tree.close_window(9),
        lambda tree: tree.close_file("missing"),
        lambda tree: tree.rename_file("missing", "x"),
        lambda tree: tree.window(9),
    ],
)
def test_tree_operations_reject_unknown_windows_and_files(action: object) -> None:
    with pytest.raises(InputValidationError, match="not open"):
        action(browser_with_two_files())  # type: ignore[operator]


def test_template_windows_are_listed_under_their_template() -> None:
    f1 = data_file("file-1", "dut.s2p")
    tree, plain = DataBrowserTree().open(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, f1)
    tree, templated = tree.open(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, f1, template="channel")

    assert tree.windows_of(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED) == (plain,)
    assert tree.windows_of_template("channel") == (templated,)
    assert tree.windows_of_template("") == ()
    assert templated.label == "dut.s2p : 2"
    assert tree.rename_file("file-1", "x").window(2).template == "channel"
