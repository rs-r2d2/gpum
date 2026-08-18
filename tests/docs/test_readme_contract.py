"""A-10, A-11: one source of truth, and no version typed by hand.

The README and the site describe the same product. Two editable copies of the same instruction
diverge — not usually by contradicting each other outright, but by one being updated and the
other not. So the README keeps the front door and delegates the depth, and the commands that do
appear in both are checked for agreement.
"""

from __future__ import annotations

import re

import pytest

from tests.docs.conftest import DOCS, all_pages, read_source

SITE_URL = "https://rs-r2d2.github.io/gpum"

#: A pinned release inside authored prose is drift waiting to happen: it is correct exactly until
#: the next release, and nothing tells you when that was.
PINNED_VERSION = re.compile(r"GPUM-\d[\d.]*-x86_64\.AppImage|releases/download/")


def readme() -> str:
    return read_source("README.md")


def _command_lines(markdown: str) -> list[str]:
    """Every command inside a bash fence."""
    blocks = re.findall(r"```bash\n(.*?)```", markdown, re.DOTALL)
    lines = []
    for block in blocks:
        for line in block.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    return lines


def test_readme_points_at_the_site():
    assert SITE_URL in readme(), "the README must link to the documentation site"


@pytest.mark.parametrize("command", _command_lines(readme()))
def test_readme_commands_agree_with_the_download_page(command):
    """A-10: a command in both places must be the same command in both places."""
    docs_text = "\n".join(pg.text for pg in all_pages())
    assert command in docs_text, (
        f"README shows {command!r}, which appears nowhere in the documentation — "
        "one of the two is out of date"
    )


def test_readme_does_not_duplicate_the_long_form_sections():
    """The material that moved must not creep back; that is how duplication returns."""
    text = readme()
    # Markers chosen to identify the *catalogue* that moved, not a passing mention of it. The
    # README may still say that skipping `chmod +x` gives "Permission denied" — that is the
    # warning attached to a step, not a second copy of the troubleshooting page.
    moved = {
        "the full settings list": "Keep history for",
        "the troubleshooting catalogue": "nvidia-smi",
        "the archive-viewer symptom entry": "archive viewer",
        "the full option list": "--list-scenarios",
    }
    for what, marker in moved.items():
        assert marker not in text, (
            f"{what} moved to the site; the README carries it again ({marker!r}), so the two "
            "copies can now disagree"
        )


def test_readme_pins_no_release_version():
    """A-11: the download version is generated, so no hand-typed copy may exist."""
    found = PINNED_VERSION.search(readme())
    assert found is None, (
        f"README pins a release ({found.group(0)!r}); link to the download page instead, "
        "which is generated from the release list"
    )


@pytest.mark.parametrize("pg", all_pages(), ids=[p.rel for p in all_pages()])
def test_no_authored_page_pins_a_release_version(pg):
    """A-11: exactly one place in the repository holds a release version, and it is generated."""
    found = PINNED_VERSION.search(pg.text)
    assert found is None, (
        f"{pg.rel} pins a release ({found.group(0)!r}); embed the generated snippet instead"
    )


def test_the_generated_snippet_is_not_committed():
    """It is build output: committing it would recreate the hand-maintained version it replaces."""
    gitignore = read_source(".gitignore")
    assert "docs/_snippets/" in gitignore


def test_download_page_embeds_the_generated_snippet():
    assert '--8<-- "_snippets/release.md"' in (DOCS / "download.md").read_text()
