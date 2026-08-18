# Quality gates

Every change must pass all of these before it can be merged. They run in CI on Linux across every
supported Python version.

| Gate | Command | What it verifies |
|---|---|---|
| Lint | `ruff check src tests` | Style and a set of correctness lints |
| Type check | `mypy` | Strict typing across `core`, and the two interface modules |
| Tests | `pytest` | The full default suite, on a machine with no GPU |
| Bundle | `pytest -m packaging` | The built AppImage behaves like the package |
| Documentation | `mkdocs build --strict` | The site builds with no warnings |

`pytest -m hardware` and `pytest -m network` cover what the others cannot: real hardware, and
reachability of external links and the download URL.

## Failures that mean more than they look like

### `tests/unit/test_import_boundaries.py`

**This is a constitution violation, not a style nit.** It means the vendor or platform
abstraction has been breached — `core` importing `ui`, a backend importing `core`, a vendor
library escaping its single module, or an OS conditional in feature code.

Fix the import. **Never relax the test.** If you genuinely believe the boundary is wrong, that is
an amendment to the constitution, proposed separately — not a line deleted from a test file.

### A documentation drift check

A page now disagrees with the code. Usually you renamed a flag, added a scenario, or changed a
default, and the page still describes the old one. Update the page in the same change; that is
the point of the check firing now rather than a reader finding it later.

### A contract test, for a backend you did not touch

The shared contract suite is parametrized over every registered backend. A change to the backend
interface must update every backend and the contract tests in the same change — interface drift
across backends must not be merged.

## What must be updated alongside what

| If your change… | It must also update |
|---|---|
| Alters vendor or platform support | [`docs/capability-matrix.md`](../capability-matrix.md), in the same change |
| Alters the backend interface | Every backend, plus the shared contract tests |
| Alters a flag, default, setting, or scenario | The affected documentation page |
| Alters the sampling loop, threading, or UI update path | Evidence that the GUI thread stays non-blocking under load |
| Adds a dependency | [`docs/licenses.md`](../licenses.md), with the licence checked for compatibility |

## In the pull request

State which principles the change touches, and justify any deviation. An unjustified deviation
blocks the merge; principles marked NON-NEGOTIABLE cannot be waived in review at all — a change
that cannot satisfy them needs an amendment first.

Complexity is justified against the simpler alternative that was rejected. Speculative
abstraction for an anticipated vendor or feature is prohibited until a second concrete case
exists.
