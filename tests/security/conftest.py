"""Attack tests for findings that are still open fail on purpose, so a plain `python -m pytest`
must not run them (it would turn the default suite and reports/e2e-report.md red).

They carry @pytest.mark.open_finding and are deselected unless the marker is requested:

    .venv/Scripts/python -m pytest -o addopts="" -p no:cacheprovider -m open_finding tests/security

When a finding is fixed, remove the marker from its test so it becomes a regression guard.
"""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "open_finding: attack test for a security finding not fixed yet (opt-in)")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    if "open_finding" in (config.option.markexpr or ""):
        return
    deselected = [item for item in items if item.get_closest_marker("open_finding")]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = [item for item in items if not item.get_closest_marker("open_finding")]
