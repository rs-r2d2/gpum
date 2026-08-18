"""T012 / A-12 support: the download block generator contract.

The single highest-stakes correctness requirement on the site (FR-010, SC-005): every release
this project has published is a *pre-release*, and the conventional "latest release" link skips
pre-releases and returns 404. Every case below is exercised against recorded API responses, so
the suite stays offline and hardware-free (constitution Principle IV).

Contract: ``specs/007-github-pages-site/contracts/publishing.md``.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tools import gen_release_snippet as gen

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "releases"


def load(name: str) -> list[dict]:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def test_prerelease_is_eligible():
    """The whole reason the generator exists: a pre-release must still be offered."""
    selection = gen.select(load("prerelease_with_asset"))
    assert selection is not None
    assert selection.tag == "v0.1.0-alpha.2"
    assert selection.is_prerelease is True


def test_newest_eligible_release_wins():
    selection = gen.select(load("prerelease_with_asset"))
    assert selection is not None
    assert "v0.1.0-alpha.2" in selection.asset_url
    assert "alpha.1" not in selection.asset_url


def test_drafts_are_never_selected():
    selection = gen.select(load("draft_newer_than_release"))
    assert selection is not None
    assert selection.tag == "v0.1.0-alpha.2", "a draft release must never be offered"


def test_asset_url_is_verbatim_never_constructed():
    """A URL the generator did not receive is a URL it must not print."""
    releases = load("prerelease_with_asset")
    expected = releases[0]["assets"][0]["browser_download_url"]
    selection = gen.select(releases)
    assert selection is not None
    assert selection.asset_url == expected
    assert selection.asset_name == releases[0]["assets"][0]["name"]


@pytest.mark.parametrize("fixture", ["no_bundle_asset", "no_releases"])
def test_no_eligible_release_selects_nothing(fixture):
    assert gen.select(load(fixture)) is None


def test_resolved_snippet_contains_the_three_steps():
    selection = gen.select(load("prerelease_with_asset"))
    text = gen.render(selection)
    assert selection.asset_url in text
    assert f"chmod +x {selection.asset_name}" in text
    assert f"./{selection.asset_name}" in text
    assert "0.1.0-alpha.2" in text


def test_fallback_states_the_truth_and_invents_no_url():
    """No release, no bundle, or no network: say so, link to the releases page, invent nothing."""
    text = gen.render(None)
    assert ".AppImage" not in text, "the fallback must not print a bundle download URL"
    assert "releases" in text.lower()
    assert "from source" in text.lower() or "pip install" in text
    assert gen.RELEASES_PAGE in text


def test_offline_env_var_takes_the_fallback_path(tmp_path, monkeypatch):
    """`GPUM_DOCS_OFFLINE=1` is how a contributor works offline and how CI's fallback is tested."""
    monkeypatch.setenv("GPUM_DOCS_OFFLINE", "1")
    monkeypatch.setattr(
        gen, "fetch_releases", lambda: pytest.fail("network must not be touched when offline")
    )
    out = tmp_path / "release.md"
    gen.generate(out)
    assert out.exists()
    assert ".AppImage" not in out.read_text()


def test_generate_writes_the_snippet_where_pages_include_it(tmp_path, monkeypatch):
    monkeypatch.delenv("GPUM_DOCS_OFFLINE", raising=False)
    monkeypatch.setattr(gen, "fetch_releases", lambda: load("prerelease_with_asset"))
    out = tmp_path / "nested" / "release.md"
    gen.generate(out)
    assert "GPUM-0.1.0-x86_64.AppImage" in out.read_text()


def test_unreachable_api_falls_back_rather_than_failing_the_build(tmp_path, monkeypatch):
    """A build that fails because GitHub is slow would be worse than a page saying 'not now'."""
    monkeypatch.delenv("GPUM_DOCS_OFFLINE", raising=False)

    def boom():
        raise OSError("connection refused")

    monkeypatch.setattr(gen, "fetch_releases", boom)
    out = tmp_path / "release.md"
    gen.generate(out)
    assert gen.RELEASES_PAGE in out.read_text()
