# E2E report

- Date: 2026-10-17 05:26 UTC
- Commit: 63a67ab (dirty)
- n8n image: docker.n8n.io/n8nio/n8n:2.18.7
- Command: `python -m pytest` (regenerates this file after a full run)
- Setup: real n8n container via docker compose; LLM, Telegram and leads sink replaced by one fake HTTP server

| # | Test | Failure mode covered | Result | Duration |
|---|------|----------------------|--------|----------|
| 1 | `test_missing_secret_is_rejected_and_llm_not_called` | Request without the shared secret reaches the LLM | PASSED | 0.07 s |
| 2 | `test_wrong_secret_is_rejected_and_llm_not_called` | Request with a wrong secret reaches the LLM | PASSED | 0.05 s |
| 3 | `test_invalid_input_is_rejected_before_calling_llm` | Empty message is sent to the LLM instead of a 400 | PASSED | 0.07 s |
| 4 | `test_faq_with_catalog_price_is_passed_through` | Valid catalog answer is blocked or altered | PASSED | 0.20 s |
| 5 | `test_price_missing_from_catalog_is_replaced_by_handoff_reply` | LLM invents a price ($ form) and it reaches the customer | PASSED | 0.22 s |
| 6 | `test_price_written_without_currency_sign_is_still_checked` | LLM invents a price written as '35000 pesos' | PASSED | 0.08 s |
| 7 | `test_non_price_numbers_do_not_trip_the_guard` | Guard false positive on days and opening hours | PASSED | 0.09 s |
| 8 | `test_non_json_llm_output_returns_fallback` | LLM answers with plain text instead of JSON | PASSED | 0.08 s |
| 9 | `test_schema_invalid_llm_output_returns_fallback` | LLM returns JSON with an intent outside the contract | PASSED | 0.09 s |
| 10 | `test_llm_hang_returns_fallback_within_five_seconds` | LLM never answers; ManyChat would time out | PASSED | 3.13 s |
| 11 | `test_llm_500_returns_fallback` | LLM provider returns HTTP 500 | PASSED | 0.09 s |
| 12 | `test_lead_intent_posts_exactly_one_lead_and_dedups_same_day` | Duplicate lead rows for one contact on the same day | PASSED | 3.39 s |
| 13 | `test_lead_for_a_different_contact_is_not_deduplicated` | Dedup swallows leads from other contacts | PASSED | 0.27 s |
| 14 | `test_human_intent_sends_one_telegram_message_and_hands_off` | Customer asks for a person and the owner is not notified (or notified twice) | PASSED | 1.68 s |
| 15 | `test_leads_sink_failure_does_not_break_customer_reply` | Leads sink is down and the customer gets an error | PASSED | 0.18 s |
| 16 | `test_telegram_failure_does_not_break_customer_reply` | Telegram is down and the customer gets an error | PASSED | 0.19 s |
| 17 | `test_sixth_message_in_a_minute_gets_rate_limit_reply_without_calling_llm` | Message flood from one contact burns LLM calls | PASSED | 0.59 s |
| 18 | `test_user_text_only_reaches_llm_in_a_user_message` | Customer text injected into the system prompt, or tools exposed to the LLM | PASSED | 0.09 s |

**Summary: 18/18 passed, 0 not passed, 10.5 s of test time (excluding container startup).**

## Not covered here

These can only be proven by the live eval or with real accounts:

- LLM behavior with a real model: the suite uses a fake LLM, so answer quality, prompt-injection resistance and off-catalog questions are only checked by `eval/live_eval.py` with a real Groq key (`reports/live-eval.md`).
- Apps Script deployment: the suite uses a fake leads endpoint. `apps-script/Code.gs`, the Google redirect flow and the sheet writes were not exercised against Google.
- ManyChat: no ManyChat account was involved. The steps and field names in `docs/manychat-setup.md` are unverified against the real product, including its plan limits and request timeout.
- Concurrency race on workflow static data: tests send requests one at a time per contact. Simultaneous executions for the same contact can lose rate-limit or dedup updates (the Apps Script upsert is the second line of defense for leads).
- Real Telegram delivery, Instagram delivery and the Instagram 24 h messaging window.
