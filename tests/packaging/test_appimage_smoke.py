"""T027: the two distribution forms must be indistinguishable (E-01..E-08).

Requires a built AppImage; marked `packaging` and deselected by default. Build with:

    docker build -f packaging/Dockerfile.build -t gpum-build .
    docker run --rm -v "$PWD:/src" gpum-build /src/packaging/build-appimage.sh
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / "dist"

_ENV = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}


def _appimage() -> pathlib.Path:
    found = sorted(DIST.glob("GPUM-*-x86_64.AppImage"))
    if not found:
        pytest.skip("no AppImage built; see docs/building.md")
    return found[-1]


@pytest.fixture(scope="module")
def bundle() -> pathlib.Path:
    return _appimage()


def _run_bundle(bundle: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(bundle), *args], capture_output=True, text=True, timeout=120, env=_ENV
    )


def _run_package(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "gpum", *args],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=REPO,
        env=_ENV,
    )


class TestEquivalence:
    def test_e01_versions_match(self, bundle: pathlib.Path) -> None:
        """A bug report from either form must be reproducible against the other."""
        theirs = _run_bundle(bundle, "--version").stdout.strip()
        ours = _run_package("--version").stdout.strip()
        assert theirs.split()[1] == ours.split()[1], f"{theirs!r} vs {ours!r}"

    def test_e03_bundle_starts_and_reports(self, bundle: pathlib.Path) -> None:
        result = _run_bundle(bundle, "--version")
        assert result.returncode == 0, result.stderr

    def test_e04_bundle_runs_without_a_driver(self, bundle: pathlib.Path) -> None:
        """FR-018: absence of NVIDIA support is reported, never fatal."""
        result = _run_bundle(bundle, "--list-scenarios")
        assert result.returncode == 0
        assert "two-nvidia" in result.stdout

    def test_e05_same_scenario_listing(self, bundle: pathlib.Path) -> None:
        assert (
            _run_bundle(bundle, "--list-scenarios").stdout
            == _run_package("--list-scenarios").stdout
        )

    def test_e06_no_elevation_required(self, bundle: pathlib.Path) -> None:
        assert os.geteuid() != 0, "run this suite unprivileged"
        assert _run_bundle(bundle, "--version").returncode == 0


class TestBundleContents:
    def test_no_driver_library_shipped(self, bundle: pathlib.Path, tmp_path) -> None:
        """The most important assertion here. A bundled libnvidia-ml is version-locked to the
        build machine's driver and misreports silently on any other."""
        subprocess.run(
            [str(bundle), "--appimage-extract"],
            cwd=tmp_path,
            capture_output=True,
            timeout=180,
            check=True,
        )
        root = tmp_path / "squashfs-root"
        offenders = [
            p.name
            for p in root.rglob("*")
            if p.is_file()
            and any(
                p.name.startswith(prefix)
                for prefix in ("libnvidia-", "libcuda", "libGLX_nvidia")
            )
        ]
        assert not offenders, f"driver libraries bundled: {offenders}"

    def test_excluded_qt_modules_absent(self, bundle: pathlib.Path, tmp_path) -> None:
        subprocess.run(
            [str(bundle), "--appimage-extract"],
            cwd=tmp_path,
            capture_output=True,
            timeout=180,
            check=True,
        )
        root = tmp_path / "squashfs-root"
        banned = [
            p.name
            for p in root.rglob("libQt6*")
            if p.name.startswith(("libQt6WebEngine", "libQt6Quick", "libQt6Qml"))
        ]
        assert not banned, f"excluded Qt modules bundled: {banned}"

    def test_within_download_budget(self, bundle: pathlib.Path) -> None:
        size_mb = bundle.stat().st_size / (1024 * 1024)
        assert size_mb <= 120, f"bundle is {size_mb:.0f} MB"


class TestSharedPreferences:
    def test_e02_both_forms_use_the_same_config_path(self, bundle: pathlib.Path) -> None:
        """FR-028: a user switching forms keeps their settings. The way this breaks is a
        wrapper script setting a private XDG_CONFIG_HOME."""
        apprun = (REPO / "packaging" / "AppRun").read_text()
        assert "XDG_CONFIG_HOME" not in apprun or "export XDG_CONFIG_HOME" not in apprun
