"""XDG autostart entry (FR-022, research D-08).

**Constitution note**: this writes a file outside the tool's own preference store, which
brushes against Principle V ("MUST NOT modify any system state other than its own saved user
preferences"). It is user-initiated from a settings toggle, user-scoped, reversible by the same
toggle, and never written by default. Recorded in plan.md § Complexity Tracking with a proposed
amendment.

The file's *presence* is the single source of truth. Mirroring it into preferences would create
two sources that drift the moment a user deletes the file by hand.
"""

from __future__ import annotations

import logging
import os
import pathlib
import sys

__all__ = ["autostart_path", "disable_autostart", "enable_autostart", "is_autostart_enabled"]

_log = logging.getLogger(__name__)

_ENTRY_NAME = "gpum.desktop"

_TEMPLATE = """[Desktop Entry]
Type=Application
Name=GPUM
Comment=Live GPU memory and process monitor
Exec={exec_line}
Icon=gpum
Terminal=false
Categories=System;Monitor;
X-GNOME-Autostart-enabled=true
"""


def _config_home() -> pathlib.Path:
    return pathlib.Path(
        os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config"
    )


def autostart_path() -> pathlib.Path:
    return _config_home() / "autostart" / _ENTRY_NAME


def is_autostart_enabled() -> bool:
    """Queried, never assumed — the file is the truth."""
    return autostart_path().is_file()


def _exec_line() -> str:
    """The command the session should run.

    ``--hidden`` so an autostarted instance opens to the status area without taking focus
    (FR-022).
    """
    executable = os.environ.get("APPIMAGE") or sys.argv[0]
    if executable and pathlib.Path(executable).name not in {"python", "python3", "-c"}:
        return f"{executable} --hidden"
    return f"{sys.executable} -m gpum --hidden"


def enable_autostart() -> pathlib.Path:
    """Write the entry. Returns the path so the caller can disclose it to the user."""
    path = autostart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_TEMPLATE.format(exec_line=_exec_line()))
    _log.info("autostart enabled: %s", path)
    return path


def disable_autostart() -> None:
    """Remove exactly what ``enable_autostart`` wrote. Idempotent."""
    path = autostart_path()
    try:
        path.unlink()
        _log.info("autostart disabled: %s", path)
    except FileNotFoundError:
        pass
    except OSError:
        _log.warning("could not remove autostart entry at %s", path, exc_info=True)
