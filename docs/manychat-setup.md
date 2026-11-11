# ManyChat setup

Goal: Instagram comment or DM -> ManyChat -> `POST /webhook/assistant` (n8n) -> reply sent back to the customer.
Menu names change between ManyChat versions; where a label is uncertain this guide says "look for".
Official docs: https://help.manychat.com

## 0. Before you start

- n8n must be reachable from the internet over HTTPS (a tunnel or a server). `localhost` is not reachable by ManyChat.
- Have your `ASSISTANT_SECRET` (from `.env`) at hand.
- Check that your ManyChat plan includes the **External Request** action (availability depends on the plan; see the help center). Without it, this integration cannot work.

## 1. Connect Instagram

1. The Instagram account must be a **professional** account (Business or Creator), linked to a Facebook Page.
2. In ManyChat, look for the Instagram connection (Settings -> Instagram or the onboarding screen), choose Connect, log in and accept the permissions.
3. Confirm that ManyChat can see messages from that account (send a DM from a second account).

## 2. Comment automation (keyword -> public reply + DM)

1. Look for **Automation** -> New Automation, with the Instagram trigger for **comments on a post or reel** (often called Comments/Post or Reel Comments).
2. Pick the post or reel. Set the keyword filter to contain `PRECIO` and `INFO` (add both).
3. Add a public reply to the comment (for example "Te escribimos por privado!"). Several variants are better than one.
4. Add the DM action with a short message and **buttons** (for example "Ver precios", "Hablar con una persona"). Keep the text under the Instagram DM limits shown in the editor.
5. Set the automation live.

## 3. Default Reply -> External Request

The Default Reply runs when no other automation matches a DM.

1. Look for Automation -> **Default Reply** (under the Instagram settings or Automation section).
2. Add an action **External Request** (look for "Actions" -> "External Request") with:
   - Method `POST`, URL `https://<n8n host>/webhook/assistant`
   - Header `X-Assistant-Secret: <ASSISTANT_SECRET>`, header `Content-Type: application/json`
   - Body (JSON; insert ManyChat fields with the field picker, names below are the usual ones):

         {
           "channel": "instagram",
           "contact_id": "{{user_id}}",
           "username": "{{ig_username}}",
           "message": "{{last_text_input}}"
         }

     `contact_id` = the ManyChat user id field, `username` = the Instagram username field, `message` = the last text input field.
3. Create two **custom fields** (User fields): `ai_reply` (text) and `ai_handoff` (use text or boolean, per what the response mapping offers).
4. In the request's **Response mapping** (look for the "Response" tab and Test the request), map:
   - `$.reply` -> `ai_reply`
   - `$.handoff` -> `ai_handoff`
5. Next action: **Send message** with the text `{{ai_reply}}`.
6. Add a **Condition** on `ai_handoff` (is true / equals `true`): in that branch pause the automation for that contact and move the conversation to live chat (look for "Pause automation" / "Live Chat" / "Conversation" actions, and Notify admin if you want an alert in ManyChat too). The owner also gets a Telegram message from n8n on every handoff.

Constraints to keep in mind:

- The External Request has a short timeout. This workflow caps the LLM call (`LLM_TIMEOUT_MS`, 3000 by default) and always answers with a canned reply on failure, so ManyChat gets a response. Check the current limit in the help center rather than assuming a number. n8n runs one execution at a time (`N8N_CONCURRENCY_PRODUCTION_LIMIT=1`, needed for exact rate limits), so during a burst queued messages can wait longer than that timeout; see the rate-limit note in the README.
- The plan, pricing and Instagram messaging window rules are set by ManyChat and Meta; check the pricing page and help center for current values.

Response contract, for reference: `{"reply": "...", "intent": "faq|lead|human|other", "handoff": true|false}`.
Wrong or missing secret -> HTTP 401.

## 4. Test without Instagram

With the stack running (`docker compose up`), call the webhook directly:

    curl -s -X POST http://localhost:5678/webhook/assistant \
      -H "Content-Type: application/json" -H "X-Assistant-Secret: $ASSISTANT_SECRET" \
      -d '{"channel":"instagram","contact_id":"manual-1","username":"demo","message":"¿Cuánto sale el buzo canguro?"}'

Expected: HTTP 200 and `{"reply":"...","intent":"faq","handoff":false}`.

Handoff (also sends the Telegram alert):

    curl -s -X POST http://localhost:5678/webhook/assistant \
      -H "Content-Type: application/json" -H "X-Assistant-Secret: $ASSISTANT_SECRET" \
      -d '{"channel":"instagram","contact_id":"manual-2","username":"demo","message":"Quiero hablar con una persona"}'

Wrong secret (expect 401):

    curl -i -X POST http://localhost:5678/webhook/assistant -H "X-Assistant-Secret: wrong" \
      -H "Content-Type: application/json" -d '{"channel":"instagram","contact_id":"x","username":"x","message":"hola"}'

For the full set of cases with the real model, run `python eval/live_eval.py`.
