"""T010: the layering rules, enforced mechanically (contract C-12, C-13).

A failure here is a constitution violation (Principle I / II), not a style nit. Fix the
import; never relax the test.
"""

import ast
import pathlib

import pytest

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "gpum"


def _imports(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def _modules(*parts: str) -> list[pathlib.Path]:
    root = SRC.joinpath(*parts)
    return sorted(root.rglob("*.py")) if root.exists() else []


def _ids(paths: list[pathlib.Path]) -> list[str]:
    return [str(p.relative_to(SRC)) for p in paths]


CORE = _modules("core")
BACKENDS = _modules("backends")
ADAPTERS = _modules("adapters")
ALL = _modules()


@pytest.mark.parametrize("path", CORE, ids=_ids(CORE))
def test_core_imports_no_qt_no_vendor_no_platform(path: pathlib.Path) -> None:
    """core must be importable and testable without a QApplication."""
    for name in _imports(path):
        root = name.split(".")[0]
        assert root not in {"PySide6", "PyQt5", "PyQt6", "pynvml", "psutil"}, (
            f"{path.name} imports {name}; core must stay free of Qt and vendor/OS libraries"
        )
        assert not name.startswith("gpum.ui"), f"{path.name} imports {name}"
        assert not name.startswith("gpum.backends."), f"{path.name} imports {name}"
        assert not name.startswith("gpum.adapters."), f"{path.name} imports {name}"


@pytest.mark.parametrize("path", BACKENDS, ids=_ids(BACKENDS))
def test_backends_do_not_import_core_ui_or_adapters(path: pathlib.Path) -> None:
    """C-12: adding a vendor must not require touching anything else."""
    for name in _imports(path):
        assert not name.startswith("gpum.ui"), f"{path.name} imports {name}"
        assert not name.startswith("gpum.adapters"), f"{path.name} imports {name}"
        assert name.split(".")[0] not in {"PySide6", "PyQt5", "PyQt6"}, (
            f"{path.name} imports Qt"
        )


@pytest.mark.parametrize("path", ALL, ids=_ids(ALL))
def test_only_the_nvml_wrapper_imports_pynvml(path: pathlib.Path) -> None:
    """C-13: the single most important guard against an NVML-shaped abstraction."""
    if any(name.split(".")[0] == "pynvml" for name in _imports(path)):
        assert path.relative_to(SRC).as_posix() == "backends/nvidia/nvml.py", (
            f"{path} imports pynvml; only backends/nvidia/nvml.py may"
        )


@pytest.mark.parametrize("path", ALL, ids=_ids(ALL))
def test_only_ui_imports_qt(path: pathlib.Path) -> None:
    if any(name.split(".")[0] in {"PySide6", "PyQt5", "PyQt6"} for name in _imports(path)):
        assert path.relative_to(SRC).parts[0] == "ui", f"{path} imports Qt outside ui/"


@pytest.mark.parametrize("path", CORE + BACKENDS, ids=_ids(CORE + BACKENDS))
def test_no_os_branching_outside_adapters(path: pathlib.Path) -> None:
    """Principle II: OS-conditional logic lives only in adapters/."""
    text = path.read_text()
    for marker in ("sys.platform", "platform.system()", "os.name =="):
        assert marker not in text, (
            f"{path.name} branches on the OS; that belongs in gpum/adapters/"
        )


# --- feature 002 additions -------------------------------------------------

UI = _modules("ui")
LINUX_ADAPTERS = _modules("adapters", "linux")


@pytest.mark.parametrize("path", UI, ids=_ids(UI))
def test_ui_does_not_import_dbus(path: pathlib.Path) -> None:
    """Contract T-12: the tray *widget* is cross-platform Qt; the DBus availability probe is
    Linux-specific and belongs in adapters/linux/tray_probe.py (Principle II)."""
    for name in _imports(path):
        root = name.split(".")[0]
        assert root not in {"dbus", "jeepney", "pydbus", "sdbus"}, (
            f"{path.name} imports {name}; DBus belongs in adapters/linux/"
        )


@pytest.mark.parametrize("path", ALL, ids=_ids(ALL))
def test_application_never_imports_build_tooling(path: pathlib.Path) -> None:
    """packaging/ and tools/ are not application code and must not reach the runtime import
    path — the app must not be able to observe how it was packaged (FR-026)."""
    for name in _imports(path):
        root = name.split(".")[0]
        assert root not in {"PyInstaller", "packaging_scripts"}, (
            f"{path.name} imports build tooling ({name})"
        )
        assert not name.startswith("tools."), f"{path.name} imports {name}"


@pytest.mark.parametrize("path", LINUX_ADAPTERS, ids=_ids(LINUX_ADAPTERS))
def test_linux_adapters_do_not_import_ui(path: pathlib.Path) -> None:
    for name in _imports(path):
        assert not name.startswith("gpum.ui"), f"{path.name} imports {name}"


# --- feature 007 additions -------------------------------------------------

FEATURE_CODE = CORE + BACKENDS + UI


@pytest.mark.parametrize("path", FEATURE_CODE, ids=_ids(FEATURE_CODE))
def test_t003_feature_code_does_not_import_a_platform_adapter(path: pathlib.Path) -> None:
    """Principle II, in the shape the existing rules missed (feature 007, D-07).

    ``test_no_os_branching_outside_adapters`` looks for ``sys.platform`` conditionals. This one
    catches the other way to bind feature code to one OS: importing the platform module by name,
    unconditionally, with no branch to find.

    That is not hypothetical. ``ui/app.py`` did exactly this with
    ``from gpum.adapters.linux import autostart``, and on Windows it reported the autostart
    location as ``C:\\Users\\<user>\\.config\\autostart\\gpum.desktop``, wrote a file nothing on
    Windows reads, and told the user the setting was enabled. A capability claimed but absent is
    the same fault as a metric rendered as zero when it was never measured.

    Feature code imports ``gpum.adapters``; the switch inside it picks the implementation.
    """
    for name in _imports(path):
        assert not name.startswith("gpum.adapters.linux"), (
            f"{path.name} imports {name}; import gpum.adapters and let it choose"
        )
        assert not name.startswith("gpum.adapters.windows"), (
            f"{path.name} imports {name}; import gpum.adapters and let it choose"
        )
