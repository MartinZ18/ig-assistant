# E2E report

- Date: 2026-11-11 17:43 UTC
- Commit: b7a0440 (dirty)
- n8n image: docker.n8n.io/n8nio/n8n:2.18.7
- Command: `python -m pytest` (regenerates this file after a full run)
- Setup: real n8n container via docker compose; LLM, Telegram and leads sink replaced by one fake HTTP server

| # | Test | Failure mode covered | Result | Duration |
|---|------|----------------------|--------|----------|
| 1 | `test_wrong_or_missing_secret_writes_nothing` | wrong or missing secret writes nothing | PASSED | 0.50 s |
| 2 | `test_message_and_username_formulas_are_neutralized_on_create_and_update` | message and username formulas are neutralized on create and update | PASSED | 0.18 s |
| 3 | `test_positive_control_fixed_account_is_capped` | positive control fixed account is capped | PASSED | 0.19 s |
| 4 | `test_llm_request_contains_no_secret_and_no_tools` | llm request contains no secret and no tools | PASSED | 0.14 s |
| 5 | `test_second_customer_prompt_never_contains_first_customer_message` | second customer prompt never contains first customer message | PASSED | 0.12 s |
| 6 | `test_huge_message_is_clipped_and_output_is_bounded` | huge message is clipped and output is bounded | PASSED | 0.12 s |
| 7 | `test_unset_server_secret_fails_closed` | unset server secret fails closed | PASSED | 0.22 s |
| 8 | `test_off_catalog_commercial_promise_never_reaches_the_customer[price-swap-between-products]` | off catalog commercial promise never reaches the customer[price-swap-between-products] | PASSED | 0.15 s |
| 9 | `test_off_catalog_commercial_promise_never_reaches_the_customer[shipping-cost-as-product-price]` | off catalog commercial promise never reaches the customer[shipping-cost-as-product-price] | PASSED | 0.11 s |
| 10 | `test_off_catalog_commercial_promise_never_reaches_the_customer[threshold-as-product-price]` | off catalog commercial promise never reaches the customer[threshold-as-product-price] | PASSED | 0.11 s |
| 11 | `test_off_catalog_commercial_promise_never_reaches_the_customer[price-in-words-with-multiplier]` | off catalog commercial promise never reaches the customer[price-in-words-with-multiplier] | PASSED | 0.14 s |
| 12 | `test_off_catalog_commercial_promise_never_reaches_the_customer[price-in-words]` | off catalog commercial promise never reaches the customer[price-in-words] | PASSED | 0.16 s |
| 13 | `test_off_catalog_commercial_promise_never_reaches_the_customer[foreign-currency]` | off catalog commercial promise never reaches the customer[foreign-currency] | PASSED | 0.16 s |
| 14 | `test_off_catalog_commercial_promise_never_reaches_the_customer[fullwidth-digits]` | off catalog commercial promise never reaches the customer[fullwidth-digits] | PASSED | 0.16 s |
| 15 | `test_off_catalog_commercial_promise_never_reaches_the_customer[invented-discount]` | off catalog commercial promise never reaches the customer[invented-discount] | PASSED | 0.13 s |
| 16 | `test_off_catalog_commercial_promise_never_reaches_the_customer[invented-installments]` | off catalog commercial promise never reaches the customer[invented-installments] | PASSED | 0.12 s |
| 17 | `test_positive_control_guard_passes_catalog_price_and_blocks_invented_one` | positive control guard passes catalog price and blocks invented one | PASSED | 0.26 s |
| 18 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[live-off-catalog]` | catalog faithful answer reaches the customer unchanged[live-off-catalog] | PASSED | 0.11 s |
| 19 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[live-injection-refusal]` | catalog faithful answer reaches the customer unchanged[live-injection-refusal] | PASSED | 0.15 s |
| 20 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[live-out-of-stock]` | catalog faithful answer reaches the customer unchanged[live-out-of-stock] | PASSED | 0.14 s |
| 21 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[live-shipping-zone]` | catalog faithful answer reaches the customer unchanged[live-shipping-zone] | PASSED | 0.15 s |
| 22 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[live-buying]` | catalog faithful answer reaches the customer unchanged[live-buying] | PASSED | 0.12 s |
| 23 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[live-english]` | catalog faithful answer reaches the customer unchanged[live-english] | PASSED | 0.12 s |
| 24 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[e2e-shirt]` | catalog faithful answer reaches the customer unchanged[e2e-shirt] | PASSED | 0.11 s |
| 25 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[e2e-days-hours]` | catalog faithful answer reaches the customer unchanged[e2e-days-hours] | PASSED | 0.10 s |
| 26 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[two-products-one-sentence]` | catalog faithful answer reaches the customer unchanged[two-products-one-sentence] | PASSED | 0.13 s |
| 27 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[short-alias-second-product]` | catalog faithful answer reaches the customer unchanged[short-alias-second-product] | PASSED | 0.12 s |
| 28 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[product-in-previous-sentence]` | catalog faithful answer reaches the customer unchanged[product-in-previous-sentence] | PASSED | 0.12 s |
| 29 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[product-then-shipping]` | catalog faithful answer reaches the customer unchanged[product-then-shipping] | PASSED | 0.12 s |
| 30 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[two-zones]` | catalog faithful answer reaches the customer unchanged[two-zones] | PASSED | 0.11 s |
| 31 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[threshold]` | catalog faithful answer reaches the customer unchanged[threshold] | PASSED | 0.12 s |
| 32 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[threshold-first]` | catalog faithful answer reaches the customer unchanged[threshold-first] | PASSED | 0.11 s |
| 33 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[installments-catalog]` | catalog faithful answer reaches the customer unchanged[installments-catalog] | PASSED | 0.11 s |
| 34 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[installments-spelled]` | catalog faithful answer reaches the customer unchanged[installments-spelled] | PASSED | 0.11 s |
| 35 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[price-range-category]` | catalog faithful answer reaches the customer unchanged[price-range-category] | PASSED | 0.11 s |
| 36 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[price-before-product]` | catalog faithful answer reaches the customer unchanged[price-before-product] | PASSED | 0.11 s |
| 37 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[no-product-in-reply]` | catalog faithful answer reaches the customer unchanged[no-product-in-reply] | PASSED | 0.11 s |
| 38 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[pesos-suffix]` | catalog faithful answer reaches the customer unchanged[pesos-suffix] | PASSED | 0.11 s |
| 39 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[mil-gracias]` | catalog faithful answer reaches the customer unchanged[mil-gracias] | PASSED | 0.12 s |
| 40 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[refusal-plus-price]` | catalog faithful answer reaches the customer unchanged[refusal-plus-price] | PASSED | 0.14 s |
| 41 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[returns-days]` | catalog faithful answer reaches the customer unchanged[returns-days] | PASSED | 0.14 s |
| 42 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[address-hours]` | catalog faithful answer reaches the customer unchanged[address-hours] | PASSED | 0.12 s |
| 43 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[shirt-with-sizes]` | catalog faithful answer reaches the customer unchanged[shirt-with-sizes] | PASSED | 0.14 s |
| 44 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[shipping-word-then-product-price]` | catalog faithful answer reaches the customer unchanged[shipping-word-then-product-price] | PASSED | 0.16 s |
| 45 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[generic-range-entre]` | catalog faithful answer reaches the customer unchanged[generic-range-entre] | PASSED | 0.18 s |
| 46 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[generic-list-commas]` | catalog faithful answer reaches the customer unchanged[generic-list-commas] | PASSED | 0.20 s |
| 47 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[product-price-shipping-included]` | catalog faithful answer reaches the customer unchanged[product-price-shipping-included] | PASSED | 0.18 s |
| 48 | `test_catalog_faithful_answer_reaches_the_customer_unchanged[short-answer-claro]` | catalog faithful answer reaches the customer unchanged[short-answer-claro] | PASSED | 0.14 s |
| 49 | `test_more_off_catalog_variants_never_reach_the_customer[price-before-wrong-product]` | more off catalog variants never reach the customer[price-before-wrong-product] | PASSED | 0.10 s |
| 50 | `test_more_off_catalog_variants_never_reach_the_customer[rounded-thousands]` | more off catalog variants never reach the customer[rounded-thousands] | PASSED | 0.13 s |
| 51 | `test_more_off_catalog_variants_never_reach_the_customer[k-suffix]` | more off catalog variants never reach the customer[k-suffix] | PASSED | 0.16 s |
| 52 | `test_more_off_catalog_variants_never_reach_the_customer[two-for-one]` | more off catalog variants never reach the customer[two-for-one] | PASSED | 0.14 s |
| 53 | `test_more_off_catalog_variants_never_reach_the_customer[dollars-after]` | more off catalog variants never reach the customer[dollars-after] | PASSED | 0.12 s |
| 54 | `test_more_off_catalog_variants_never_reach_the_customer[discount-amount-equal-price]` | more off catalog variants never reach the customer[discount-amount-equal-price] | PASSED | 0.11 s |
| 55 | `test_more_off_catalog_variants_never_reach_the_customer[fits-only-one-asked-product]` | more off catalog variants never reach the customer[fits-only-one-asked-product] | PASSED | 0.10 s |
| 56 | `test_more_off_catalog_variants_never_reach_the_customer[price-without-any-subject]` | more off catalog variants never reach the customer[price-without-any-subject] | PASSED | 0.10 s |
| 57 | `test_more_off_catalog_variants_never_reach_the_customer[arabic-indic-digits]` | more off catalog variants never reach the customer[arabic-indic-digits] | PASSED | 0.10 s |
| 58 | `test_more_off_catalog_variants_never_reach_the_customer[spelled-installments]` | more off catalog variants never reach the customer[spelled-installments] | PASSED | 0.10 s |
| 59 | `test_more_off_catalog_variants_never_reach_the_customer[six-payments]` | more off catalog variants never reach the customer[six-payments] | PASSED | 0.10 s |
| 60 | `test_more_off_catalog_variants_never_reach_the_customer[percent-off]` | more off catalog variants never reach the customer[percent-off] | PASSED | 0.10 s |
| 61 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-lead-correo]` | more off catalog variants never reach the customer[shipping-lead-correo] | PASSED | 0.10 s |
| 62 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-lead-rest-of-country]` | more off catalog variants never reach the customer[shipping-lead-rest-of-country] | PASSED | 0.12 s |
| 63 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-lead-con-envio]` | more off catalog variants never reach the customer[shipping-lead-con-envio] | PASSED | 0.11 s |
| 64 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-lead-moto]` | more off catalog variants never reach the customer[shipping-lead-moto] | PASSED | 0.12 s |
| 65 | `test_more_off_catalog_variants_never_reach_the_customer[category-alias-wrong-product]` | more off catalog variants never reach the customer[category-alias-wrong-product] | PASSED | 0.10 s |
| 66 | `test_more_off_catalog_variants_never_reach_the_customer[generic-alias-jogger-price]` | more off catalog variants never reach the customer[generic-alias-jogger-price] | PASSED | 0.11 s |
| 67 | `test_more_off_catalog_variants_never_reach_the_customer[generic-alias-musculosa-price]` | more off catalog variants never reach the customer[generic-alias-musculosa-price] | PASSED | 0.12 s |
| 68 | `test_more_off_catalog_variants_never_reach_the_customer[unknown-product-validated-by-message]` | more off catalog variants never reach the customer[unknown-product-validated-by-message] | PASSED | 0.14 s |
| 69 | `test_more_off_catalog_variants_never_reach_the_customer[unknown-noun-validated-by-message]` | more off catalog variants never reach the customer[unknown-noun-validated-by-message] | PASSED | 0.12 s |
| 70 | `test_more_off_catalog_variants_never_reach_the_customer[unknown-noun-after-filler]` | more off catalog variants never reach the customer[unknown-noun-after-filler] | PASSED | 0.13 s |
| 71 | `test_more_off_catalog_variants_never_reach_the_customer[generic-alias-repeated-price]` | more off catalog variants never reach the customer[generic-alias-repeated-price] | PASSED | 0.16 s |
| 72 | `test_more_off_catalog_variants_never_reach_the_customer[generic-alias-with-threshold]` | more off catalog variants never reach the customer[generic-alias-with-threshold] | PASSED | 0.13 s |
| 73 | `test_more_off_catalog_variants_never_reach_the_customer[generic-alias-other-product-price]` | more off catalog variants never reach the customer[generic-alias-other-product-price] | PASSED | 0.13 s |
| 74 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-included-after-price]` | more off catalog variants never reach the customer[shipping-included-after-price] | PASSED | 0.12 s |
| 75 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-lead-con-el-envio]` | more off catalog variants never reach the customer[shipping-lead-con-el-envio] | PASSED | 0.11 s |
| 76 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-lead-incluido]` | more off catalog variants never reach the customer[shipping-lead-incluido] | PASSED | 0.11 s |
| 77 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-lead-para-la]` | more off catalog variants never reach the customer[shipping-lead-para-la] | PASSED | 0.15 s |
| 78 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-lead-then-price-clause]` | more off catalog variants never reach the customer[shipping-lead-then-price-clause] | PASSED | 0.16 s |
| 79 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-lead-colon]` | more off catalog variants never reach the customer[shipping-lead-colon] | PASSED | 0.17 s |
| 80 | `test_more_off_catalog_variants_never_reach_the_customer[shipping-subject-wrong-zone]` | more off catalog variants never reach the customer[shipping-subject-wrong-zone] | PASSED | 0.16 s |
| 81 | `test_concurrent_burst_from_one_contact_reaches_llm_at_most_five_times` | concurrent burst from one contact reaches llm at most five times | PASSED | 16.35 s |
| 82 | `test_concurrent_burst_of_rotating_contacts_respects_account_cap` | concurrent burst of rotating contacts respects account cap | PASSED | 46.22 s |
| 83 | `test_same_secret_accepts_only_exact_matches` | same secret accepts only exact matches | PASSED | 0.10 s |
| 84 | `test_missing_secret_is_rejected_and_llm_not_called` | Request without the shared secret reaches the LLM | PASSED | 0.05 s |
| 85 | `test_wrong_secret_is_rejected_and_llm_not_called` | Request with a wrong secret reaches the LLM | PASSED | 0.06 s |
| 86 | `test_invalid_input_is_rejected_before_calling_llm` | Empty message is sent to the LLM instead of a 400 | PASSED | 0.05 s |
| 87 | `test_faq_with_catalog_price_is_passed_through` | Valid catalog answer is blocked or altered | PASSED | 0.11 s |
| 88 | `test_price_missing_from_catalog_is_replaced_by_handoff_reply` | LLM invents a price ($ form) and it reaches the customer | PASSED | 0.18 s |
| 89 | `test_price_written_without_currency_sign_is_still_checked` | LLM invents a price written as '35000 pesos' | PASSED | 0.09 s |
| 90 | `test_non_price_numbers_do_not_trip_the_guard` | Guard false positive on days and opening hours | PASSED | 0.15 s |
| 91 | `test_non_json_llm_output_returns_fallback` | LLM answers with plain text instead of JSON | PASSED | 0.09 s |
| 92 | `test_schema_invalid_llm_output_returns_fallback` | LLM returns JSON with an intent outside the contract | PASSED | 0.11 s |
| 93 | `test_llm_hang_returns_fallback_within_five_seconds` | LLM never answers; ManyChat would time out | PASSED | 3.10 s |
| 94 | `test_llm_500_returns_fallback` | LLM provider returns HTTP 500 | PASSED | 0.09 s |
| 95 | `test_lead_intent_posts_exactly_one_lead_and_dedups_same_day` | Duplicate lead rows for one contact on the same day | PASSED | 3.28 s |
| 96 | `test_lead_for_a_different_contact_is_not_deduplicated` | Dedup swallows leads from other contacts | PASSED | 0.29 s |
| 97 | `test_human_intent_sends_one_telegram_message_and_hands_off` | Customer asks for a person and the owner is not notified (or notified twice) | PASSED | 1.68 s |
| 98 | `test_leads_sink_failure_does_not_break_customer_reply` | Leads sink is down and the customer gets an error | PASSED | 0.22 s |
| 99 | `test_telegram_failure_does_not_break_customer_reply` | Telegram is down and the customer gets an error | PASSED | 0.24 s |
| 100 | `test_sixth_message_in_a_minute_gets_rate_limit_reply_without_calling_llm` | Message flood from one contact burns LLM calls | PASSED | 0.58 s |
| 101 | `test_rotating_contact_ids_hit_the_account_cap_but_other_accounts_are_unaffected` | rotating contact ids hit the account cap but other accounts are unaffected | PASSED | 1.76 s |
| 102 | `test_rejected_messages_do_not_consume_account_budget` | rejected messages do not consume account budget | PASSED | 1.61 s |
| 103 | `test_user_text_only_reaches_llm_in_a_user_message` | Customer text injected into the system prompt, or tools exposed to the LLM | PASSED | 0.09 s |

**Summary: 103/103 passed, 0 not passed, 87.4 s of test time (excluding container startup).**

## Not covered here

These can only be proven by the live eval or with real accounts:

- LLM behavior with a real model: the suite uses a fake LLM, so answer quality, prompt-injection resistance and off-catalog questions are only checked by `eval/live_eval.py` with a real Groq key (`reports/live-eval.md`).
- Apps Script deployment: the suite uses a fake leads endpoint. `apps-script/Code.gs`, the Google redirect flow and the sheet writes were not exercised against Google.
- ManyChat: no ManyChat account was involved. The steps and field names in `docs/manychat-setup.md` are unverified against the real product, including its plan limits and request timeout.
- Concurrency: this suite sends requests one at a time. Bursts are covered by `tests/security/test_e2e_rate_limit_race.py`; the limits hold because n8n runs one production execution at a time (`N8N_CONCURRENCY_PRODUCTION_LIMIT=1`).
- Real Telegram delivery, Instagram delivery and the Instagram 24 h messaging window.
