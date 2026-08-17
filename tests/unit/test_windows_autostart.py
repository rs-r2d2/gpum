"""T004, T005: Windows autostart (feature 007, D-06, FR-004).

**Runs on every platform**, including the Linux machines this project is developed on and the
GPU-less CI runners, as Principle IV requires. The registry is faked; what is under test is the
module's behaviour, not Windows'.

The behaviour that matters is the one the Linux module already states: the entry's *presence*
is the single source of truth. Mirroring it into preferences would create two sources that
drift the moment a user removes the entry by hand.
"""

from __future__ import annotations

import sys

import pytest

from gpum.adapters.windows import autostart as win_autostart

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "GPUM"


class FakeRegistry:
    """The smallest thing that behaves like the corner of the registry this module touches."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.opened_keys: list[str] = []

    def read(self, key: str, name: str) -> str | None:
        self.opened_keys.append(key)
        return self.values.get(name)

    def write(self, key: str, name: str, value: str) -> None:
        self.opened_keys.append(key)
        self.values[name] = value

    def delete(self, key: str, name: str) -> None:
        self.opened_keys.append(key)
        self.values.pop(name, None)


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> FakeRegistry:
    fake = FakeRegistry()
    monkeypatch.setattr(win_autostart, "_read_value", fake.read)
    monkeypatch.setattr(win_autostart, "_write_value", fake.write)
    monkeypatch.setattr(win_autostart, "_delete_value", fake.delete)
    return fake


class TestPresenceIsTheTruth:
    def test_t004_absent_entry_reads_as_disabled(self, registry: FakeRegistry) -> None:
        assert win_autostart.is_autostart_enabled() is False

    def test_t004_present_entry_reads_as_enabled(self, registry: FakeRegistry) -> None:
        registry.values[VALUE_NAME] = r"C:\somewhere\gpum.exe --hidden"
        assert win_autostart.is_autostart_enabled() is True

    def test_t004_state_is_read_from_the_registry_not_remembered(
        self, registry: FakeRegistry
    ) -> None:
        """An entry removed behind the module's back must read as disabled immediately.

        This is the property that makes the registry the single source of truth rather than one
        of two that can disagree.
        """
        win_autostart.enable_autostart()
        assert win_autostart.is_autostart_enabled() is True
        registry.values.clear()
        assert win_autostart.is_autostart_enabled() is False


class TestRoundTrip:
    def test_t004_enable_then_disable_leaves_the_registry_as_found(
        self, registry: FakeRegistry
    ) -> None:
        before = dict(registry.values)
        win_autostart.enable_autostart()
        assert registry.values != before
        win_autostart.disable_autostart()
        assert registry.values == before

    def test_t004_disable_is_idempotent(self, registry: FakeRegistry) -> None:
        win_autostart.disable_autostart()
        win_autostart.disable_autostart()
        assert VALUE_NAME not in registry.values

    def test_t004_enable_writes_only_under_hkcu_run(self, registry: FakeRegistry) -> None:
        """Principle V: user-scoped and unelevated. An HKLM write would need administrator
        rights, which the constitution forbids requiring."""
        win_autostart.enable_autostart()
        assert registry.opened_keys
        for key in registry.opened_keys:
            assert key == RUN_KEY, f"touched {key}; only {RUN_KEY} is permitted"

    def test_t004_entry_starts_hidden(self, registry: FakeRegistry) -> None:
        """An autostarted instance opens to the status area without stealing focus, the same
        contract the Linux entry already honours."""
        win_autostart.enable_autostart()
        assert "--hidden" in registry.values[VALUE_NAME]


class TestDisclosedLocation:
    def test_t004_reported_location_is_a_registry_path(self, registry: FakeRegistry) -> None:
        """The settings dialog discloses this string before the user enables anything.

        On Windows it must name the registry. A path containing ``.config`` or ending in
        ``.desktop`` is the pre-existing defect (D-07) still present.
        """
        location = str(win_autostart.autostart_path())
        assert "HKCU" in location or "HKEY_CURRENT_USER" in location
        assert RUN_KEY in location
        assert ".desktop" not in location
        assert ".config" not in location


class TestPlatformContract:
    """T005: both implementations satisfy one contract, so the UI needs no platform knowledge."""

    REQUIRED = ("autostart_path", "disable_autostart", "enable_autostart", "is_autostart_enabled")

    def test_t005_windows_module_exposes_the_contract(self) -> None:
        for name in self.REQUIRED:
            assert callable(getattr(win_autostart, name, None)), f"missing {name}"

    @pytest.mark.skipif(
        not sys.platform.startswith("linux"), reason="the Linux module is importable on Linux"
    )
    def test_t005_both_platform_modules_expose_the_same_contract(self) -> None:
        from gpum.adapters.linux import autostart as linux_autostart

        for name in self.REQUIRED:
            assert callable(getattr(linux_autostart, name, None)), f"linux missing {name}"
            assert callable(getattr(win_autostart, name, None)), f"windows missing {name}"

    def test_t005_public_surface_matches(self) -> None:
        """``__all__`` is the declared contract; a divergence here means the settings dialog
        would need to know which platform it is on."""
        from gpum.adapters.linux import autostart as linux_autostart

        assert set(win_autostart.__all__) == set(linux_autostart.__all__)
