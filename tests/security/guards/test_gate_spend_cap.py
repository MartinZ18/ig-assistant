"""Denial of wallet through the account-wide cap (LLM10, A06).

README: the per-account cap "bounds total LLM spend even if contact_id is rotated". The cap is
keyed by `account_id`, a field taken from the request BODY. Whoever can call the webhook (ManyChat,
or anyone holding a leaked ASSISTANT_SECRET) chooses that key.

How the defense could fail (written before the tests):
1. account_id is caller-controlled, so rotating it together with contact_id gives every request
   a fresh budget: total LLM calls are unbounded.
2. Each fresh key adds an entry to workflow static data (persisted on every execution), so the
   state grows with the attack inside each window.
3. The cap works only when the key is fixed (positive control below proves the harness sees it).
"""

import pytest
from tests.security.guards.harness import gate_request, run_steps

ENV = {"ASSISTANT_SECRET": "s3cret", "RATE_LIMIT_PER_CONTACT": "5",
       "RATE_LIMIT_PER_ACCOUNT": "12", "RATE_LIMIT_WINDOW_SECONDS": "60"}
CAP = 12
ATTEMPTS = 40


def _burst(account_for):
    steps = [
        gate_request("s3cret", {"channel": "instagram", "contact_id": f"bot-{i}", "username": "x",
                                "message": "hola", "account_id": account_for(i)}, env=ENV)
        for i in range(ATTEMPTS)
    ]
    out = run_steps(steps)
    passed = sum(1 for r in out["results"] if r["gate"] == "ok")
    return passed, out["staticData"]["global"]


def test_positive_control_fixed_account_is_capped():
    passed, state = _burst(lambda i: "page-1")
    assert passed == CAP
    assert list(state["accountRate"]) == ["page-1"]


@pytest.mark.open_finding  # SEC-04, not fixed yet
def test_rotating_account_id_does_not_lift_the_global_spend_cap():
    passed, state = _burst(lambda i: f"page-{i}")
    # Safe state: the LLM is reached at most CAP times per window, whatever the caller sends.
    assert passed <= CAP, f"{passed} of {ATTEMPTS} requests reached the LLM (cap {CAP})"
    assert len(state["accountRate"]) <= 1
