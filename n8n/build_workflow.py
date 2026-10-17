"""Generate n8n/workflows/assistant.json from n8n/code/*.js and catalog/catalog.json.

The catalog is baked into the "Build LLM Request" Code node so the workflow has no file
dependency at runtime. Re-run this script after editing a Code node or the catalog:

    python n8n/build_workflow.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "n8n" / "code"
WORKFLOW_ID = "igAssistant0001"  # fixed so the startup import overwrites instead of duplicating


def js(name: str) -> str:
    source = (CODE / name).read_text(encoding="utf-8")
    if "__CATALOG__" in source:
        catalog = json.loads((ROOT / "catalog" / "catalog.json").read_text(encoding="utf-8"))
        source = source.replace("__CATALOG__", json.dumps(catalog, ensure_ascii=False))
    return source


def code_node(name, file, position):
    return {
        "id": f"ig-{file.removesuffix('.js').replace('_', '-')}",
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": position,
        "parameters": {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": js(file)},
    }


def http_node(node_id, name, url, body, position, *, headers=None, timeout):
    parameters = {
        "method": "POST",
        "url": url,
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": body,
        "options": {"timeout": timeout},
    }
    if headers:
        parameters["sendHeaders"] = True
        parameters["headerParameters"] = {"parameters": headers}
    return {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": position,
        "parameters": parameters,
        # A failed call continues down the regular output carrying an `error` field.
        "onError": "continueRegularOutput",
    }


def condition(left, right):
    return {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
            "conditions": [
                {
                    "id": f"c-{right}",
                    "leftValue": left,
                    "rightValue": right,
                    "operator": {"type": "string", "operation": "equals"},
                }
            ],
            "combinator": "and",
        }
    }


def link(*targets):
    return {"main": [[{"node": t, "type": "main", "index": 0} for t in output] for output in targets]}


def build() -> dict:
    nodes = [
        {
            "id": "ig-webhook",
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2.1,
            "position": [0, 0],
            "webhookId": "ig-assistant-webhook",
            "parameters": {
                "httpMethod": "POST",
                "path": "assistant",
                "responseMode": "responseNode",
                "options": {},
            },
        },
        code_node("Gate", "gate.js", [240, 0]),
        {
            "id": "ig-gate-ok",
            "name": "Gate OK?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [480, 0],
            "parameters": {
                "conditions": condition("={{ $json.gate }}", "ok")["conditions"],
                "options": {},
            },
        },
        {
            "id": "ig-respond-reject",
            "name": "Respond Reject",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.4,
            "position": [720, 160],
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ $json.body }}",
                "options": {"responseCode": "={{ $json.status }}"},
            },
        },
        code_node("Build LLM Request", "build_request.js", [720, -80]),
        http_node(
            "ig-llm",
            "Call LLM",
            "={{ $env.LLM_BASE_URL }}/chat/completions",
            "={{ $json.llmBody }}",
            [960, -80],
            headers=[{"name": "Authorization", "value": "={{ 'Bearer ' + $env.GROQ_API_KEY }}"}],
            timeout="={{ Number($env.LLM_TIMEOUT_MS || 3000) }}",
        ),
        code_node("Parse & Guard", "parse_guard.js", [1200, -80]),
        {
            "id": "ig-respond-result",
            "name": "Respond Result",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.4,
            "position": [1440, -80],
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ $json.response }}",
                "options": {"responseCode": 200},
            },
        },
        {
            # Side effects run after the reply is sent, so a slow or failing sink never delays the customer.
            "id": "ig-effect",
            "name": "Side Effect",
            "type": "n8n-nodes-base.switch",
            "typeVersion": 3.2,
            "position": [1680, -80],
            "parameters": {
                "rules": {
                    "values": [
                        {**condition("={{ $json.effect }}", name), "renameOutput": True, "outputKey": name}
                        for name in ("lead", "human")
                    ]
                },
                "options": {},
            },
        },
        code_node("Claim Lead", "claim_lead.js", [1920, -200]),
        {
            "id": "ig-new-lead",
            "name": "New Lead Today?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [2160, -200],
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                    "conditions": [
                        {
                            "id": "c-send",
                            "leftValue": "={{ $json.send }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
        },
        http_node(
            "ig-post-lead",
            "Post Lead",
            "={{ $env.LEADS_URL }}",
            "={{ $json.leadPayload }}",
            [2400, -240],
            timeout=8000,
        ),
        code_node("Release Lead On Error", "release_lead.js", [2640, -240]),
        http_node(
            "ig-notify-owner",
            "Notify Owner",
            "={{ $env.TELEGRAM_API_BASE + '/bot' + $env.TELEGRAM_BOT_TOKEN + '/sendMessage' }}",
            "={{ { chat_id: $env.TELEGRAM_CHAT_ID, text: $json.alertText } }}",
            [1920, 80],
            timeout=8000,
        ),
    ]
    connections = {
        "Webhook": link(["Gate"]),
        "Gate": link(["Gate OK?"]),
        "Gate OK?": link(["Build LLM Request"], ["Respond Reject"]),
        "Build LLM Request": link(["Call LLM"]),
        "Call LLM": link(["Parse & Guard"]),
        "Parse & Guard": link(["Respond Result"]),
        "Respond Result": link(["Side Effect"]),
        "Side Effect": link(["Claim Lead"], ["Notify Owner"]),
        "Claim Lead": link(["New Lead Today?"]),
        "New Lead Today?": link(["Post Lead"], []),
        "Post Lead": link(["Release Lead On Error"]),
    }
    return {
        "id": WORKFLOW_ID,
        "name": "IG Assistant",
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1", "timezone": "America/Argentina/Mendoza"},
    }


if __name__ == "__main__":
    out = ROOT / "n8n" / "workflows" / "assistant.json"
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
