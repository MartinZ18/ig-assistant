"""Owner alert flooding and n8n surface exposure, against the real container. Needs Docker.

How the defenses could fail (written before the tests):
Alert flood (LLM10 / ASI08):
1. Every 'human' intent (or any induced fallback, e.g. asking for a non-catalog number) sends a
   Telegram message; there is no per-contact dedup like the lead claim, so one stranger produces
   up to RATE_LIMIT_PER_CONTACT alerts per minute, and N accounts N times that.
n8n exposure (A02 / A01):
2. The editor UI and REST API share port 5678 with the webhook, so the tunnel/proxy that ManyChat
   needs (docs/manychat-setup.md step 0) publishes the editor too unless a path rule limits it.
3. A fresh instance offers owner setup to whoever arrives first; with
   N8N_BLOCK_ENV_ACCESS_IN_NODE=false that owner reads every secret through $env.
"""

import pytest
import requests

from tests.conftest import N8N_URL, settle, wait_until


@pytest.mark.open_finding  # SEC-06, not fixed yet
def test_one_contact_triggers_at_most_one_owner_alert_per_window(assistant, fake, contact):
    fake.llm_returns_json("Te paso con una persona del equipo.", "human")
    for _ in range(5):
        assert assistant.call("quiero hablar con una persona", contact_id=contact).json()["handoff"] is True
    wait_until(lambda: len(fake.telegram_calls) >= 2, timeout=5)
    settle()
    assert len(fake.telegram_calls) <= 1, f"{len(fake.telegram_calls)} alerts for one contact in one minute"


@pytest.mark.open_finding  # SEC-05, not fixed yet
def test_webhook_listener_does_not_serve_the_editor_or_rest_api():
    ui = requests.get(f"{N8N_URL}/", timeout=10)
    settings = requests.get(f"{N8N_URL}/rest/settings", timeout=10)
    assert ui.status_code == 404 or "n8n" not in ui.text.lower(), "editor UI served on the webhook port"
    assert settings.status_code in (401, 403, 404), "REST API reachable on the webhook port"


@pytest.mark.open_finding  # SEC-05, not fixed yet
def test_fresh_instance_does_not_offer_owner_setup_to_first_visitor():
    settings = requests.get(f"{N8N_URL}/rest/settings", timeout=10)
    if settings.status_code != 200:
        return  # REST not reachable: nothing to claim
    um = settings.json().get("data", {}).get("userManagement", {})
    assert um.get("showSetupOnFirstLoad") is not True, "owner account is unclaimed on a reachable instance"
