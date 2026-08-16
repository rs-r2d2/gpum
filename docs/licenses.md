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
