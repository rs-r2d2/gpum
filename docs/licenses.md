# Third-party licences

Constitution tech constraints require dependencies to be licence-compatible with the project's
distribution licence, and copyleft-incompatible additions to be rejected in review.

**Project licence**: **MIT**, as declared in `LICENSE`. Decided 2026-08-17; see the resolution
note at the bottom of this file for what was contradictory before and what MIT obliges.

## Runtime dependencies

| Package | Licence | Compatible | Notes |
|---|---|---|---|
| PySide6 | LGPL-3.0 / commercial | ✅ | Compatible, but it carries obligations — see below. The reason PySide6 was chosen over PyQt6, which is GPL-3.0 / commercial and *would* have forced the whole application to GPL. Dynamic linking only — no PySide6 source is vendored. |
| psutil | BSD-3-Clause | ✅ | Permissive. |
| nvidia-ml-py (`[nvidia]` extra) | BSD-3-Clause | ✅ | Optional at install time. Pure Python over ctypes; the NVIDIA *driver* it talks to is proprietary but is not distributed with this project. |

## Development dependencies

pytest (MIT), pytest-qt (MIT), pytest-cov (MIT), ruff (MIT), mypy (MIT) — all permissive, and
none are distributed with the application.

## Review rule

Adding a GPL-licensed runtime dependency would require relicensing the project and **must** be
rejected unless that relicensing is an explicit, separate decision.

## ✅ Resolved: the project is MIT

The repository used to declare two different licences for itself. Recorded here because the
contradiction shipped, and because the resolution changes what the PySide6 note above means.

| Source | Declared before | Now |
|---|---|---|
| `LICENSE` | **MIT** — "Copyright (c) 2026 Rishabh Sethi", the full 21-line MIT text | unchanged, MIT |
| `pyproject.toml` | LGPL-3.0-or-later | **MIT** |
| `docs/licenses.md` (this file) | LGPL-3.0-or-later, "chosen to match PySide6" | **MIT** |

**Decision (2026-08-17): MIT.** `LICENSE` is the file that actually governs redistribution, and
the two that disagreed with it were changed to match rather than the other way round.

**What this changes about the PySide6 reasoning.** The old note said LGPL was "chosen to match
PySide6". That conflated two things. LGPL-3.0 does not require the *application* to be LGPL — it
requires that the LGPL library remain replaceable and that its licence travel with it. So MIT
application code linking LGPL PySide6 is fine. What was genuinely load-bearing in that decision
is narrower, and still true: **PyQt6 is GPL-3.0 / commercial, and GPL would have forced this
project's own code to GPL.** Avoiding PyQt6 is what kept MIT available as an option at all.

**What MIT obliges, given the bundle.** The AppImage ships Qt as separate `.so` files loaded at
runtime, not statically linked, so the replaceability condition is satisfied structurally. Two
obligations are *not* satisfied by structure and must be met explicitly:

- The LGPL-3.0 licence text and PySide6/Qt attribution must be distributed with the AppImage.
- The MIT text in `LICENSE` covers GPUM's own code only. It must not be presented as covering
  the whole bundle, because it does not — a recipient reading `LICENSE` alone would conclude
  they may relicense bundled LGPL code, which is exactly the confusion this section existed to
  flag.

**Open gap**: the published AppImage does not currently ship those licence texts.
`packaging/build-appimage.sh` collects no licence files. This is a real compliance gap, it is
narrower than the contradiction it replaces, and it is not fixed by this change.
