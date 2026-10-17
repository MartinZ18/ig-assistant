// Parse the LLM answer, validate its shape and run the deterministic price guard.
// Any failure (HTTP error, timeout, non-JSON, wrong schema, unknown price) becomes the canned
// handoff reply. n8n, not the model, decides side effects: `effect` is derived from intent.
const FALLBACK_REPLY =
  'Gracias por escribirnos. En este momento no puedo responder tu consulta, pero una persona del equipo te va a contestar a la brevedad.';
const INTENTS = ['faq', 'lead', 'human', 'other'];

const context = $('Build LLM Request').first().json;
const input = context.input;
const allowed = new Set(context.allowedPrices);
const llm = $input.first().json;

function parseAnswer() {
  if (!llm || llm.error || !Array.isArray(llm.choices)) return null;
  const content = llm.choices[0] && llm.choices[0].message && llm.choices[0].message.content;
  if (typeof content !== 'string') return null;
  let answer;
  try {
    answer = JSON.parse(content);
  } catch (e) {
    return null;
  }
  if (!answer || typeof answer !== 'object') return null;
  const reply = typeof answer.reply === 'string' ? answer.reply.trim() : '';
  if (!reply || reply.length > 1000 || !INTENTS.includes(answer.intent)) return null;
  return { reply, intent: answer.intent };
}

// Prices are numbers after "$", before "pesos"/"ARS", or written with thousands separators / 4+ digits.
// Small bare numbers (30 días, 10 a 19 horas, 3 cuotas) are not prices.
function quotesUnknownPrice(reply) {
  const pattern = /\$\s*(\d[\d.,]*)|(\d[\d.,]*)\s*(?:pesos|ars)\b|\b(\d{1,3}(?:[.,]\d{3})+|\d{4,})\b/gi;
  for (const match of reply.matchAll(pattern)) {
    let token = (match[1] || match[2] || match[3]).replace(/[.,]+$/, '');
    token = token.replace(/[.,]\d{1,2}$/, ''); // cents
    const value = Number(token.replace(/[.,]/g, ''));
    if (!allowed.has(value)) return true;
  }
  return false;
}

let answer = parseAnswer();
if (answer && quotesUnknownPrice(answer.reply)) answer = null;
if (!answer) answer = { reply: FALLBACK_REPLY, intent: 'human' };

const handoff = answer.intent === 'human';
const clip = (value, max) => (value.length > max ? value.slice(0, max) + '...' : value);

return [
  {
    json: {
      response: { reply: answer.reply, intent: answer.intent, handoff },
      effect: answer.intent === 'lead' ? 'lead' : handoff ? 'human' : 'none',
      leadPayload: {
        secret: $env.LEADS_SECRET || '',
        channel: input.channel,
        contact_id: input.contact_id,
        username: input.username,
        message: input.message,
        timestamp: new Date().toISOString(),
      },
      alertText:
        `Atención humana requerida (${input.channel})\n` +
        `Contacto: ${input.username || '(sin usuario)'} [${input.contact_id}]\n` +
        `Mensaje: ${clip(input.message, 500)}`,
      contactId: input.contact_id,
    },
  },
];
