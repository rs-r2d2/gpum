"""Backend and attribution-provider discovery — the application's composition root.

This lives at the package root rather than in ``core`` on purpose. A registry has to know
about every backend and adapter in order to construct them, and ``core`` importing
``backends`` would invert the one-way dependency arrow the constitution requires
(``backends`` -> ``core`` -> ``ui``). Keeping wiring above ``core`` lets ``core`` stay a pure
domain layer that nothing else in the application depends upon.

Constructions are still deferred into factories so that importing this module does not drag
in every vendor binding.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from gpum.adapters.base import ProcessAttributionProvider, ProcessIdentityProvider
    from gpum.backends.base import GpuBackend

__all__ = [
    "all_backends",
    "build_backends",
    "present_gpu_probe",
    "select_attribution_provider",
    "select_identity_provider",
]


def _nvidia() -> Any:
    from gpum.backends.nvidia.backend import NvidiaBackend

    return NvidiaBackend()


def _amd() -> Any:
    from gpum.backends.amd.backend import AMDBackend

    return AMDBackend()


def _intel() -> Any:
    from gpum.backends.intel.backend import IntelBackend

    return IntelBackend()


def _fake(scenario: str | None = None) -> Any:
    from gpum.backends.fake.backend import FakeBackend

    return FakeBackend(scenario)


#: Probe order. Stubs are included on purpose: the discovery report names every vendor that
#: was looked for, so "AMD: not supported in this release" reaches the user (FR-018, SC-006).
_BACKEND_FACTORIES: dict[str, Callable[[], Any]] = {
    "nvidia": _nvidia,
    "amd": _amd,
    "intel": _intel,
}


def build_backends(
    selection: str | None = None, *, scenario: str | None = None
) -> list[GpuBackend]:
    """Construct the backends for this run.

    ``selection`` may be ``None`` (all real backends), ``"fake"``, ``"none"``, or a single
    vendor name. ``"none"`` yields an empty list, which is a supported configuration — the
    tool must stay usable with no backends at all (FR-018).
    """
    if selection == "none":
        return []
    if selection == "fake":
        return [_fake(scenario)]
    if selection:
        factory = _BACKEND_FACTORIES.get(selection)
        if factory is None:
            raise ValueError(f"unknown backend {selection!r}")
        return [factory()]
    return [factory() for factory in _BACKEND_FACTORIES.values()]


def all_backends() -> list[GpuBackend]:
    """Every backend including the fake — used by the shared contract suite so a new vendor
    inherits the tests automatically."""
    return [*build_backends(), _fake()]


def select_attribution_provider(
    backends: Sequence[GpuBackend],
) -> ProcessAttributionProvider | None:
    """Pick an attribution source, per contracts/process-attribution.md.

    Order: a backend's own companion provider, then the platform adapter, then nothing.
    Returning ``None`` is a supported, tested outcome — it is what NVIDIA-on-Windows looks
    like before the PDH adapter lands, and the tool stays fully useful for device metrics.
    """
    for backend in backends:
        provider = _companion_provider(backend)
        if provider is not None and provider.probe().available:
            return provider

    platform_provider = _platform_attribution_provider()
    if platform_provider is not None and platform_provider.probe().available:
        return platform_provider
    return None


def _companion_provider(backend: GpuBackend) -> ProcessAttributionProvider | None:
    if getattr(backend, "vendor", None) is None:
        return None
    if backend.name != "nvidia":
        return None
    try:
        from gpum.backends.nvidia.attribution import NvmlAttributionProvider
    except ImportError:  # pragma: no cover - defensive
        return None
    return NvmlAttributionProvider(backend)


def _platform_attribution_provider() -> ProcessAttributionProvider | None:
    """Resolved through the adapters package, which owns all OS branching."""
    from gpum.adapters import platform_attribution_provider

    return platform_attribution_provider()


def present_gpu_probe() -> Callable[[], list[object]]:
    """A callable returning physically-present GPUs, for injection into the engine."""
    from gpum.adapters import present_gpus

    return present_gpus


def select_identity_provider() -> ProcessIdentityProvider:
    from gpum.adapters import platform_identity_provider

    return platform_identity_provider()
