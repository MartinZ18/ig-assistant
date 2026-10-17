"""Pytest plugin: writes reports/e2e-report.md after a full run.

Loaded through pytest.ini (`-p tests.report_plugin`), so `python -m pytest` is the only command needed.
Runs that select a subset (-k, -m, explicit node ids) or that did not execute every collected test
leave the committed report untouched.
"""

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "e2e-report.md"

# Failure mode each scenario covers, keyed by test function name.
FAILURE_MODES = {
    "test_missing_secret_is_rejected_and_llm_not_called": "Request without the shared secret reaches the LLM",
    "test_wrong_secret_is_rejected_and_llm_not_called": "Request with a wrong secret reaches the LLM",
    "test_invalid_input_is_rejected_before_calling_llm": "Empty message is sent to the LLM instead of a 400",
    "test_faq_with_catalog_price_is_passed_through": "Valid catalog answer is blocked or altered",
    "test_price_missing_from_catalog_is_replaced_by_handoff_reply": "LLM invents a price ($ form) and it reaches the customer",
    "test_price_written_without_currency_sign_is_still_checked": "LLM invents a price written as '35000 pesos'",
    "test_non_price_numbers_do_not_trip_the_guard": "Guard false positive on days and opening hours",
    "test_non_json_llm_output_returns_fallback": "LLM answers with plain text instead of JSON",
    "test_schema_invalid_llm_output_returns_fallback": "LLM returns JSON with an intent outside the contract",
    "test_llm_hang_returns_fallback_within_five_seconds": "LLM never answers; ManyChat would time out",
    "test_llm_500_returns_fallback": "LLM provider returns HTTP 500",
    "test_lead_intent_posts_exactly_one_lead_and_dedups_same_day": "Duplicate lead rows for one contact on the same day",
    "test_lead_for_a_different_contact_is_not_deduplicated": "Dedup swallows leads from other contacts",
    "test_human_intent_sends_one_telegram_message_and_hands_off": "Customer asks for a person and the owner is not notified (or notified twice)",
    "test_leads_sink_failure_does_not_break_customer_reply": "Leads sink is down and the customer gets an error",
    "test_telegram_failure_does_not_break_customer_reply": "Telegram is down and the customer gets an error",
    "test_sixth_message_in_a_minute_gets_rate_limit_reply_without_calling_llm": "Message flood from one contact burns LLM calls",
    "test_user_text_only_reaches_llm_in_a_user_message": "Customer text injected into the system prompt, or tools exposed to the LLM",
}

NOT_COVERED = [
    "LLM behavior with a real model: the suite uses a fake LLM, so answer quality, prompt-injection resistance and off-catalog questions are only checked by `eval/live_eval.py` with a real Groq key (`reports/live-eval.md`).",
    "Apps Script deployment: the suite uses a fake leads endpoint. `apps-script/Code.gs`, the Google redirect flow and the sheet writes were not exercised against Google.",
    "ManyChat: no ManyChat account was involved. The steps and field names in `docs/manychat-setup.md` are unverified against the real product, including its plan limits and request timeout.",
    "Concurrency race on workflow static data: tests send requests one at a time per contact. Simultaneous executions for the same contact can lose rate-limit or dedup updates (the Apps Script upsert is the second line of defense for leads).",
    "Real Telegram delivery, Instagram delivery and the Instagram 24 h messaging window.",
]

_results = {}


def pytest_collection_modifyitems(config, items):
    config._e2e_collected = len(items)


def pytest_runtest_logreport(report):
    name = report.nodeid.split("::")[-1]
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        _results[report.nodeid] = (name, report.outcome, report.duration)


def _git(*args):
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def _commit():
    short = _git("rev-parse", "--short", "HEAD") or "unknown"
    # Ignore reports/: regenerating the report must not make the tree look dirty.
    dirty = _git("status", "--porcelain", "--", ".", ":(exclude)reports")
    return f"{short} (dirty)" if dirty else short


def _n8n_image():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    match = re.search(r"image:\s*(\S*n8n\S*)", compose)
    return match.group(1) if match else "unknown"


def _cell(text):
    return text.replace("|", r"\|")


def pytest_sessionfinish(session, exitstatus):
    collected = getattr(session.config, "_e2e_collected", 0)
    if not collected or len(_results) != collected or session.config.option.keyword or session.config.option.markexpr:
        return
    rows = list(_results.values())
    passed = sum(1 for _, o, _ in rows if o == "passed")
    total_time = sum(d for _, _, d in rows)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# E2E report",
        "",
        f"- Date: {now}",
        f"- Commit: {_commit()}",
        f"- n8n image: {_n8n_image()}",
        "- Command: `python -m pytest` (regenerates this file after a full run)",
        "- Setup: real n8n container via docker compose; LLM, Telegram and leads sink replaced by one fake HTTP server",
        "",
        "| # | Test | Failure mode covered | Result | Duration |",
        "|---|------|----------------------|--------|----------|",
    ]
    for i, (name, outcome, duration) in enumerate(rows, 1):
        mode = FAILURE_MODES.get(name, name.removeprefix("test_").replace("_", " "))
        lines.append(f"| {i} | `{name}` | {_cell(mode)} | {outcome.upper()} | {duration:.2f} s |")
    lines += [
        "",
        f"**Summary: {passed}/{len(rows)} passed, {len(rows) - passed} not passed, {total_time:.1f} s of test time (excluding container startup).**",
        "",
        "## Not covered here",
        "",
        "These can only be proven by the live eval or with real accounts:",
        "",
        *[f"- {item}" for item in NOT_COVERED],
        "",
    ]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
