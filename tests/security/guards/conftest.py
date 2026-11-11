"""Deterministic security guards: no Docker. Override the session-wide n8n stack from tests/conftest.py."""

import shutil

import pytest


@pytest.fixture(scope="session", autouse=True)
def n8n():
    if shutil.which("node") is None:
        pytest.skip("node is required to run the Code-node harness")
    yield


@pytest.fixture(autouse=True)
def _reset_fake():
    yield
