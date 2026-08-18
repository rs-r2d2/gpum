"""MkDocs build hooks (spec 007, contracts/publishing.md).

Registered in ``mkdocs.yml`` under ``hooks:``. Running the generator here rather than as a
documented manual step is deliberate: it means no build — and no ``mkdocs serve`` — can proceed
with a stale or missing download block, which is the one piece of the site that goes wrong
silently.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_release_snippet  # noqa: E402


def on_pre_build(config, **kwargs):  # noqa: ANN001, ARG001
    gen_release_snippet.generate()
