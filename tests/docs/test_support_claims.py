"""A-04, A-05: the site may not claim more than the project delivers.

Constitution Principle II makes ``docs/capability-matrix.md`` the auditable record of what works
where, and requires it to be updated in the same change that alters support. These tests are the
other half of that: a page cannot quietly claim support the matrix does not record.
"""

from __future__ import annotations

import re

import pytest

from tests.docs.conftest import DOCS, all_pages, read_source

PAGES = all_pages()
IDS = [p.rel for p in PAGES]

#: Positive-claim shapes. A match is only a violation if its own sentence is not a denial —
#: "runs on Windows" is a claim, "runs on Linux and makes no claim about Windows" is not. Both
#: halves are needed: the shape alone produces false positives on honest denials, and a
#: negation scan alone would pass any sentence that happened to contain the word "not".
FORBIDDEN = [
    (
        re.compile(
            r"\b(?:supports?|supported on|runs on|works on|available (?:on|for)|"
            r"compatible with)\b[^.\n]{0,40}\b(?:Windows|macOS|Mac OS X|OS X)\b",
            re.IGNORECASE,
        ),
        "claims Windows or macOS support (constitution Principle II: Linux only)",
    ),
    (
        re.compile(
            r"\b(?:AMD|Intel)\b[^.\n]{0,60}\b(?:coming soon|planned|will be supported|"
            r"support is coming|in progress|roadmap)\b",
            re.IGNORECASE,
        ),
        "promises vendor support the capability matrix does not record",
    ),
    (
        re.compile(
            r"\b(?:AMD|Intel)\b[^.\n]{0,30}\b(?:is|are) (?:fully |now )?"
            r"(?:supported|implemented)\b",
            re.IGNORECASE,
        ),
        "describes an unimplemented vendor as supported",
    ),
]

#: Words that turn a claim-shaped sentence into a denial of that claim.
DENIAL = re.compile(
    r"\b(?:no|not|never|neither|nor|without|unsupported|dropped|removed|instead of|"
    r"isn't|aren't|doesn't|don't|won't)\b",
    re.IGNORECASE,
)


def _sentence_around(text: str, match: re.Match[str]) -> str:
    start = max(text.rfind(".", 0, match.start()), text.rfind("\n", 0, match.start())) + 1
    end = min(
        (i for i in (text.find(".", match.end()), text.find("\n", match.end())) if i != -1),
        default=len(text),
    )
    return text[start:end]


def claims(text: str) -> list[str]:
    """Positive support claims in ``text``, ignoring sentences that deny them."""
    found = []
    for pattern, why in FORBIDDEN:
        for match in pattern.finditer(text):
            if DENIAL.search(_sentence_around(text, match)):
                continue
            found.append(f"{why} — {match.group(0)!r}")
    return found


def test_the_detector_catches_real_claims():
    """A guard on the guard: a detector loosened into uselessness would pass every page."""
    assert claims("GPUM supports Windows 11.")
    assert claims("It also runs on macOS.")
    assert claims("AMD support is coming soon.")
    assert claims("Intel is fully supported.")


def test_the_detector_permits_honest_denials():
    assert not claims("GPUM runs on Linux and makes no claim about Windows or macOS.")
    assert not claims("Windows and macOS are not supported and not planned.")
    assert not claims("AMD and Intel are registered but not implemented.")


@pytest.mark.parametrize("pg", PAGES, ids=IDS)
def test_no_page_claims_unsupported_platforms_or_vendors(pg):
    """A-04."""
    found = claims(pg.text)
    assert not found, f"{pg.rel}: " + "; ".join(found)


def test_capability_matrix_still_records_linux_only():
    """The site's source of truth must keep saying what the site relies on it saying."""
    matrix = (DOCS / "capability-matrix.md").read_text()
    assert "Linux only" in matrix or "Platform: Linux" in matrix


@pytest.mark.parametrize("pg", PAGES, ids=IDS)
def test_pages_mentioning_amd_or_intel_say_they_are_unimplemented(pg):
    """Registered-but-unimplemented is the honest description, and it must be the one used."""
    if not re.search(r"\b(AMD|Intel)\b", pg.text):
        pytest.skip("page does not discuss vendors")
    honest = re.search(
        r"not implemented|unimplemented|registered but|stub|no claim|say so plainly|"
        r"❌|not available",
        pg.text,
        re.IGNORECASE,
    )
    assert honest, f"{pg.rel}: mentions AMD or Intel without recording that they are unimplemented"


def test_download_page_python_version_matches_project_metadata():
    """A-05: the version a reader installs against comes from pyproject, not from memory."""
    requires = re.search(r'requires-python\s*=\s*"([^"]+)"', read_source("pyproject.toml"))
    assert requires, "pyproject.toml declares no requires-python"
    minimum = re.search(r"(\d+\.\d+)", requires.group(1)).group(1)
    download = (DOCS / "download.md").read_text()
    assert f"Python {minimum}" in download, (
        f"download page must state Python {minimum}, matching requires-python"
    )


def test_download_page_glibc_baseline_matches_the_build_container():
    """A-05: the bundle's floor is set by the container it is built in, and nothing else."""
    dockerfile = read_source("packaging/Dockerfile.build")
    ubuntu = re.search(r"FROM ubuntu:(\d+\.\d+)", dockerfile)
    glibc = re.search(r"glibc \((\d+\.\d+)\)", dockerfile)
    assert ubuntu and glibc, "build container no longer states its Ubuntu and glibc versions"
    download = (DOCS / "download.md").read_text()
    assert ubuntu.group(1) in download, "download page must state the oldest supported Ubuntu"
    assert glibc.group(1) in download, "download page must state the glibc baseline"
