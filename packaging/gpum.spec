# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the self-contained bundle (research D-03).

Two separate exclusion rules, for two different reasons.

**Excluded for size**: PySide6 installs at roughly 400 MB and GPUM uses QtCore, QtGui, and
QtWidgets only. Without trimming, the download is unusable.

**Never bundled — correctness, not size**: NVIDIA driver libraries. NVML is version-locked to
the host's kernel module. A copy taken from the build machine either fails to initialise or,
worse, misreports against a different host driver — wrong numbers presented as measurements on
someone else's machine, silently. `nvidia-ml-py` is pure Python over ctypes and resolves the
library at call time — `libnvidia-ml.so.1` by name on Linux, `System32\nvml.dll` by absolute
path on Windows — so excluding it is sufficient and correct on both.

**One spec, two platforms** (feature 007). The tables below are selected per platform because
the same libraries carry different names (`libQt6Quick.so.6` vs `Qt6Quick.dll`) and paths use
different separators. A single Linux-shaped table would appear configured and silently exclude
nothing on Windows.

`packaging/verify-appdir.sh` (Linux) and `packaging/windows/verify-dist.ps1` (Windows) enforce
these as build-blocking checks, because none of these failures is visible on the build host.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

sys.setrecursionlimit(5000)

PROJECT_ROOT = Path(SPECPATH).parent

# Size: Qt modules GPUM does not use.
EXCLUDED_MODULES = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets", "PySide6.QtQml",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtSerialPort",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtUiTools",
    "tkinter", "unittest", "pydoc", "doctest", "pytest", "numpy", "PIL",
]

# Correctness: driver components must come from the host, never from this build machine.
#
# Both platforms, because the reason is the same on both: the management library is
# version-locked to the host's kernel driver, and a copy taken from the build machine either
# fails to initialise or misreports against a different host driver — wrong numbers presented as
# measurements, silently. On Windows `nvidia-ml-py` loads `%WINDIR%\System32\nvml.dll` (DCH) or
# `%ProgramFiles%\NVIDIA Corporation\NVSMI\nvml.dll` by absolute path at call time, so excluding
# these is both sufficient and correct (feature 007, research D-03).
FORBIDDEN_BINARY_PREFIXES_LINUX = (
    "libnvidia-", "libcuda", "libGLX_nvidia", "libnvcuvid", "libnvoptix", "libglvnd",
)
FORBIDDEN_BINARY_PREFIXES_WINDOWS = (
    "nvml", "nvcuda", "nvapi", "nvfatbinaryloader", "nvrtc", "cudart",
)
FORBIDDEN_BINARY_PREFIXES = (
    FORBIDDEN_BINARY_PREFIXES_WINDOWS if sys.platform.startswith("win")
    else FORBIDDEN_BINARY_PREFIXES_LINUX
)

# Size: Qt shared objects pulled in transitively. Excluding the Python module is not enough —
# PySide6's hooks collect the libraries as dependencies regardless, which is how a 400 MB Qt
# install leaks back into a bundle that only needs three modules.
#
# Named per platform: the same libraries are `libQt6Quick.so.6` on Linux and `Qt6Quick.dll` on
# Windows, so a single table silently excludes nothing on the other platform (feature 007).
_UNUSED_QT_MODULES = (
    "Quick", "Qml", "WebEngine", "WebChannel", "WebSockets",
    "3D", "Multimedia", "Charts", "DataVisualization",
    "Designer", "Help", "Sql", "Test", "Pdf",
    "Bluetooth", "Nfc", "Positioning", "Location",
    "SerialPort", "Quick3D", "ShaderTools", "Spatial",
)
UNUSED_QT_LIBRARY_PREFIXES = tuple(
    (f"Qt6{m}" if sys.platform.startswith("win") else f"libQt6{m}") for m in _UNUSED_QT_MODULES
)

# Directories of Qt plugins GPUM never loads.
UNUSED_PLUGIN_DIRS = (
    "qml", "Qt/qml", "plugins/multimedia", "plugins/sqldrivers", "plugins/webview",
    "plugins/designer", "plugins/geometryloaders", "plugins/renderers", "plugins/sceneparsers",
)


def _as_posix(dest):
    """Normalise a destination path for substring matching.

    PyInstaller emits native separators, so a table written with ``/`` matches nothing on
    Windows — the exclusion would appear to be configured and silently do nothing, which is the
    worst of the three outcomes (feature 007).
    """
    return str(dest).replace("\\", "/")


def _strip_driver_libraries(binaries):
    """Remove host-driver components (correctness) and unused Qt modules (size)."""
    kept = []
    for entry in binaries:
        dest = _as_posix(entry[0])
        name = Path(dest).name
        if any(name.startswith(prefix) for prefix in FORBIDDEN_BINARY_PREFIXES):
            print(f"gpum.spec: excluding driver library {name} (research D-03)")
            continue
        if any(name.startswith(prefix) for prefix in UNUSED_QT_LIBRARY_PREFIXES):
            continue
        if any(part in dest for part in UNUSED_PLUGIN_DIRS):
            continue
        kept.append(entry)
    return kept


def _strip_data(datas):
    kept = []
    for entry in datas:
        dest = _as_posix(entry[0])
        name = Path(dest).name
        # PySide6's hook collects some Qt libraries as *data*, not binaries, so the same
        # prefix rule has to be applied on both lists or the exclusions leak straight back in.
        if any(name.startswith(prefix) for prefix in UNUSED_QT_LIBRARY_PREFIXES):
            continue
        if any(part in dest for part in UNUSED_PLUGIN_DIRS):
            continue
        # Translations are ~30 MB and GPUM ships English only.
        if "/translations/" in dest or dest.startswith("PySide6/Qt/translations"):
            continue
        kept.append(entry)
    return kept


a = Analysis(
    [str(PROJECT_ROOT / "src" / "gpum" / "__main__.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    # Package metadata must travel with the bundle: `importlib.metadata` is the single source
    # of version truth (research D-13), and without it the bundle reports a different version
    # from the pip install, breaking the equivalence FR-026 requires.
    datas=[
        (str(PROJECT_ROOT / "src" / "gpum" / "resources"), "gpum/resources"),
        *copy_metadata("gpum"),
    ],
    hiddenimports=["gpum", "pynvml", "psutil"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDED_MODULES,
    noarchive=False,
)

a.binaries = _strip_driver_libraries(a.binaries)
a.datas = _strip_data(a.datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gpum",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=False,
    name="gpum",
)
