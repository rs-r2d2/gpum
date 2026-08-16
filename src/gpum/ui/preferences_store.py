"""Preference persistence via QSettings (FR-023, research D-10).

QSettings picks the platform-appropriate location itself — the registry on Windows, a config
file on Linux — which is one less thing to fork per platform. The `Preferences` model it reads
and writes stays Qt-free in `core`.
"""

from __future__ import annotations

import json
import logging

from PySide6.QtCore import QSettings

from gpum.core.models import ProcessSortColumn
from gpum.core.preferences import Preferences

__all__ = ["load_preferences", "save_preferences"]

_log = logging.getLogger(__name__)

_ORG = "gpum"
_APP = "gpum"


def _settings() -> QSettings:
    return QSettings(_ORG, _APP)


def load_preferences() -> Preferences:
    s = _settings()
    try:
        sort_column = ProcessSortColumn(s.value("sort_column", ProcessSortColumn.MEMORY_USED))
    except ValueError:
        sort_column = ProcessSortColumn.MEMORY_USED

    geometry = s.value("window_geometry")
    return Preferences(
        refresh_interval_ms=int(s.value("refresh_interval_ms", 1000)),
        paused=_as_bool(s.value("paused", False)),
        sort_column=sort_column,
        sort_descending=_as_bool(s.value("sort_descending", True)),
        history_window_s=int(s.value("history_window_s", 300)),
        throttle_when_hidden=_as_bool(s.value("throttle_when_hidden", True)),
        window_geometry=bytes(geometry) if geometry else None,
        device_sort_orders=_load_sort_orders(s.value("device_sort_orders")),
        tray_enabled=_as_bool(s.value("tray_enabled", True)),
        close_notice_shown=_as_bool(s.value("close_notice_shown", False)),
        start_hidden=_as_bool(s.value("start_hidden", False)),
    )


def save_preferences(prefs: Preferences) -> None:
    s = _settings()
    s.setValue("refresh_interval_ms", prefs.refresh_interval_ms)
    s.setValue("paused", prefs.paused)
    s.setValue("sort_column", str(prefs.sort_column))
    s.setValue("sort_descending", prefs.sort_descending)
    s.setValue("history_window_s", prefs.history_window_s)
    s.setValue("throttle_when_hidden", prefs.throttle_when_hidden)
    s.setValue("tray_enabled", prefs.tray_enabled)
    s.setValue("close_notice_shown", prefs.close_notice_shown)
    s.setValue("start_hidden", prefs.start_hidden)
    if prefs.window_geometry:
        s.setValue("window_geometry", prefs.window_geometry)
    s.setValue("device_sort_orders", _dump_sort_orders(prefs.device_sort_orders))
    s.sync()


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes"}


def _load_sort_orders(raw: object) -> dict[str, tuple[ProcessSortColumn, bool]]:
    """Restore the per-device sort map, tolerating anything.

    A preferences file is user-editable, so every malformed shape must degrade to the default
    order rather than prevent a table from displaying (FR-020, FR-021). A corrupt map must also
    not take the rest of the preferences down with it.
    """
    if not raw:
        return {}
    try:
        decoded = json.loads(raw if isinstance(raw, str) else str(raw))
    except (ValueError, TypeError):
        _log.warning("saved sort orders were unreadable; using defaults")
        return {}
    if not isinstance(decoded, dict):
        return {}

    orders: dict[str, tuple[ProcessSortColumn, bool]] = {}
    for key, value in decoded.items():
        if not isinstance(key, str) or not isinstance(value, (list, tuple)) or len(value) != 2:
            continue
        column_name, descending = value
        try:
            column = ProcessSortColumn(column_name)
        except ValueError:
            # The saved column no longer exists — fall back to the default for this device.
            continue
        orders[key] = (column, bool(descending))
    return orders


def _dump_sort_orders(orders: dict[str, tuple[ProcessSortColumn, bool]]) -> str:
    return json.dumps({k: [str(c), bool(d)] for k, (c, d) in orders.items()})
