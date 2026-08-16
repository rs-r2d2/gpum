"""Container membership from /proc (FR-029, FR-030, research D-06).

Reads only ``/proc/<pid>/cgroup``. Deliberately does **not** talk to the Docker socket: that
would require group membership the user may not have, which sits badly against the
constitution's least-privilege principle. The trade-off is that this yields the container
*ID*, not its human-readable name — naming requires the daemon API and is out of scope.
"""

from __future__ import annotations

import re

__all__ = ["container_id_for_pid"]

# Matches the 64-hex-char IDs Docker/containerd embed in cgroup paths, in both cgroup v1
# (/docker/<id>) and v2 (/system.slice/docker-<id>.scope) layouts, plus Podman's libpod form.
_PATTERNS = (
    re.compile(r"/docker[-/]([0-9a-f]{12,64})"),
    re.compile(r"/libpod[-/]([0-9a-f]{12,64})"),
    re.compile(r"/cri-containerd[-/]([0-9a-f]{12,64})"),
    re.compile(r"/kubepods.*?/([0-9a-f]{32,64})"),
    re.compile(r"[-/]([0-9a-f]{64})\.scope"),
)


def container_id_for_pid(pid: int, *, proc_root: str = "/proc") -> str | None:
    """The container ID owning ``pid``, or ``None`` when it is not containerised.

    Returns ``None`` on any read failure — a process may exit between the GPU query and this
    lookup, which is expected rather than exceptional.
    """
    try:
        with open(f"{proc_root}/{pid}/cgroup", encoding="utf-8") as handle:
            content = handle.read()
    except (OSError, PermissionError):
        return None
    return container_id_from_cgroup(content)


def container_id_from_cgroup(content: str) -> str | None:
    """Extracted for testing without a running container."""
    for line in content.splitlines():
        for pattern in _PATTERNS:
            match = pattern.search(line)
            if match:
                return match.group(1)
    return None
