#!/usr/bin/env python3
"""Concurrent comparison harness: our numbers vs the vendor's own tooling (research D-12).

This is the first thing in the project that checks the tool's output against reality — feature
001 was verified entirely against simulated devices.

**Sampling is concurrent, not sequential.** GPU memory moves continuously; sampling us and then
`nvidia-smi` measures the delay between the two reads, not their agreement. Both reads are
issued from threads started together and their timestamps recorded, so a comparison is only
counted when the two reads are close enough in time to be meaningful.

Emits a HardwareVerificationRecord as JSON (data-model.md), including the measured cycle cost
that sets the sampler's per-device timeout (FR-009).

Usage:
    python tools/compare-with-nvidia-smi.py --duration 600 --out verification.json
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field

sys.path.insert(0, "src")

from gpum.core.engine import SamplingEngine  # noqa: E402
from gpum.registry import (  # noqa: E402
    build_backends,
    select_attribution_provider,
    select_identity_provider,
)

#: A pair of reads further apart than this is discarded rather than compared — beyond it the
#: difference measures elapsed time, not disagreement.
MAX_PAIR_SKEW_S = 0.25

MIB = 1024 * 1024


@dataclass
class DeviceComparison:
    uuid: str
    ours_used_bytes: int
    theirs_used_bytes: int
    ours_total_bytes: int
    theirs_total_bytes: int
    skew_s: float

    @property
    def used_deviation_pct(self) -> float:
        if not self.theirs_used_bytes:
            return 0.0
        delta = abs(self.ours_used_bytes - self.theirs_used_bytes)
        return 100.0 * delta / self.theirs_used_bytes

    @property
    def total_matches(self) -> bool:
        # Totals are static; disagreement here is a unit bug, not sampling drift.
        return abs(self.ours_total_bytes - self.theirs_total_bytes) < 2 * MIB


@dataclass
class VerificationRecord:
    captured_at: str
    driver_version: str
    gpu_model: str
    duration_s: float
    sample_count: int
    max_memory_deviation_pct: float
    mean_memory_deviation_pct: float
    total_memory_mismatches: int
    process_match_rate: float
    process_samples: int
    mean_cycle_cost_ms: float
    p99_cycle_cost_ms: float
    max_cycle_cost_ms: float
    #: Cost of a single sample_device() call — what the per-device timeout actually guards.
    mean_device_query_ms: float = 0.0
    p99_device_query_ms: float = 0.0
    max_device_query_ms: float = 0.0
    recommended_timeout_ms: int = 0
    notes: list[str] = field(default_factory=list)


def nvidia_smi_devices() -> tuple[list[dict[str, object]], float]:
    """Query the vendor tool. Returns (rows, timestamp)."""
    started = time.monotonic()
    out = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=uuid,name,memory.total,memory.used,driver_version",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout
    rows = []
    for line in out.strip().splitlines():
        uuid, name, total, used, driver = (p.strip() for p in line.split(","))
        rows.append(
            {
                "uuid": uuid,
                "name": name,
                # nvidia-smi reports MiB with nounits; convert to bytes to match our model.
                "total": int(float(total)) * MIB,
                "used": int(float(used)) * MIB,
                "driver": driver,
            }
        )
    return rows, (started + time.monotonic()) / 2


def nvidia_smi_pids() -> set[int]:
    """Every PID nvidia-smi attributes to a GPU — graphics *and* compute.

    ``--query-compute-apps`` returns CUDA processes only. On a desktop the GPU is mostly used
    by graphics clients (the display server, browsers), so relying on that query alone made
    the process comparison pass with zero samples — a vacuous 100%. The plain-text process
    table lists both types, so it is parsed instead.
    """
    pids: set[int] = set()

    out = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    ).stdout
    for line in out.strip().splitlines():
        line = line.strip()
        if line.isdigit():
            pids.add(int(line))

    # Plain output: rows look like
    #   |    0   N/A  N/A      3099      G   /usr/lib/xorg/Xorg            188MiB |
    plain = subprocess.run(
        ["nvidia-smi"], capture_output=True, text=True, timeout=15, check=False
    ).stdout
    in_process_table = False
    for line in plain.splitlines():
        if "Processes:" in line:
            in_process_table = True
            continue
        if not in_process_table or not line.startswith("|"):
            continue
        fields = line.strip("| \t").split()
        # A data row carries a process type marker (G/C/C+G) followed by a command.
        for index, field_value in enumerate(fields):
            if field_value in {"G", "C", "C+G"} and index >= 1:
                for candidate in fields[:index]:
                    if candidate.isdigit() and len(candidate) >= 2:
                        pids.add(int(candidate))
                break
    return pids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=600.0, help="seconds (default 600)")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--out", default="verification.json")
    args = parser.parse_args()

    backends = build_backends("nvidia")
    attribution = select_attribution_provider(backends)
    identity = select_identity_provider()
    engine = SamplingEngine(
        backends, attribution_provider=attribution, identity_provider=identity
    )

    probe = engine.sample()
    if not probe.devices:
        print("No NVIDIA devices found; nothing to verify.", file=sys.stderr)
        return 2

    driver_version = ""
    gpu_model = probe.devices[0].name
    comparisons: list[DeviceComparison] = []
    cycle_costs_ms: list[float] = []
    device_query_ms: list[float] = []
    process_hits = 0
    process_total = 0
    notes: list[str] = []
    skipped_skew = 0

    deadline = time.monotonic() + args.duration
    started_wall = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    print(f"Comparing against nvidia-smi for {args.duration:.0f}s ...", flush=True)
    while time.monotonic() < deadline:
        # Both reads issued together — this is the point of the harness.
        t0 = time.monotonic()
        ours_future = pool.submit(engine.sample)
        theirs_future = pool.submit(nvidia_smi_devices)
        snapshot = ours_future.result(timeout=30)
        theirs, theirs_ts = theirs_future.result(timeout=30)
        cycle_costs_ms.append((time.monotonic() - t0) * 1000)

        by_uuid = {row["uuid"]: row for row in theirs}
        if theirs:
            driver_version = str(theirs[0]["driver"])

        for device in snapshot.devices:
            row = by_uuid.get(device.id.key)
            if row is None or not device.memory_used.is_measurement:
                continue
            skew = abs(time.monotonic() - theirs_ts)
            if skew > MAX_PAIR_SKEW_S:
                skipped_skew += 1
                continue
            comparisons.append(
                DeviceComparison(
                    uuid=device.id.key,
                    ours_used_bytes=int(device.memory_used.value),
                    theirs_used_bytes=int(row["used"]),
                    ours_total_bytes=int(device.memory_total.value),
                    theirs_total_bytes=int(row["total"]),
                    skew_s=skew,
                )
            )

        # Time a bare per-device query, which is what the timeout guards — the full cycle
        # also includes attribution and psutil identity resolution.
        for backend in backends:
            for device in backend.enumerate_devices():
                if not device.supported:
                    continue
                d0 = time.monotonic()
                backend.sample_device(device.id)
                device_query_ms.append((time.monotonic() - d0) * 1000)

        their_pids = nvidia_smi_pids()
        if their_pids:
            our_pids = {p.pid for p in snapshot.processes}
            process_total += len(their_pids)
            process_hits += len(their_pids & our_pids)
            missing = their_pids - our_pids
            if missing:
                notes.append(f"pids reported by nvidia-smi but not by us: {sorted(missing)}")

        time.sleep(args.interval)

    pool.shutdown(wait=False)
    engine.shutdown()

    if not comparisons:
        print("No comparable samples collected.", file=sys.stderr)
        return 2

    deviations = [c.used_deviation_pct for c in comparisons]
    mismatched_totals = sum(1 for c in comparisons if not c.total_matches)
    if skipped_skew:
        notes.append(f"{skipped_skew} sample pairs discarded for exceeding the skew budget")

    ordered = sorted(cycle_costs_ms)
    p99 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.99))]

    dq = sorted(device_query_ms) or [0.0]
    dq_p99 = dq[min(len(dq) - 1, int(len(dq) * 0.99))]
    # 20x the measured p99, rounded up to 50 ms. Generous enough that a momentarily busy
    # driver is not misreported as timed out, tight enough that a wedged one is caught within
    # a refresh interval.
    recommended = max(50, int(round(dq_p99 * 20 / 50.0)) * 50)

    record = VerificationRecord(
        captured_at=started_wall,
        driver_version=driver_version,
        gpu_model=gpu_model,
        duration_s=args.duration,
        sample_count=len(comparisons),
        max_memory_deviation_pct=round(max(deviations), 3),
        mean_memory_deviation_pct=round(statistics.fmean(deviations), 3),
        total_memory_mismatches=mismatched_totals,
        process_match_rate=(100.0 * process_hits / process_total) if process_total else 100.0,
        process_samples=process_total,
        mean_cycle_cost_ms=round(statistics.fmean(cycle_costs_ms), 3),
        p99_cycle_cost_ms=round(p99, 3),
        max_cycle_cost_ms=round(max(cycle_costs_ms), 3),
        mean_device_query_ms=round(statistics.fmean(dq), 3),
        p99_device_query_ms=round(dq_p99, 3),
        max_device_query_ms=round(max(dq), 3),
        recommended_timeout_ms=recommended,
        notes=notes,
    )

    with open(args.out, "w") as handle:
        json.dump(asdict(record), handle, indent=2)

    print(json.dumps(asdict(record), indent=2))

    if not process_total:
        notes.append(
            "no GPU processes were observed; the process match rate is vacuous for this run"
        )
    ok = (
        record.max_memory_deviation_pct <= 5.0
        and record.process_match_rate >= 100.0
        and record.total_memory_mismatches == 0
        # A 100% match over zero samples proves nothing and must not pass (SC-004).
        and process_total > 0
    )
    print("\nVERDICT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
