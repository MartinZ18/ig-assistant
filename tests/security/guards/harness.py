"""Python side of run_nodes.js: execute the real n8n Code nodes without Docker."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / "n8n" / "workflows" / "assistant.json"
RUNNER = Path(__file__).resolve().parent / "run_nodes.js"

FALLBACK_REPLY = (
    "Gracias por escribirnos. En este momento no puedo responder tu consulta, "
    "pero una persona del equipo te va a contestar a la brevedad."
)


def run_steps(steps):
    spec = {"workflow": str(WORKFLOW), "steps": steps}
    out = subprocess.run(
        ["node", str(RUNNER)], input=json.dumps(spec), capture_output=True,
        text=True, encoding="utf-8", check=True, timeout=60,
    )
    return json.loads(out.stdout)


def gate_request(secret, body, *, env):
    return {"node": "Gate", "input": {"headers": {"x-assistant-secret": secret} if secret is not None else {},
                                       "body": body}, "env": env}


def llm_completion(reply, intent):
    content = json.dumps({"reply": reply, "intent": intent}, ensure_ascii=False)
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def guard(reply, intent="faq", message="consulta", env=None):
    """Build LLM Request + Parse & Guard for one fake LLM answer; returns Parse & Guard output."""
    customer = {"channel": "instagram", "contact_id": "c-1", "username": "ana", "message": message}
    res = run_steps([
        {"node": "Build LLM Request", "input": {"input": customer}, "env": env or {}},
        {"node": "Parse & Guard", "input": llm_completion(reply, intent), "env": env or {}},
    ])
    return res["results"][1]
