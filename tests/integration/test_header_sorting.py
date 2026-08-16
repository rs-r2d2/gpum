"""T006-T010, T018-T019, T027-T028: header sorting in the running interface.

Headless — no GPU needed for any of it.
"""

from __future__ import annotations

import datetime as dt
import time

from PySide6.QtCore import Qt

from gpum.core.models import (
    Availability,
    DeviceId,
    GpuDevice,
    GpuProcess,
    MetricValue,
    ProcessIdentity,
    ProcessSortColumn,
    Snapshot,
    Vendor,
)
from gpum.core.preferences import Preferences
from gpum.ui.main_window import MainWindow


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _device(key: str, index: int = 0) -> GpuDevice:
    return GpuDevice(
        id=DeviceId(Vendor.NVIDIA, key, index),
        name=f"GPU {index}",
        memory_total=MetricValue.available(24 * 1024**3, sampled_at=_now()),
        memory_used=MetricValue.available(6 * 1024**3, sampled_at=_now()),
        utilization_gpu=MetricValue.available(50, sampled_at=_now()),
        attribution=Availability.AVAILABLE,
    )


def _proc(pid: int, key: str, name: str, user: str, mem: int) -> GpuProcess:
    return GpuProcess(
        pid=pid,
        device_key=key,
        name=name,
        username=user,
        memory_used=MetricValue.available(mem, sampled_at=_now()),
        identity_state=ProcessIdentity.RESOLVED,
    )


def _snapshot(devices, processes, seq=1) -> Snapshot:
    return Snapshot(
        taken_at=_now(), sequence=seq, devices=tuple(devices), processes=tuple(processes)
    )


def _window(qtbot, prefs=None) -> MainWindow:
    window = MainWindow(prefs or Preferences())
    qtbot.addWidget(window)
    return window


def _pids(panel) -> list[int]:
    model = panel._model
    return [int(model.data(model.index(r, 1))) for r in range(model.rowCount())]


class TestHeaderInteraction:
    def test_clicking_a_header_sorts(self, qtbot) -> None:
        window = _window(qtbot)
        procs = [
            _proc(1, "a", "zeta", "u", 100),
            _proc(2, "a", "alpha", "u", 300),
            _proc(3, "a", "beta", "u", 200),
        ]
        window.on_snapshot(_snapshot([_device("a")], procs))
        panel = window._panels["a"]
        panel._table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        assert _pids(panel) == [2, 3, 1]

    def test_clicking_again_reverses(self, qtbot) -> None:
        window = _window(qtbot)
        procs = [_proc(i, "a", f"p{i}", "u", i * 100) for i in (1, 2, 3)]
        window.on_snapshot(_snapshot([_device("a")], procs))
        panel = window._panels["a"]
        panel._table.sortByColumn(3, Qt.SortOrder.AscendingOrder)
        ascending = _pids(panel)
        panel._table.sortByColumn(3, Qt.SortOrder.DescendingOrder)
        assert _pids(panel) == list(reversed(ascending))

    def test_every_column_is_sortable(self, qtbot) -> None:
        """S-01 / FR-006 — including User, which is inert before this feature."""
        window = _window(qtbot)
        procs = [
            _proc(3, "a", "c", "zoe", 300),
            _proc(1, "a", "a", "alice", 100),
            _proc(2, "a", "b", "bob", 200),
        ]
        window.on_snapshot(_snapshot([_device("a")], procs))
        panel = window._panels["a"]
        for section in range(4):
            panel._table.sortByColumn(section, Qt.SortOrder.AscendingOrder)
            assert len(_pids(panel)) == 3

    def test_user_column_sorts(self, qtbot) -> None:
        window = _window(qtbot)
        procs = [
            _proc(1, "a", "x", "zoe", 100),
            _proc(2, "a", "y", "alice", 100),
            _proc(3, "a", "z", "bob", 100),
        ]
        window.on_snapshot(_snapshot([_device("a")], procs))
        panel = window._panels["a"]
        panel._table.sortByColumn(2, Qt.SortOrder.AscendingOrder)
        assert _pids(panel) == [2, 3, 1]


