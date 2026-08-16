"""T026: desktop integration stays inside XDG and is fully reversible (FR-003, FR-004)."""

from __future__ import annotations

import pathlib

import pytest

from gpum.adapters.linux import desktop_entry


@pytest.fixture
def xdg(tmp_path: pathlib.Path, monkeypatch) -> pathlib.Path:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    return tmp_path


class TestInstall:
    def test_not_installed_by_default(self, xdg: pathlib.Path) -> None:
        assert desktop_entry.is_installed() is False

    def test_install_writes_entry_and_icon(self, xdg: pathlib.Path) -> None:
        written = desktop_entry.install_desktop_entry()
        assert desktop_entry.is_installed()
        assert any(p.suffix == ".desktop" for p in written)
        assert any(p.suffix == ".svg" for p in written)

    def test_entry_is_valid(self, xdg: pathlib.Path) -> None:
        desktop_entry.install_desktop_entry()
        content = desktop_entry.desktop_entry_path().read_text()
        assert content.startswith("[Desktop Entry]")
        for key in ("Type=Application", "Name=GPUM", "Exec=", "Categories="):
            assert key in content

    def test_everything_written_stays_inside_xdg(self, xdg: pathlib.Path) -> None:
        for path in desktop_entry.install_desktop_entry():
            assert xdg in path.parents, f"{path} escaped the XDG root"


class TestRemove:
    def test_remove_deletes_exactly_what_was_written(self, xdg: pathlib.Path) -> None:
        written = set(desktop_entry.install_desktop_entry())
        removed = set(desktop_entry.remove_desktop_entry())
        assert removed == written
        assert desktop_entry.is_installed() is False

    def test_remove_is_idempotent(self, xdg: pathlib.Path) -> None:
        desktop_entry.remove_desktop_entry()
        desktop_entry.remove_desktop_entry()


class TestNoSideEffects:
    def test_querying_writes_nothing(self, xdg: pathlib.Path) -> None:
        desktop_entry.is_installed()
        desktop_entry.desktop_entry_path()
        desktop_entry.icon_path()
        assert not (xdg / "applications").exists()

    def test_importing_writes_nothing(self, xdg: pathlib.Path) -> None:
        import importlib

        importlib.reload(desktop_entry)
        assert not (xdg / "applications").exists()
