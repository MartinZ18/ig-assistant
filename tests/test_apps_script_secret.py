"""Apps Script secret check, run through node by loading Code.gs in a vm sandbox."""

import json
import subprocess
from pathlib import Path

CODE_GS = Path(__file__).resolve().parent.parent / "apps-script" / "Code.gs"

HARNESS = """
const vm = require('vm'), fs = require('fs');
const ctx = {};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
const cases = JSON.parse(process.argv[2]);
console.log(JSON.stringify(cases.map(([g, e]) => ctx.sameSecret(g, e))));
"""


def run(cases):
    out = subprocess.run(
        ["node", "-e", HARNESS, str(CODE_GS), json.dumps(cases)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    return json.loads(out.stdout)


def test_same_secret_accepts_only_exact_matches():
    secret = "s3cr3t-ñ-" + "x" * 40
    cases = [
        [secret, secret],
        [secret[:-1], secret],          # prefix
        [secret + "x", secret],         # longer
        [secret[:-1] + "y", secret],    # last char differs
        ["y" + secret[1:], secret],     # first char differs
        ["", secret],
        [None, secret],
        [123, secret],
        [secret, ""],                   # unset expected secret never matches
        [secret, None],
        ["", ""],
    ]
    assert run(cases) == [True, False, False, False, False, False, False, False, False, False, False]