class TestStabilityAcrossRefresh:
    def test_s07_order_survives_a_refresh(self, qtbot) -> None:
        window = _window(qtbot)
        procs = [_proc(i, "a", f"p{i}", "u", i * 100) for i in (1, 2, 3)]
        window.on_snapshot(_snapshot([_device("a")], procs, seq=1))
        panel = window._panels["a"]
        panel._table.sortByColumn(3, Qt.SortOrder.DescendingOrder)
        before = _pids(panel)
        window.on_snapshot(_snapshot([_device("a")], procs, seq=2))
        assert _pids(panel) == before

    def test_s06_equal_rows_never_reshuffle(self, qtbot) -> None:
        window = _window(qtbot)
        procs = [_proc(p, "a", "same", "same", 1024) for p in (5, 3, 9, 1)]
        window.on_snapshot(_snapshot([_device("a")], procs, seq=1))
        panel = window._panels["a"]
        panel._table.sortByColumn(2, Qt.SortOrder.AscendingOrder)
        first = _pids(panel)
        for seq in range(2, 22):
            window.on_snapshot(_snapshot([_device("a")], procs, seq=seq))
            assert _pids(panel) == first


class TestPerDeviceIndependence:
    def test_s08_sorting_one_table_leaves_others_alone(self, qtbot) -> None:
        window = _window(qtbot)
        devices = [_device("a", 0), _device("b", 1)]
        procs = [
            _proc(1, "a", "zeta", "u", 100),
            _proc(2, "a", "alpha", "u", 300),
            _proc(3, "b", "zeta", "u", 100),
            _proc(4, "b", "alpha", "u", 300),
        ]
        window.on_snapshot(_snapshot(devices, procs))
        panel_a, panel_b = window._panels["a"], window._panels["b"]
        panel_b.set_sort(ProcessSortColumn.MEMORY_USED, True)
        before_b = _pids(panel_b)

        panel_a._table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        assert _pids(panel_a) == [2, 1]
        assert _pids(panel_b) == before_b, "sorting one table disturbed another"

    def test_s09_new_device_uses_the_default(self, qtbot) -> None:
        prefs = Preferences()
        prefs.remember_sort("a", ProcessSortColumn.NAME, False)
        window = _window(qtbot, prefs)
        window.on_snapshot(_snapshot([_device("a"), _device("b", 1)], []))
        assert window._panels["b"]._model._sort_column is prefs.sort_column


class TestPersistenceWiring:
    def test_user_sort_is_remembered_per_device(self, qtbot) -> None:
        window = _window(qtbot)
        window.on_snapshot(_snapshot([_device("a")], []))
        window._panels["a"]._table.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        # USER is a text column, so a first click starts ascending regardless of the order the
        # view proposed — see TestFirstClickDirection.
        assert window.current_preferences().sort_for("a") == (ProcessSortColumn.USER, False)

    def test_saved_order_is_applied_on_first_display(self, qtbot) -> None:
        prefs = Preferences()
        prefs.remember_sort("a", ProcessSortColumn.PID, True)
        window = _window(qtbot, prefs)
        window.on_snapshot(_snapshot([_device("a")], []))
        assert window._panels["a"]._model._sort_column is ProcessSortColumn.PID
        assert window._panels["a"]._model.sort_descending is True

    def test_applying_a_saved_order_is_not_reported_as_a_user_action(self, qtbot) -> None:
        """Restoring must not overwrite another device's entry via a spurious signal."""
        prefs = Preferences()
        prefs.remember_sort("a", ProcessSortColumn.PID, True)
        window = _window(qtbot, prefs)
        changes: list[tuple] = []
        window.on_snapshot(_snapshot([_device("a")], []))
        window._panels["a"].sort_changed.connect(lambda *a: changes.append(a))
        window.on_snapshot(_snapshot([_device("a")], [], seq=2))
        assert changes == []


