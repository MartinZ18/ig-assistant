# ig-assistant

Backend for an Instagram DM assistant for a fictional clothing store ("Tienda Demo Ropa").
ManyChat owns the Instagram channel and calls an n8n webhook; n8n asks an LLM (answering only from
the store catalog), applies deterministic guards and returns `{reply, intent, handoff}`.

## Run

    cp .env.example .env     # fill in values
    docker compose up        # n8n on http://localhost:5678, workflow imported and activated at startup

Webhook: `POST http://localhost:5678/webhook/assistant` with header `X-Assistant-Secret`.

## Docs

- [docs/manychat-setup.md](docs/manychat-setup.md): connect Instagram, comment automation, External Request, manual curl tests.
- [apps-script/README.md](apps-script/README.md): leads sheet web app (deploy, secret, redirect note).
- `eval/live_eval.py`: live cases against the real LLM (needs your own `GROQ_API_KEY`); writes `reports/live-eval.md`.

Full documentation (architecture, tests) is added in a later task.
