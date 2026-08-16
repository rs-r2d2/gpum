"""T002, T022-T023: the per-device sort map (S-10 .. S-12).

A preferences file is user-editable. Every malformed shape must degrade to the default order
rather than stop a table displaying.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

from gpum.core.models import ProcessSortColumn
from gpum.core.preferences import Preferences
from gpum.ui.preferences_store import (
    _dump_sort_orders,
    _load_sort_orders,
    load_preferences,
    save_preferences,
)


class TestDefaults:
    def test_unseen_device_uses_the_default(self) -> None:
        prefs = Preferences(sort_column=ProcessSortColumn.NAME, sort_descending=False)
        assert prefs.sort_for("never-seen") == (ProcessSortColumn.NAME, False)

    def test_remembered_device_uses_its_own_order(self) -> None:
        prefs = Preferences()
        prefs.remember_sort("gpu-a", ProcessSortColumn.USER, True)
        assert prefs.sort_for("gpu-a") == (ProcessSortColumn.USER, True)

    def test_devices_are_independent(self) -> None:
        prefs = Preferences()
        prefs.remember_sort("gpu-a", ProcessSortColumn.NAME, False)
        prefs.remember_sort("gpu-b", ProcessSortColumn.PID, True)
        assert prefs.sort_for("gpu-a") == (ProcessSortColumn.NAME, False)
        assert prefs.sort_for("gpu-b") == (ProcessSortColumn.PID, True)


class TestRoundTrip:
    def test_map_survives_serialisation(self) -> None:
        orders = {
            "gpu-a": (ProcessSortColumn.USER, True),
            "gpu-b": (ProcessSortColumn.PID, False),
        }
        assert _load_sort_orders(_dump_sort_orders(orders)) == orders

    def test_s10_orders_survive_a_simulated_restart(self, tmp_path) -> None:
        prefs = Preferences()
        prefs.remember_sort("gpu-a", ProcessSortColumn.USER, True)
        prefs.remember_sort("gpu-b", ProcessSortColumn.NAME, False)
        save_preferences(prefs)

        restored = load_preferences()
        assert restored.sort_for("gpu-a") == (ProcessSortColumn.USER, True)
        assert restored.sort_for("gpu-b") == (ProcessSortColumn.NAME, False)

    def test_s11_a_reconnected_device_resumes_its_own_order(self, tmp_path) -> None:
        """An entry is retained for a device that is not currently present (FR-018)."""
        prefs = Preferences()
        prefs.remember_sort("GPU-uuid-removed", ProcessSortColumn.PID, True)
        save_preferences(prefs)
        assert load_preferences().sort_for("GPU-uuid-removed") == (
            ProcessSortColumn.PID,
            True,
        )


class TestMalformedInput:
    """S-12 — a user-editable file must not be able to break the interface."""

    def test_empty_is_empty(self) -> None:
        assert _load_sort_orders(None) == {}
        assert _load_sort_orders("") == {}

    def test_unparseable_falls_back(self) -> None:
        assert _load_sort_orders("{not json") == {}

    def test_non_mapping_falls_back(self) -> None:
        assert _load_sort_orders("[1, 2, 3]") == {}

    def test_unknown_column_is_dropped(self) -> None:
        """FR-021: a saved column that no longer exists falls back to the default."""
        loaded = _load_sort_orders('{"gpu-a": ["tensor_cores", true]}')
        assert loaded == {}

    def test_wrong_shape_is_dropped(self) -> None:
        assert _load_sort_orders('{"gpu-a": "memory_used"}') == {}
        assert _load_sort_orders('{"gpu-a": ["memory_used"]}') == {}

    def test_valid_entries_survive_alongside_invalid_ones(self) -> None:
        loaded = _load_sort_orders(
            '{"good": ["user", true], "bad": ["nonsense", false], "worse": 7}'
        )
        assert loaded == {"good": (ProcessSortColumn.USER, True)}

    def test_a_corrupt_map_does_not_lose_other_preferences(self, tmp_path) -> None:
        s = QSettings("gpum", "gpum")
        s.setValue("refresh_interval_ms", 5000)
        s.setValue("device_sort_orders", "{corrupt")
        s.sync()
        restored = load_preferences()
        assert restored.refresh_interval_ms == 5000
        assert restored.device_sort_orders == {}
