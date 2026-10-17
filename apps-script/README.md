# Leads sheet (Apps Script)

`Code.gs` is a Google Apps Script web app that receives leads from n8n and writes them to a sheet.

## Behavior

- `POST` JSON `{secret, channel, contact_id, username, message, timestamp}`.
- Wrong or missing `secret` (compared with the Script Property `LEADS_SECRET`) -> `{"ok":false,"error":"unauthorized"}`.
  Missing `contact_id`, `channel` or `message`, or no `username` key -> `{"ok":false,"error":"missing field: ..."}`.
- One row per `contact_id` per day (America/Argentina/Mendoza). A repeat post that day updates
  `last_message` and `updated_at`; otherwise a row is appended. A script lock serializes concurrent posts.
- Columns: `created_at, updated_at, channel, contact_id, username, first_message, last_message, status` (`status` starts as `nuevo`).
- The secret is in the body because Apps Script web apps cannot read request headers.

## Deploy

1. Create a Google Sheet. Open Extensions -> Apps Script and paste `Code.gs` over the default file.
2. Project Settings -> Script Properties -> add `LEADS_SECRET` with a long random value (same as `LEADS_SECRET` in `.env`).
3. Deploy -> New deployment -> type Web app. Execute as: **Me**. Who has access: **Anyone**. Authorize when asked.
4. Copy the web app URL (ends in `/exec`) into `LEADS_URL` in `.env`, then restart n8n.
5. After any code change, create a new deployment version (Deploy -> Manage deployments -> edit -> New version); the `/exec` URL stays the same.
6. Smoke test (a `Leads` tab is created on the first call):

       curl -L -X POST "$LEADS_URL" -H "Content-Type: application/json" \
         -d '{"secret":"<LEADS_SECRET>","channel":"instagram","contact_id":"test-1","username":"demo","message":"hola"}'

   Expect `{"ok":true,"action":"created"}`; repeating it expects `"action":"updated"`.

## Redirects (302 -> 200)

Apps Script answers the POST with a `302` to a `script.googleusercontent.com` URL that holds the response.
`curl` needs `-L`. In the n8n HTTP Request node (typeVersion 4.2, the one this workflow uses), redirects
are followed by default: the node source in the pinned image (`n8n:2.18.7`) enables `followRedirect`
and `followAllRedirects` when the "Redirects" option is not set, and `Post Lead` does not set it.
So no change is needed. If you ever see a redirect error there, open Options -> add "Redirects" -> turn
"Follow Redirects" on.

Not verified against a real deployment (needs a Google account). Even if following the redirect failed,
the row is already written by the first request; n8n would treat the call as failed and release its
claim, and the per-day upsert here keeps the retry from creating a duplicate row.
