"""T059: the autostart entry (FR-022, and the Principle V deviation).

Everything is checked against a temporary XDG root — a test that wrote into the developer's
real autostart directory would be the exact overreach this feature is careful about.
"""

from __future__ import annotations

import pathlib

import pytest

from gpum.adapters.linux import autostart


@pytest.fixture
def xdg(tmp_path: pathlib.Path, monkeypatch) -> pathlib.Path:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


class TestLifecycle:
    def test_disabled_by_default(self, xdg: pathlib.Path) -> None:
        assert autostart.is_autostart_enabled() is False

    def test_enable_creates_the_entry(self, xdg: pathlib.Path) -> None:
        path = autostart.enable_autostart()
        assert path.is_file()
        assert autostart.is_autostart_enabled() is True

    def test_disable_removes_exactly_what_was_written(self, xdg: pathlib.Path) -> None:
        path = autostart.enable_autostart()
        autostart.disable_autostart()
        assert not path.exists()
        assert autostart.is_autostart_enabled() is False

    def test_disable_is_idempotent(self, xdg: pathlib.Path) -> None:
        autostart.disable_autostart()
        autostart.disable_autostart()

    def test_the_file_is_the_single_source_of_truth(self, xdg: pathlib.Path) -> None:
        """A user deleting the file by hand must be reflected immediately — which is why this
        state is not mirrored into preferences (data-model.md)."""
        path = autostart.enable_autostart()
        path.unlink()
        assert autostart.is_autostart_enabled() is False


class TestEntryContents:
    def test_starts_hidden(self, xdg: pathlib.Path) -> None:
        """FR-022: autostart must not steal focus at login."""
        content = autostart.enable_autostart().read_text()
        assert "--hidden" in content

    def test_is_a_valid_desktop_entry(self, xdg: pathlib.Path) -> None:
        content = autostart.enable_autostart().read_text()
        assert content.startswith("[Desktop Entry]")
        for key in ("Type=Application", "Name=", "Exec=", "Terminal=false"):
            assert key in content


class TestStaysInsideXdg:
    def test_writes_only_under_the_xdg_root(self, xdg: pathlib.Path) -> None:
        path = autostart.enable_autostart()
        assert xdg in path.parents, f"{path} escaped the XDG root"

    def test_nothing_is_written_without_an_explicit_call(self, xdg: pathlib.Path) -> None:
        autostart.is_autostart_enabled()
        autostart.autostart_path()
        assert not (xdg / "autostart").exists(), "querying must not create anything"