class TestBoundaries:
    def test_s14_sorting_changes_no_totals_or_membership(self, qtbot) -> None:
        window = _window(qtbot)
        device = _device("a")
        procs = [_proc(i, "a", f"p{i}", "u", i * 100) for i in range(1, 6)]
        window.on_snapshot(_snapshot([device], procs))
        panel = window._panels["a"]
        memory_before = panel._memory_label.text()
        pids_before = set(_pids(panel))
        for section in range(4):
            panel._table.sortByColumn(section, Qt.SortOrder.DescendingOrder)
            assert set(_pids(panel)) == pids_before
        assert panel._memory_label.text() == memory_before

    def test_s15_large_table_sorts_within_budget(self, qtbot) -> None:
        window = _window(qtbot)
        procs = [_proc(i, "a", f"p{i % 37}", f"u{i % 11}", (i % 97) * 1024) for i in range(500)]
        window.on_snapshot(_snapshot([_device("a")], procs))
        panel = window._panels["a"]
        start = time.perf_counter()
        panel._table.sortByColumn(3, Qt.SortOrder.DescendingOrder)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 16, f"sorting 500 rows took {elapsed_ms:.1f} ms"


class TestFirstClickDirection:
    """Regression: clicking a new column must choose a useful initial direction.

    Reported as "sort by GPU memory then process name doesn't change". The cause was that a
    newly-clicked column always started ascending, so GPU memory showed the *smallest*
    consumers first. On a real process list that ordering begins and ends with the same
    processes as the name sort, so the table looked unchanged and the click looked broken.
    """

    #: Mirrors a real machine: the same process is first and last in both orderings.
    REAL = [
        (7334, "cef_server", 2),
        (57436, "nautilus", 13),
        (3306, "gnome-shell", 34),
        (6716, "claude-desktop", 46),
        (7369, "cef_server", 126),
        (20872, "chrome", 147),
        (3099, "Xorg", 222),
    ]

    def _window(self, qtbot):
        procs = [_proc(pid, "a", name, "u", mb * 1024**2) for pid, name, mb in self.REAL]
        window = _window(qtbot)
        window.on_snapshot(_snapshot([_device("a")], procs))
        return window

    def test_first_click_on_memory_is_descending(self, qtbot) -> None:
        """Biggest consumer first — the question the column is actually asked."""
        window = self._window(qtbot)
        model = window._panels["a"]._model
        model.sort(0, Qt.SortOrder.AscendingOrder)   # move off memory
        model.sort(3, Qt.SortOrder.AscendingOrder)   # first click on memory
        assert model.sort_descending is True

    def test_first_click_on_text_columns_is_ascending(self, qtbot) -> None:
        window = self._window(qtbot)
        model = window._panels["a"]._model
        for section in (0, 1, 2):
            model.sort(3, Qt.SortOrder.AscendingOrder)
            model.sort(section, Qt.SortOrder.AscendingOrder)
            assert model.sort_descending is False

    def test_switching_columns_visibly_changes_the_order(self, qtbot) -> None:
        """The user-visible symptom: the top of the table must actually change."""
        window = self._window(qtbot)
        panel = window._panels["a"]
        model = panel._model

        model.sort(0, Qt.SortOrder.AscendingOrder)
        by_name = [model.data(model.index(r, 0)) for r in range(model.rowCount())]
        model.sort(3, Qt.SortOrder.AscendingOrder)
        by_memory = [model.data(model.index(r, 0)) for r in range(model.rowCount())]

        assert by_name != by_memory
        assert by_name[0] != by_memory[0], "the first row must change when switching columns"

    def test_clicking_the_active_column_still_toggles(self, qtbot) -> None:
        window = self._window(qtbot)
        model = window._panels["a"]._model
        # Memory is the default active column, so move away first to make the next click on it
        # a genuine first click.
        model.sort(0, Qt.SortOrder.AscendingOrder)
        model.sort(3, Qt.SortOrder.AscendingOrder)
        assert model.sort_descending is True
        model.sort(3, Qt.SortOrder.AscendingOrder)
        assert model.sort_descending is False
        model.sort(3, Qt.SortOrder.DescendingOrder)
        assert model.sort_descending is True

    def test_indicator_matches_the_direction_actually_applied(self, qtbot) -> None:
        """The arrow must not claim ascending while the data is descending."""
        window = self._window(qtbot)
        panel = window._panels["a"]
        panel._model.sort(0, Qt.SortOrder.AscendingOrder)
        panel._model.sort(3, Qt.SortOrder.AscendingOrder)
        header = panel._table.horizontalHeader()
        assert header.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
        assert panel._model.sort_descending is True
