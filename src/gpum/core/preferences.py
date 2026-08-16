"""User preferences (FR-023).

A plain dataclass with no Qt import, deliberately: persistence is ``ui.preferences_store``'s
job via ``QSettings``, and keeping the model Qt-free preserves the constitution's rule that
``core`` is testable without a Qt application (research D-10).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gpum.core.models import ProcessSortColumn

__all__ = ["MAX_INTERVAL_MS", "MIN_INTERVAL_MS", "Preferences"]

MIN_INTERVAL_MS = 100
#: The floor stops a user configuring the tool into consuming the resources it measures.
MAX_INTERVAL_MS = 60_000


@dataclass(slots=True)
class Preferences:
    refresh_interval_ms: int = 1000
    paused: bool = False
    sort_column: ProcessSortColumn = ProcessSortColumn.MEMORY_USED
    sort_descending: bool = True
    history_window_s: int = 300
    throttle_when_hidden: bool = True
    window_geometry: bytes | None = None

    # -- 002: tray presence -------------------------------------------------
    #: Whether the user wants a status-area icon at all. Independent of whether one is
    #: *possible* — that is probed at runtime, because a preference cannot make a desktop
    #: display an icon it does not support (contracts/tray-contract.md).
    tray_enabled: bool = True
    #: One-time disclosure that closing the window does not quit. Persisted so it appears once
    #: per user rather than once per session (FR-030).
    close_notice_shown: bool = False
    #: Set when launched via autostart, so the window opens to the tray without taking focus.
    start_hidden: bool = False

    # -- 003: per-device sort orders ----------------------------------------
    #: device key -> (column, descending). Keyed on the UUID-first DeviceId.key already used
    #: for device history, so a GPU that is disconnected and reconnected resumes its own
    #: arrangement (FR-018).
    #:
    #: Never pruned, by explicit decision: one small entry per GPU the machine has ever had,
    #: retained indefinitely. `sort_column`/`sort_descending` above are no longer written by a
    #: toolbar control — they are the default applied to any device with no entry here
    #: (FR-019), so an existing user's preference carries forward rather than being discarded.
    device_sort_orders: dict[str, tuple[ProcessSortColumn, bool]] = field(default_factory=dict)

    def sort_for(self, device_key: str) -> tuple[ProcessSortColumn, bool]:
        """The saved order for a device, or the default for one never sorted."""
        return self.device_sort_orders.get(
            device_key, (self.sort_column, self.sort_descending)
        )

    def remember_sort(
        self, device_key: str, column: ProcessSortColumn, descending: bool
    ) -> None:
        self.device_sort_orders[device_key] = (column, descending)

    # Deliberately absent: `autostart_enabled`. The presence of the autostart file is the
    # single source of truth; storing it here too creates two sources that drift the moment a
    # user deletes the file by hand (data-model.md).

    def __post_init__(self) -> None:
        self.refresh_interval_ms = clamp_interval(self.refresh_interval_ms)
        self.history_window_s = max(10, min(self.history_window_s, 3600))


def clamp_interval(value: int) -> int:
    return max(MIN_INTERVAL_MS, min(int(value), MAX_INTERVAL_MS))
