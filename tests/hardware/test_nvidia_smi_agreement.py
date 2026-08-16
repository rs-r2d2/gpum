"""T013: our numbers vs nvidia-smi, on real hardware (SC-003, SC-004).

The first check in the project against reality rather than a simulation.
"""

from __future__ import annotations

import subprocess
import time

import pytest

from gpum.core.engine import SamplingEngine
from gpum.registry import (
    build_backends,
    select_attribution_provider,
    select_identity_provider,
)

MIB = 1024 * 1024
#: Memory moves continuously, so agreement is only meaningful for near-simultaneous reads.
TOLERANCE_PCT = 5.0


def _smi_rows() -> dict[str, dict[str, int]]:
    out = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=uuid,memory.total,memory.used",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout
    rows = {}
    for line in out.strip().splitlines():
        uuid, total, used = (p.strip() for p in line.split(","))
        rows[uuid] = {"total": int(float(total)) * MIB, "used": int(float(used)) * MIB}
    return rows


def _smi_pids() -> set[int]:
    plain = subprocess.run(
        ["nvidia-smi"], capture_output=True, text=True, timeout=15, check=False
    ).stdout
    pids: set[int] = set()
    seen_header = False
    for line in plain.splitlines():
        if "Processes:" in line:
            seen_header = True
            continue
        if not seen_header or not line.startswith("|"):
            continue
        fields = line.strip("| \t").split()
        for index, value in enumerate(fields):
            if value in {"G", "C", "C+G"} and index >= 1:
                for candidate in fields[:index]:
                    if candidate.isdigit() and len(candidate) >= 2:
                        pids.add(int(candidate))
                break
    return pids


@pytest.fixture
def engine() -> SamplingEngine:
    backends = build_backends("nvidia")
    eng = SamplingEngine(
        backends,
        attribution_provider=select_attribution_provider(backends),
        identity_provider=select_identity_provider(),
    )
    if not eng.sample().devices:
        eng.shutdown()
        pytest.skip("no NVIDIA devices present")
    yield eng
    eng.shutdown()


class TestMemoryAgreement:
    def test_total_memory_matches_exactly(self, engine: SamplingEngine) -> None:
        """Total is static — any disagreement is a unit bug, not sampling drift."""
        theirs = _smi_rows()
        for device in engine.sample().devices:
            if device.id.key not in theirs:
                continue
            assert abs(device.memory_total.value - theirs[device.id.key]["total"]) < 2 * MIB

    def test_used_memory_within_tolerance(self, engine: SamplingEngine) -> None:
        """SC-003. This is the assertion that caught driver-reserved memory being reported as
        used — a ~90% overstatement before the v2 memory struct was adopted."""
        worst = 0.0
        for _ in range(10):
            snapshot = engine.sample()
            theirs = _smi_rows()
            for device in snapshot.devices:
                row = theirs.get(device.id.key)
                if row is None or not device.memory_used.is_measurement:
                    continue
                if not row["used"]:
                    continue
                deviation = 100.0 * abs(device.memory_used.value - row["used"]) / row["used"]
                worst = max(worst, deviation)
            time.sleep(0.5)
        assert worst <= TOLERANCE_PCT, f"worst deviation {worst:.2f}% exceeds {TOLERANCE_PCT}%"

    def test_used_never_exceeds_total(self, engine: SamplingEngine) -> None:
        for device in engine.sample().devices:
            if device.memory_used.is_measurement and device.memory_total.is_measurement:
                assert device.memory_used.value <= device.memory_total.value


class TestProcessAgreement:
    def test_every_smi_process_appears(self, engine: SamplingEngine) -> None:
        """SC-004: 100% of processes nvidia-smi reports must appear in our list."""
        theirs = _smi_pids()
        if not theirs:
            pytest.skip("no GPU processes running")
        ours = {p.pid for p in engine.sample().processes}
        missing = theirs - ours
        assert not missing, f"nvidia-smi reports GPU processes we do not: {sorted(missing)}"

    def test_processes_are_named(self, engine: SamplingEngine) -> None:
        snapshot = engine.sample()
        if not snapshot.processes:
            pytest.skip("no GPU processes running")
        named = [p for p in snapshot.processes if p.name]
        assert named, "no GPU process could be identified"

    def test_process_memory_is_measured_on_linux(self, engine: SamplingEngine) -> None:
        """NVML supplies per-process memory on Linux; on Windows/WDDM it does not, which is
        reported honestly rather than as zero."""
        snapshot = engine.sample()
        if not snapshot.processes:
            pytest.skip("no GPU processes running")
        measured = [p for p in snapshot.processes if p.memory_used.is_measurement]
        assert measured, "no per-process memory obtained on Linux"
        for process in snapshot.processes:
            if not process.memory_used.is_measurement:
                assert process.memory_used.value is None
                assert process.memory_used.reason


class TestDeviceIdentity:
    def test_uuid_matches_nvidia_smi(self, engine: SamplingEngine) -> None:
        theirs = set(_smi_rows())
        ours = {d.id.key for d in engine.sample().devices}
        assert ours & theirs, "device keys do not correspond to nvidia-smi UUIDs"

    def test_identity_is_stable_across_samples(self, engine: SamplingEngine) -> None:
        first = {d.id.key for d in engine.sample().devices}
        for _ in range(5):
            assert {d.id.key for d in engine.sample().devices} == first
