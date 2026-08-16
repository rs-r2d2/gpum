"""All tests in this directory require a real NVIDIA GPU.

The hook receives every collected item, not only this directory's, so it must filter by path.
"""

import pathlib

import pytest

_HERE = pathlib.Path(__file__).parent


def pytest_collection_modifyitems(items):
    for item in items:
        if _HERE in pathlib.Path(str(item.fspath)).parents:
            item.add_marker(pytest.mark.hardware)
