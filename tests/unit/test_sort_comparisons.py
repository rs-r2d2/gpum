"""T001, T008, T009: column comparisons (S-01 .. S-06).

Two of these guard behaviour the code *already* has. Routing sorting through a new entry point
is exactly how an emergent property vanishes unnoticed, so they are asserted directly.
"""

from __future__ import annotations

import datetime as dt

import pytest

from gpum.core.models import GpuProcess, MetricValue, ProcessIdentity, ProcessSortColumn
from gpum.ui.process_model import ProcessTableModel


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _p(pid: int, name=None, user=None, mem=None, state=ProcessIdentity.RESOLVED) -> GpuProcess:
    return GpuProcess(
        pid=pid,
        device_key="gpu-a",
        name=name,
        username=user,
        memory_used=(
            MetricValue.available(mem, sampled_at=_now())
            if mem is not None
            else MetricValue.unsupported("not reported")
        ),
        identity_state=state,
    )


def _order(rows, column, descending=False) -> list[int]:
    model = ProcessTableModel()
    model.set_sort(column, descending)
    model.set_processes(tuple(rows))
    return [int(model.data(model.index(r, 1))) for r in range(model.rowCount())]


class TestUserColumnExists:
    def test_user_is_sortable(self) -> None:
        """The column is displayed today but absent from the enum — the core of FR-006."""
        assert ProcessSortColumn.USER.value == "user"

    def test_all_four_columns_available(self) -> None:
        assert {c.value for c in ProcessSortColumn} == {"name", "pid", "user", "memory_used"}


class TestComparisons:
    def test_s02_pid_sorts_numerically(self) -> None:
        """Text ordering would put 100 before 9."""
        rows = [_p(100, "a", "u", 1), _p(9, "b", "u", 1), _p(50, "c", "u", 1)]
        assert _order(rows, ProcessSortColumn.PID) == [9, 50, 100]

    def test_s03_memory_sorts_by_quantity(self) -> None:
        rows = [_p(1, "a", "u", 900), _p(2, "b", "u", 1000), _p(3, "c", "u", 90)]
        assert _order(rows, ProcessSortColumn.MEMORY_USED) == [3, 1, 2]

    def test_s04_name_sorts_case_insensitively(self) -> None:
        rows = [_p(1, "zeta", "u", 1), _p(2, "Alpha", "u", 1), _p(3, "beta", "u", 1)]
        assert _order(rows, ProcessSortColumn.NAME) == [2, 3, 1]

    def test_s04_user_sorts_case_insensitively(self) -> None:
        rows = [_p(1, "a", "zoe", 1), _p(2, "b", "Alice", 1), _p(3, "c", "bob", 1)]
        assert _order(rows, ProcessSortColumn.USER) == [2, 3, 1]

    def test_descending_reverses(self) -> None:
        rows = [_p(1, "a", "u", 10), _p(2, "b", "u", 30), _p(3, "c", "u", 20)]
        assert _order(rows, ProcessSortColumn.MEMORY_USED, descending=True) == [2, 3, 1]


class TestUnavailableSortsLast:
    """S-05 / FR-010 — the rule that keeps an absence from ranking as a measurement."""

    @pytest.mark.parametrize("descending", [False, True])
    def test_unmeasurable_memory_last_in_both_directions(self, descending: bool) -> None:
        rows = [_p(1, "a", "u", None), _p(2, "b", "u", 500), _p(3, "c", "u", 100)]
        order = _order(rows, ProcessSortColumn.MEMORY_USED, descending)
        assert order[-1] == 1, "an unreadable figure must never outrank a measured one"

    @pytest.mark.parametrize("descending", [False, True])
    def test_missing_name_last_in_both_directions(self, descending: bool) -> None:
        rows = [
            _p(1, None, "u", 1, ProcessIdentity.UNRESOLVED),
            _p(2, "beta", "u", 1),
            _p(3, "alpha", "u", 1),
        ]
        order = _order(rows, ProcessSortColumn.NAME, descending)
        assert order[-1] == 1, "a missing name must not sort as an empty string"

    @pytest.mark.parametrize("descending", [False, True])
    def test_missing_user_last_in_both_directions(self, descending: bool) -> None:
        rows = [
            _p(1, "a", None, 1, ProcessIdentity.RESTRICTED),
            _p(2, "b", "zoe", 1),
            _p(3, "c", "alice", 1),
        ]
        order = _order(rows, ProcessSortColumn.USER, descending)
        assert order[-1] == 1

    def test_multiple_unavailable_rows_keep_a_stable_order(self) -> None:
        rows = [_p(3, "a", "u", None), _p(1, "b", "u", None), _p(2, "c", "u", 5)]
        order = _order(rows, ProcessSortColumn.MEMORY_USED)
        assert order[0] == 2
        assert order[1:] == [1, 3], "unavailable rows must be ordered deterministically"


class TestStability:
    """S-06 / FR-012 — at 1 Hz, reshuffling makes the table impossible to click."""

    def test_equal_values_never_reshuffle_across_refreshes(self) -> None:
        rows = tuple(_p(pid, "same", "same", 1024) for pid in (5, 3, 9, 1, 7))
        model = ProcessTableModel()
        model.set_sort(ProcessSortColumn.MEMORY_USED, True)
        model.set_processes(rows)
        first = [model.data(model.index(r, 1)) for r in range(model.rowCount())]
        for _ in range(20):
            model.set_processes(rows)
            assert [
                model.data(model.index(r, 1)) for r in range(model.rowCount())
            ] == first

    def test_equal_names_are_tie_broken_by_identity(self) -> None:
        rows = [_p(9, "same", "u", 1), _p(2, "same", "u", 1), _p(5, "same", "u", 1)]
        assert _order(rows, ProcessSortColumn.NAME) == [2, 5, 9]


class TestSortIsPresentationOnly:
    """S-14 / FR-022."""

    def test_row_count_is_unchanged_by_sorting(self) -> None:
        rows = tuple(_p(i, f"p{i}", "u", i * 10) for i in range(1, 8))
        model = ProcessTableModel()
        model.set_processes(rows)
        before = model.rowCount()
        for column in ProcessSortColumn:
            for descending in (True, False):
                model.set_sort(column, descending)
                assert model.rowCount() == before

    def test_the_same_pids_are_present_after_any_sort(self) -> None:
        rows = tuple(_p(i, f"p{i}", "u", i * 10) for i in range(1, 8))
        model = ProcessTableModel()
        model.set_processes(rows)
        expected = {int(model.data(model.index(r, 1))) for r in range(model.rowCount())}
        for column in ProcessSortColumn:
            model.set_sort(column, True)
            assert {
                int(model.data(model.index(r, 1))) for r in range(model.rowCount())
            } == expected
