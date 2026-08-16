"""The process table (FR-006 – FR-010).

Keyed on ``(pid, started_at)`` so rows update in place rather than being rebuilt each refresh:
rebuilding would reset selection and scroll position every second, and a bare PID would let a
recycled PID inherit an exited process's row (research D-05).
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt, Signal

from gpum.core.models import GpuProcess, ProcessIdentity, ProcessSortColumn
from gpum.ui import availability as av

__all__ = ["ProcessTableModel"]

_COLUMNS = ("Process", "PID", "User", "GPU memory")

#: Display order -> the column each header sorts by (FR-006: all four are sortable).
_COLUMN_ORDER = (
    ProcessSortColumn.NAME,
    ProcessSortColumn.PID,
    ProcessSortColumn.USER,
    ProcessSortColumn.MEMORY_USED,
)

#: The direction a column takes when it is first clicked.
#:
#: A quantity column must start descending. Ascending would put the *smallest* consumers at the
#: top, which is never the question being asked, and on a real process list the result looks
#: almost identical to the name sort — both begin with the same low-memory process and end with
#: the same one — so the table reads as though the click did nothing. Text and identifier
#: columns start ascending, which is their natural reading order.
_FIRST_CLICK_DESCENDING = {
    ProcessSortColumn.MEMORY_USED: True,
    ProcessSortColumn.NAME: False,
    ProcessSortColumn.USER: False,
    ProcessSortColumn.PID: False,
}

def _identity(process: GpuProcess) -> tuple[int, float]:
    """Stable tiebreak: fixed across refreshes so equal-valued rows hold position."""
    started = process.started_at.timestamp() if process.started_at else 0.0
    return (process.pid, started)


def _memory_value(process: GpuProcess) -> float:
    return float(process.memory_used.value or 0.0)


#: column -> (sort key, "does this row have a real value for this column?")
_COMPARATORS: dict[ProcessSortColumn, tuple] = {
    ProcessSortColumn.NAME: (
        lambda p: (p.name or "").lower(),
        lambda p: bool(p.name),
    ),
    ProcessSortColumn.PID: (
        # Numeric, so 9 sorts before 100. Every row has a PID, so none can be missing.
        lambda p: p.pid,
        lambda p: True,
    ),
    ProcessSortColumn.USER: (
        lambda p: (p.username or "").lower(),
        lambda p: bool(p.username),
    ),
    ProcessSortColumn.MEMORY_USED: (
        # By byte quantity, never by the formatted text.
        _memory_value,
        lambda p: p.memory_used.is_measurement,
    ),
}

_IDENTITY_NOTE = {
    ProcessIdentity.RESTRICTED: "Not inspectable at your privilege level",
    ProcessIdentity.UNRESOLVED: "Could not be identified; its memory is still counted",
    ProcessIdentity.CONTAINERIZED: "Running inside a container",
}


class ProcessTableModel(QAbstractTableModel):
    #: (column value, descending) — emitted when the user sorts, for persistence.
    sort_changed = Signal(str, bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[GpuProcess] = []
        self._sort_column = ProcessSortColumn.MEMORY_USED
        self._descending = True

    # -- Qt model API ---------------------------------------------------------

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():
            return 0
        return len(_COLUMNS)

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        return _COLUMNS[section]

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        process = self._rows[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return self._name_text(process)
            if column == 1:
                return str(process.pid)
            if column == 2:
                return process.username or "—"
            if column == 3:
                # Never "0" for an unobtainable figure (SC-007).
                return av.memory_text(process.memory_used)
        elif role == Qt.ItemDataRole.ToolTipRole:
            notes = [_IDENTITY_NOTE.get(process.identity_state, "")]
            if process.container_id:
                notes.append(f"Container {process.container_id[:12]}")
            if column == 3:
                notes.append(av.tooltip_for(process.memory_used))
            if process.executable:
                notes.append(process.executable)
            return "\n".join(n for n in notes if n)
        elif role == Qt.ItemDataRole.TextAlignmentRole and column in (1, 3):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    # -- updating -------------------------------------------------------------

    def set_processes(self, processes: tuple[GpuProcess, ...]) -> None:
        """Replace the contents, preserving the current sort order (FR-010)."""
        ordered = self._sorted(list(processes))
        if len(ordered) == len(self._rows):
            self._rows = ordered
            if ordered:
                top = self.index(0, 0)
                bottom = self.index(len(ordered) - 1, len(_COLUMNS) - 1)
                self.dataChanged.emit(top, bottom)
            return
        self.beginResetModel()
        self._rows = ordered
        self.endResetModel()

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """The view's sorting entry point.

        Implementing this rather than intercepting header clicks lets the toolkit supply the
        whole interaction — the direction indicator, click-to-reverse, and the single-active-
        column rule — instead of reimplementing each and getting one subtly wrong (research
        D-01).
        """
        if not 0 <= column < len(_COLUMN_ORDER):
            return
        target = _COLUMN_ORDER[column]

        if target is self._sort_column:
            # Same column: honour the toggle the view computed.
            descending = order == Qt.SortOrder.DescendingOrder
        else:
            # A different column: choose the direction that answers the question the column is
            # usually asked, rather than always starting ascending.
            descending = _FIRST_CLICK_DESCENDING[target]

        self.set_sort(target, descending)
        self.sort_changed.emit(str(target), descending)

    @property
    def sort_section(self) -> int:
        """The display index of the active column, for restoring a saved order."""
        return _COLUMN_ORDER.index(self._sort_column)

    @property
    def sort_descending(self) -> bool:
        return self._descending

    def set_sort(self, column: ProcessSortColumn, descending: bool) -> None:
        # Coerced because Qt may hand back a bare string; the ordering below compares with `is`.
        try:
            self._sort_column = ProcessSortColumn(column)
        except ValueError:
            self._sort_column = ProcessSortColumn.MEMORY_USED
        self._descending = descending
        self.set_processes(tuple(self._rows))

    def _sorted(self, rows: list[GpuProcess]) -> list[GpuProcess]:
        """Order rows by the active column.

        Two rules are load-bearing and easy to lose:

        * **Rows without a value rank last in BOTH directions** (FR-010). They are partitioned
          out rather than given a sentinel key, because a sentinel flips with the sort direction
          and would put unmeasurable rows first when ascending — ranking an absence as though it
          were the smallest measured value.
        * **Equal values keep a fixed relative order** (FR-012), tie-broken on process identity.
          At a 1 Hz refresh, rows that reshuffle every second cannot be clicked.
        """
        key, has_value = _COMPARATORS[self._sort_column]

        available = [r for r in rows if has_value(r)]
        missing = [r for r in rows if not has_value(r)]

        available.sort(key=lambda p: (key(p), _identity(p)), reverse=self._descending)
        # Deterministic, and deliberately never reversed: their position is "last", not "last
        # in this direction".
        missing.sort(key=_identity)
        return available + missing

    @staticmethod
    def _name_text(process: GpuProcess) -> str:
        if process.identity_state is ProcessIdentity.CONTAINERIZED and process.container_id:
            return f"{process.display_name}  [{process.container_id[:12]}]"
        return process.display_name
