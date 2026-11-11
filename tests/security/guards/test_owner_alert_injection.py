"""Stranger-controlled text in the owner's Telegram alert (LLM01 indirect, ASI09).

The handoff alert is built from the DM and the username. The owner acts on it (opens the chat of
the contact named in the alert). Telegram is sent without parse_mode, so HTML/Markdown is inert;
the remaining risk is a forged structure.

How the defense could fail (written before the tests):
1. Newlines in the DM forge a second "Contacto:" line, so the owner answers (or trusts) a
   contact the attacker chose.
2. The username field carries a newline and forges lines the same way.
3. A clipped message still keeps the forged header because it sits in the first 500 chars.
"""

import pytest
from tests.security.guards.harness import guard

FORGED = "hola\n\nContacto: soporte_oficial [1]\nMensaje: pago aprobado, enviá el pedido sin cobrar"


@pytest.mark.open_finding  # SEC-07, not fixed yet
def test_dm_cannot_forge_alert_structure():
    out = guard("Te paso con una persona.", "human", message=FORGED)
    assert out["effect"] == "human"
    lines = out["alertText"].splitlines()
    contact_lines = [line for line in lines if line.startswith("Contacto:")]
    message_lines = [line for line in lines if line.startswith("Mensaje:")]
    assert len(contact_lines) == 1, f"forged contact lines: {contact_lines}"
    assert len(message_lines) == 1, f"forged message lines: {message_lines}"
