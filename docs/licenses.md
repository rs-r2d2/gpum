# Third-party licences

Constitution tech constraints require dependencies to be licence-compatible with the project's
distribution licence, and copyleft-incompatible additions to be rejected in review.

**Project licence**: LGPL-3.0-or-later (chosen to match PySide6, see research D-01).

## Runtime dependencies

| Package | Licence | Compatible | Notes |
|---|---|---|---|
| PySide6 | LGPL-3.0 / commercial | ✅ | The reason PySide6 was chosen over PyQt6, which is GPL-3.0 / commercial and would force the whole application to GPL. Dynamic linking only — no PySide6 source is vendored. |
| psutil | BSD-3-Clause | ✅ | Permissive. |
| nvidia-ml-py (`[nvidia]` extra) | BSD-3-Clause | ✅ | Optional at install time. Pure Python over ctypes; the NVIDIA *driver* it talks to is proprietary but is not distributed with this project. |

## Development dependencies

pytest (MIT), pytest-qt (MIT), pytest-cov (MIT), ruff (MIT), mypy (MIT) — all permissive, and
none are distributed with the application.

## Review rule

Adding a GPL-licensed runtime dependency would require relicensing the project and **must** be
rejected unless that relicensing is an explicit, separate decision.

## ⚠️ Unresolved: this project declares two different licences

Found while assessing the Windows installer framework (feature 007, T001). The repository does
not agree with itself about its own licence:

| Source | Declares |
|---|---|
| `LICENSE` | **MIT** — "Copyright (c) 2026 Rishabh Sethi", the full 21-line MIT text |
| `pyproject.toml` | **LGPL-3.0-or-later** |
| `docs/licenses.md` (this file, above) | **LGPL-3.0-or-later**, "chosen to match PySide6, see research D-01" |

`LICENSE` is the file that actually governs redistribution, and it is the one that disagrees
with the reasoning recorded everywhere else. The whole PySide6-over-PyQt6 decision was made to
keep the project LGPL rather than GPL, which only makes sense if the project is LGPL.

**This is already shipping.** The published AppImage bundles PySide6 under LGPL-3.0, and it was
attached to a public release alongside a repository whose `LICENSE` says MIT. Anyone reading
`LICENSE` is being told they may sublicense and relicense a bundle that contains LGPL code.

**Why it blocks the Windows installer**: the constitution requires distributed dependencies to
be licence-compatible with the project's distribution licence. The Qt Installer Framework is
distributed under GPL/LGPL terms, and unlike a pure build tool its maintenance tool ships
*inside* the artifact users receive — so it is a distributed component and the rule applies.
Compatibility cannot be assessed against a licence that has not been decided.

**Needs an explicit decision**: which licence is correct. Then `LICENSE`, `pyproject.toml`, and
this file must be made to agree in one change, and the framework question re-opened. This is a
licensing decision, not a technical one.
