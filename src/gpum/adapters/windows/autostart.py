"""Windows autostart via the per-user Run key (feature 007, FR-004, research D-06).

**Constitution note**: this writes outside the tool's own preference store, the same Principle V
deviation `adapters/linux/autostart.py` records. It is user-initiated from a settings toggle,
user-scoped, reversible by the same toggle, and never written by default. The amendment that
module proposes should cover both platforms.

**Why the registry rather than a Startup-folder shortcut**: the two are equivalent in effect,
but a shortcut means writing a `.lnk`, which means COM or a shortcut library for no benefit.
The registry entry is one string.

**HKCU only, never HKLM.** A machine-wide entry would require administrator rights, which the
constitution forbids requiring.

The value's *presence* is the single source of truth, exactly as the file is on Linux. Mirroring
it into preferences would create two sources that drift the moment a user removes the entry by
hand.
"""

from __future__ import annotations

import logging
import os
import pathlib
import sys

__all__ = ["autostart_path", "disable_autostart", "enable_autostart", "is_autostart_enabled"]

_log = logging.getLogger(__name__)

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "GPUM"


def _winreg():
    """Imported lazily so this module is importable — and testable — on any platform.

    Principle IV requires the suite to pass on machines without the platform under test. The
    three accessors below are the seam the tests replace.
    """
    import winreg

    return winreg


def _read_value(key: str, name: str) -> str | None:
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            value, _ = winreg.QueryValueEx(handle, name)
    except FileNotFoundError:
        return None
    except OSError:
        _log.warning("could not read autostart entry %s\\%s", key, name, exc_info=True)
        return None
    return str(value)


def _write_value(key: str, name: str, value: str) -> None:
    winreg = _winreg()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
        winreg.SetValueEx(handle, name, 0, winreg.REG_SZ, value)


def _delete_value(key: str, name: str) -> None:
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as handle:
            winreg.DeleteValue(handle, name)
    except FileNotFoundError:
        pass
    except OSError:
        _log.warning("could not remove autostart entry %s\\%s", key, name, exc_info=True)


def autostart_path() -> pathlib.PurePath:
    """Where the entry lives, for disclosure in the settings dialog before the user enables it.

    Returned as a path-like so both platform implementations answer the same shape. On Windows
    this names the registry; a value containing ``.config`` would mean the Linux module was
    reached by mistake, which is the defect D-07 fixed.
    """
    return pathlib.PureWindowsPath("HKCU") / _RUN_KEY / _VALUE_NAME


def is_autostart_enabled() -> bool:
    """Queried, never assumed — the registry value is the truth."""
    return _read_value(_RUN_KEY, _VALUE_NAME) is not None


#: Interpreter names that mean "we were launched as a package, not as a bundled executable".
_INTERPRETERS = {"python.exe", "pythonw.exe", "python", "pythonw", "-c"}


def _command() -> str:
    """The command Windows should run at sign-in.

    ``--hidden`` so an autostarted instance opens to the status area without taking focus, the
    same contract the Linux entry honours.

    The packaging form is deliberately **not** consulted: FR-026 keeps the frozen-bundle marker
    inside ``distribution.py`` so the two delivery forms cannot drift apart, and the same
    argv-shape check the Linux module uses answers this without asking how we were packaged.

    Quoted because the installed location (``%LOCALAPPDATA%\\Programs\\GPUM``) sits under a user
    profile path that routinely contains spaces — an unquoted value there silently starts
    nothing, which would be a toggle that reports success and does not work.
    """
    launched_as = sys.argv[0]
    if launched_as and pathlib.PurePath(launched_as).name.lower() not in _INTERPRETERS:
        return f'"{os.path.abspath(launched_as)}" --hidden'
    return f'"{sys.executable}" -m gpum --hidden'


def enable_autostart() -> pathlib.PurePath:
    """Write the entry. Returns the location so the caller can disclose it to the user."""
    _write_value(_RUN_KEY, _VALUE_NAME, _command())
    location = autostart_path()
    _log.info("autostart enabled: %s", location)
    return location


def disable_autostart() -> None:
    """Remove exactly what ``enable_autostart`` wrote. Idempotent."""
    _delete_value(_RUN_KEY, _VALUE_NAME)
    _log.info("autostart disabled: %s", autostart_path())
