"""A-02: the demonstration scenarios on the page are the ones the application actually has."""

from __future__ import annotations

import pytest

from gpum.backends.fake.scenarios import SCENARIOS
from tests.docs.conftest import DOCS

DEMO_PAGE = DOCS / "usage" / "demo-mode.md"


@pytest.mark.parametrize("name", sorted(SCENARIOS), ids=sorted(SCENARIOS))
def test_scenario_is_documented(name):
    page = DEMO_PAGE.read_text()
    assert name in page, f"scenario {name!r} exists but is not documented"


@pytest.mark.parametrize("name", sorted(SCENARIOS), ids=sorted(SCENARIOS))
def test_scenario_description_matches_the_application(name):
    """The page must not drift from what ``gpum --list-scenarios`` prints."""
    description = SCENARIOS[name].description
    if not description:
        pytest.skip("scenario carries no description")
    assert description in DEMO_PAGE.read_text(), (
        f"scenario {name!r} is described differently on the page than by --list-scenarios: "
        f"{description!r}"
    )


def test_the_page_claims_the_right_number_of_scenarios():
    words = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
             9: "nine", 10: "ten"}
    page = DEMO_PAGE.read_text().lower()
    count = len(SCENARIOS)
    assert str(count) in page or words.get(count, "") in page, (
        f"there are {count} scenarios; the page states a different number"
    )
