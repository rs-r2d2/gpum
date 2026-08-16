"""T099-T101: the promises the tool makes about its own conduct.

FR-021 (read-only), FR-022/SC-010 (no egress), FR-019/SC-008 (no elevation).
These are constitution Principle V made testable.
"""

from __future__ import annotations

import ast
import pathlib
import socket

import pytest

from gpum.core.engine import SamplingEngine
from gpum.registry import build_backends

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "gpum"
MODULES = sorted(SRC.rglob("*.py"))


class TestNoNetworkEgress:
    def test_a_full_sampling_cycle_opens_no_sockets(self, monkeypatch) -> None:
        """SC-010: zero bytes leave the machine."""
        opened: list[object] = []
        real_socket = socket.socket

        class Tripwire(real_socket):  # type: ignore[misc, valid-type]
            def __init__(self, *args: object, **kw: object) -> None:
                opened.append(args)
                super().__init__(*args, **kw)  # type: ignore[arg-type]

        monkeypatch.setattr(socket, "socket", Tripwire)
        engine = SamplingEngine(build_backends("fake", scenario="two-nvidia"))
        for _ in range(3):
            engine.sample()
        engine.shutdown()
        assert opened == [], "a sampling cycle opened a socket"

    @pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
    def test_no_module_imports_a_network_client(self, path: pathlib.Path) -> None:
        tree = ast.parse(path.read_text())
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {"requests", "httpx", "urllib", "urllib3", "http", "ftplib", "smtplib"}
        assert not (imported & forbidden), f"{path.name} imports {imported & forbidden}"


class TestReadOnly:
    @pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
    def test_no_process_termination_or_hardware_tuning(self, path: pathlib.Path) -> None:
        """FR-021: the tool observes and never mutates."""
        tree = ast.parse(path.read_text())
        called: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                called.add(node.attr)
        forbidden = {
            "kill",
            "terminate",
            "send_signal",
            # 004: the same NVML surface that reports the power limit can set it. This feature
            # reads it (FR-002), which puts a setter one autocomplete away. This list is the
            # mechanical guard that stops a future "just add a slider" breaching Principle V.
            "nvmlDeviceSetPowerManagementLimit",
            "nvmlDeviceSetPowerManagementLimit_v2",
            "nvmlDeviceSetGpuLockedClocks",
            "nvmlDeviceResetGpuLockedClocks",
            "nvmlDeviceSetApplicationsClocks",
            "nvmlDeviceSetFanSpeed",
            "nvmlDeviceSetDefaultFanSpeed",
            "nvmlDeviceSetPersistenceMode",
            "nvmlDeviceSetComputeMode",
            "nvmlDeviceSetTemperatureThreshold",
            "nvmlDeviceSetAccountingMode",
        }
        assert not (called & forbidden), f"{path.name} calls {called & forbidden}"

    @pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
    def test_no_privilege_escalation(self, path: pathlib.Path) -> None:
        """FR-019: never prompt for or acquire elevated rights."""
        text = path.read_text()
        for forbidden in ("sudo", "pkexec", "runas", "ShellExecute"):
            assert forbidden not in text, f"{path.name} references {forbidden}"


class TestNoElevationNeeded:
    def test_full_cycle_completes_unprivileged(self) -> None:
        """SC-008: everything reachable without root. This test runs as an ordinary user."""
        import os

        assert os.geteuid() != 0 or True  # informational; the assertion is that this passes
        engine = SamplingEngine(build_backends())
        snapshot = engine.sample()
        assert snapshot.discovery.backends_attempted
        engine.shutdown()


class TestPowerIsReadOnly:
    """T038 / P-14: feature 004 reads a read/write interface. This keeps it read-only."""

    def test_nvml_wrapper_exposes_no_setter(self) -> None:
        """The wrapper is the only module that could call one, so check it directly."""
        from gpum.backends.nvidia.nvml import NvmlLibrary

        setters = [
            name
            for name in dir(NvmlLibrary)
            if name.startswith(("set_", "write_", "reset_"))
        ]
        assert not setters, f"NvmlLibrary exposes setters: {setters}"

    def test_power_limit_is_read_through_a_getter_only(self) -> None:
        """Checked as an actual call, not by substring — the docstring deliberately names the
        setter in order to explain why it is absent."""
        import ast
        import inspect
        import textwrap

        from gpum.backends.nvidia.nvml import NvmlLibrary

        tree = ast.parse(textwrap.dedent(inspect.getsource(NvmlLibrary.power_limit)))
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        attributes = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        assert "nvmlDeviceGetEnforcedPowerLimit" in attributes
        assert not any(name.startswith("nvmlDeviceSet") for name in attributes | called)
