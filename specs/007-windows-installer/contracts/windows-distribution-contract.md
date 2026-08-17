# Contract: Windows distribution

**Modules**: `packaging/gpum.spec`, `packaging/windows/`, `src/gpum/adapters/__init__.py`,
`src/gpum/adapters/windows/autostart.py`, `src/gpum/ui/app.py` |
**Feature**: 007-windows-installer

---

## Artifact obligations

**MUST**: produce an installer and a portable executable from one PyInstaller spec; run on a
machine with no Python, no package manager and no compiler; launch and show real data within 5 s;
publish a SHA-256 alongside each artifact; carry everything needed to install and run offline.

**MUST NOT**: contain any NVIDIA driver component — `nvml.dll`, `nvcuda.dll`, `nvapi64.dll`, or a
fat-binary loader. This is the failure that is invisible on the build host and wrong on the
user's, so it is build-blocking rather than reviewed.

**MUST NOT**: assume artifacts are unsigned. No step may break when a signature is later
appended.

## Installer obligations

**MUST**: install under `%LOCALAPPDATA%`, register uninstall under `HKCU`, create a Start menu
entry, offer a desktop shortcut and start-at-login as user choices rather than defaults, and
verify Windows version and architecture before writing anything.

**MUST**: on uninstall, remove the application, its Start menu entry, any shortcut it created,
and any autostart entry it set.

**MUST**: on upgrade over an existing installation, leave exactly one installation and one
uninstall entry.

**MUST**: refuse, with a stated reason, when the application is running or the platform is
unsupported.

**MUST NOT**: prompt for elevation, write under `%ProgramFiles%` or `HKLM`, contact the network,
or remove the user's saved preferences.

## Autostart obligations

*Applies equally to both platform implementations; this is what makes the toggle honest.*

**MUST**: expose `is_autostart_enabled`, `enable_autostart`, `disable_autostart` and
`autostart_path` from every platform implementation; treat the entry's presence as the single
source of truth; write only when the user enables it; leave the system as found when disabled.

**MUST NOT**: report a capability as enabled on a platform where the entry has no effect. A
toggle that writes a file nothing reads and then reports success is the same category of fault as
rendering an unavailable metric as zero.

## Layering obligations

**MUST**: resolve the autostart implementation through `gpum.adapters`, which holds the single OS
switch.

**MUST NOT**: import `gpum.adapters.linux.*` or `gpum.adapters.windows.*` from `ui`, `core`, or
`backends`. Enforced by `tests/unit/test_import_boundaries.py` — the existing rule catches
`sys.platform` branching and missed a direct unconditional import of a platform module, which is
how this defect reached a release.

## Equivalence obligations

**MUST**: report the same version from every delivery form built from the same source; resolve
the same preference store across all forms on one machine; behave identically regardless of
delivery form.

**MUST NOT**: add a `DistributionKind` value per artifact, or branch any behaviour on the
delivery form. It is diagnostic only.

## Truthfulness obligations on Windows

**MUST**: obtain every measurement from the host's own driver library, resolved at run time;
report per-process GPU memory as explicitly unavailable with a reason under driver models that
cannot supply it; agree with the vendor's own tool within the tolerance the project applies on
Linux, using the same bracketed comparison feature 006 established.

**MUST NOT**: substitute zero for any figure the platform cannot supply; mark any capability
matrix cell as observed on the strength of a CI run, which has no GPU.
