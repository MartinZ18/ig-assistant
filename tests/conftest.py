"""E2E harness: the real n8n container, with LLM/Telegram/leads replaced by one fake server."""

import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest
import requests

from tests.fake_services import (
    LEADS_SECRET,
    TELEGRAM_CHAT_ID,
    TELEGRAM_TOKEN,
    FakeServices,
)

ROOT = Path(__file__).resolve().parent.parent
N8N_URL = "http://localhost:5678"
ASSISTANT_SECRET = "assistant-test-secret"
PROJECT = "ig-assistant-e2e"


def _compose(*args: str, env=None, check=True):
    return subprocess.run(
        ["docker", "compose", "-p", PROJECT, *args],
        cwd=ROOT, env=env, check=check, capture_output=True, text=True, timeout=300,
    )


@pytest.fixture(scope="session")
def fake():
    server = FakeServices().start()
    yield server
    server.stop()


@pytest.fixture(scope="session", autouse=True)
def n8n(fake):
    """Bring the compose stack up against the fake and wait until the webhook is live."""
    base = f"http://host.docker.internal:{fake.port}"
    env = {
        **os.environ,
        "ASSISTANT_SECRET": ASSISTANT_SECRET,
        "GROQ_API_KEY": "gsk_dummy",
        "LLM_BASE_URL": f"{base}/openai/v1",
        "LLM_MODEL": "test-model",
        "LLM_TIMEOUT_MS": "3000",
        "TELEGRAM_BOT_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
        "TELEGRAM_API_BASE": base,
        "LEADS_URL": f"{base}/leads",
        "LEADS_SECRET": LEADS_SECRET,
    }
    _compose("down", "-v", "--remove-orphans", env=env, check=False)
    _compose("up", "-d", env=env)
    try:
        deadline = time.monotonic() + 120
        while True:
            try:
                # Unauthenticated probe: 401 means the workflow is registered and answering.
                probe = requests.post(f"{N8N_URL}/webhook/assistant", json={}, timeout=5)
                if probe.status_code == 401:
                    break
            except requests.RequestException:
                pass
            if time.monotonic() > deadline:
                logs = _compose("logs", "--tail", "60", env=env, check=False).stdout
                raise RuntimeError(f"assistant webhook never became live\n{logs}")
            time.sleep(1)
        yield
    finally:
        _compose("down", "-v", "--remove-orphans", env=env, check=False)


@pytest.fixture(autouse=True)
def _reset_fake(fake, n8n):
    fake.reset()
    yield


class Assistant:
    """What ManyChat does: POST the contract with the shared secret."""

    def call(self, message="hola", *, contact_id=None, secret=ASSISTANT_SECRET, username="ana", **extra):
        headers = {"X-Assistant-Secret": secret} if secret is not None else {}
        payload = {
            "channel": "instagram",
            "contact_id": contact_id or f"c-{uuid.uuid4().hex[:10]}",
            "username": username,
            "message": message,
            **extra,
        }
        return requests.post(f"{N8N_URL}/webhook/assistant", json=payload, headers=headers, timeout=20)


@pytest.fixture
def assistant() -> Assistant:
    return Assistant()


@pytest.fixture
def contact() -> str:
    """A contact id unique to the test, so workflow static data never leaks between tests."""
    return f"c-{uuid.uuid4().hex[:10]}"


def wait_until(condition, timeout=10.0):
    """Side effects run after the webhook reply, so tests poll for them."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.1)
    return False


def settle(seconds=1.5):
    """Give a side effect that must NOT happen enough time to show up."""
    time.sleep(seconds)
