"""Rate limits under concurrency, against the real n8n container (LLM10, A06). Needs Docker.

Uses the session stack from tests/conftest.py (RATE_LIMIT_PER_ACCOUNT=12, per contact 5).

How the defense could fail (written before the tests):
1. Workflow static data is read at the start of an execution and saved when it ends; with the LLM
   call (up to LLM_TIMEOUT_MS = 3 s) inside the execution, every request of a burst reads the same
   empty counter, so the per-contact limit (5) lets the whole burst reach the LLM.
2. The same lost-update race lets a burst of rotating contacts pass the account cap (12).
3. Last-write-wins on static data erases counters written by sibling executions, so the limit
   stays open after the burst too.
The fake LLM hangs, so each execution holds its stale read for the full 3 s timeout (the window a
slow real provider gives an attacker).
"""

import uuid
from concurrent.futures import ThreadPoolExecutor


BURST = 15
# The fix (N8N_CONCURRENCY_PRODUCTION_LIMIT=1) queues executions: with the LLM hanging, the last
# queued request waits about (calls that reach the LLM) x 3 s, beyond the default 20 s client
# timeout. The longer timeout is a harness setting; the security assertions are unchanged.
CLIENT_TIMEOUT = 120


def _fire(assistant, payloads):
    with ThreadPoolExecutor(max_workers=len(payloads)) as pool:
        return list(pool.map(lambda kw: assistant.call("hola", timeout=CLIENT_TIMEOUT, **kw), payloads))


def test_concurrent_burst_from_one_contact_reaches_llm_at_most_five_times(assistant, fake, contact):
    fake.llm_hangs()
    account = f"page-{uuid.uuid4().hex[:8]}"
    replies = _fire(assistant, [{"contact_id": contact, "account_id": account}] * BURST)
    assert all(r.status_code == 200 for r in replies)
    assert len(fake.llm_calls) <= 5, f"{len(fake.llm_calls)} of {BURST} burst messages reached the LLM"


def test_concurrent_burst_of_rotating_contacts_respects_account_cap(assistant, fake, contact):
    fake.llm_hangs()
    account = f"page-{uuid.uuid4().hex[:8]}"
    payloads = [{"contact_id": f"{contact}-{i}", "account_id": account} for i in range(BURST + 10)]
    replies = _fire(assistant, payloads)
    assert all(r.status_code == 200 for r in replies)
    assert len(fake.llm_calls) <= 12, f"{len(fake.llm_calls)} of {len(payloads)} reached the LLM (cap 12)"
