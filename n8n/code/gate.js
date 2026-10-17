// Gate: shared-secret check, input validation and per-contact rate limit.
// Emits one item: { gate: 'ok' | 'unauthorized' | 'invalid' | 'rate_limited', status, body, input }.
// Rate-limit state lives in workflow static data, which n8n only persists for production
// (active, webhook-triggered) executions, not for manual test runs.
const LIMIT = 5;
const WINDOW_MS = 60 * 1000;
const RATE_LIMIT_REPLY =
  'Recibimos varios mensajes seguidos. Por favor, espera un momento y vuelve a escribirnos.';

const request = $input.first().json;
const headers = request.headers || {};
const payload = request.body && typeof request.body === 'object' ? request.body : {};

function sameSecret(given, expected) {
  if (typeof given !== 'string' || !expected || given.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= given.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}

function reject(gate, status, body) {
  return [{ json: { gate, status, body } }];
}

if (!sameSecret(headers['x-assistant-secret'], $env.ASSISTANT_SECRET || '')) {
  return reject('unauthorized', 401, { error: 'unauthorized' });
}

const text = (value, max) =>
  typeof value === 'string' || typeof value === 'number' ? String(value).trim().slice(0, max) : '';
const input = {
  channel: text(payload.channel, 40),
  contact_id: text(payload.contact_id, 128),
  username: text(payload.username, 100),
  message: text(payload.message, 1000),
};
if (!input.channel || !input.contact_id || !input.message) {
  return reject('invalid', 400, { error: 'invalid_request' });
}

const state = $getWorkflowStaticData('global');
state.rate = state.rate || {};
const now = Date.now();
for (const id of Object.keys(state.rate)) {
  state.rate[id] = state.rate[id].filter((t) => now - t < WINDOW_MS);
  if (state.rate[id].length === 0) delete state.rate[id];
}
const recent = state.rate[input.contact_id] || [];
if (recent.length >= LIMIT) {
  return [
    {
      json: {
        gate: 'rate_limited',
        status: 200,
        body: { reply: RATE_LIMIT_REPLY, intent: 'other', handoff: false },
      },
    },
  ];
}
recent.push(now);
state.rate[input.contact_id] = recent;

return [{ json: { gate: 'ok', input } }];
