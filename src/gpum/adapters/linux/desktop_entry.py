"""XDG desktop entry and icon (FR-003, FR-004, research D-07).

Installed by an explicit ``gpum --install-desktop-entry`` rather than at install time. Python
wheels have no reliable post-install hook — ``setup.py`` hooks do not run for wheels, which is
what pip installs — and writing files as an import side-effect would be worse. Making it a
user-initiated command keeps the constitution's "modifies nothing but its own preferences"
promise intact.

The AppImage does not need this: desktop environments discover AppImage metadata themselves.
"""

from __future__ import annotations

import logging
import os
import pathlib
import shutil
import sys

__all__ = [
    "desktop_entry_path",
    "icon_path",
    "install_desktop_entry",
    "is_installed",
    "remove_desktop_entry",
]

_log = logging.getLogger(__name__)

_ENTRY_NAME = "gpum.desktop"
_ICON_NAME = "gpum.svg"

_TEMPLATE = """[Desktop Entry]
Type=Application
Name=GPUM
GenericName=GPU Monitor
Comment=Live GPU memory and process monitor
Exec={exec_line}
Icon=gpum
Terminal=false
Categories=System;Monitor;
Keywords=gpu;nvidia;monitor;memory;
StartupNotify=true
"""


def _data_home() -> pathlib.Path:
    return pathlib.Path(os.environ.get("XDG_DATA_HOME") or pathlib.Path.home() / ".local/share")


def desktop_entry_path() -> pathlib.Path:
    return _data_home() / "applications" / _ENTRY_NAME


def icon_path() -> pathlib.Path:
    return _data_home() / "icons" / "hicolor" / "scalable" / "apps" / _ICON_NAME


def is_installed() -> bool:
    return desktop_entry_path().is_file()


def _exec_line() -> str:
    executable = os.environ.get("APPIMAGE") or shutil.which("gpum")
    if executable:
        return executable
    return f"{sys.executable} -m gpum"


def install_desktop_entry() -> list[pathlib.Path]:
    """Write the entry and icon. Returns every path written, for disclosure."""
    written: list[pathlib.Path] = []

    entry = desktop_entry_path()
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text(_TEMPLATE.format(exec_line=_exec_line()))
    entry.chmod(0o755)
    written.append(entry)

    source = pathlib.Path(__file__).resolve().parents[1].parent / "resources" / _ICON_NAME
    if source.is_file():
        target = icon_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        written.append(target)
    else:  # pragma: no cover - packaging error, not a user path
        _log.warning("icon not found at %s; entry installed without one", source)

    return written


def remove_desktop_entry() -> list[pathlib.Path]:
    """Remove exactly what ``install_desktop_entry`` wrote. Idempotent."""
    removed = []
    for path in (desktop_entry_path(), icon_path()):
        try:
            path.unlink()
            removed.append(path)
        except FileNotFoundError:
            continue
        except OSError:
            _log.warning("could not remove %s", path, exc_info=True)
    return removed
