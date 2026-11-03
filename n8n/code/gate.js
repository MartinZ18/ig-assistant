// Gate: shared-secret check, input validation, per-contact and per-account rate limits.
// The per-account limit caps total LLM spend even if contact_id is rotated.
// Emits one item: { gate: 'ok' | 'unauthorized' | 'invalid' | 'rate_limited', status, body, input }.
// Rate-limit state lives in workflow static data, which n8n only persists for production
// (active, webhook-triggered) executions, not for manual test runs.
function envInt(name, fallback) {
  const n = Number.parseInt($env[name], 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}
const LIMIT = envInt('RATE_LIMIT_PER_CONTACT', 5);
const ACCOUNT_LIMIT = envInt('RATE_LIMIT_PER_ACCOUNT', 60);
const WINDOW_MS = envInt('RATE_LIMIT_WINDOW_SECONDS', 60) * 1000;
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
// Instagram account/page the message arrived on. Single-account setups may omit it.
const accountId = text(payload.account_id, 128) || 'default';
if (!input.channel || !input.contact_id || !input.message) {
  return reject('invalid', 400, { error: 'invalid_request' });
}

const state = $getWorkflowStaticData('global');
state.rate = state.rate || {};
state.accountRate = state.accountRate || {};
const now = Date.now();
function prune(map) {
  for (const id of Object.keys(map)) {
    map[id] = map[id].filter((t) => now - t < WINDOW_MS);
    if (map[id].length === 0) delete map[id];
  }
}
prune(state.rate);
prune(state.accountRate);

const recent = state.rate[input.contact_id] || [];
const accountRecent = state.accountRate[accountId] || [];
// A blocked message consumes neither budget, so a flooding contact cannot drain the account.
if (recent.length >= LIMIT || accountRecent.length >= ACCOUNT_LIMIT) {
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
accountRecent.push(now);
state.accountRate[accountId] = accountRecent;

return [{ json: { gate: 'ok', input } }];
