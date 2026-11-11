// Parse the LLM answer, validate its shape and run the deterministic commercial-terms guard.
// Any failure (HTTP error, timeout, non-JSON, wrong schema, a price or term the catalog does not
// back) becomes the canned handoff reply. n8n, not the model, decides side effects: `effect` is
// derived from intent. The catalog is baked in by n8n/build_workflow.py.
const CATALOG = __CATALOG__;
const FALLBACK_REPLY =
  'Gracias por escribirnos. En este momento no puedo responder tu consulta, pero una persona del equipo te va a contestar a la brevedad.';
const INTENTS = ['faq', 'lead', 'human', 'other'];

const input = $('Build LLM Request').first().json.input;
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

// --- commercial-terms guard ------------------------------------------------------------------
// A price passes only if it belongs to what it is attached to: the product (or shipping zone)
// its clause talks about. Shipping costs are valid only for shipping, the free-shipping threshold
// only in a free-shipping sentence. Terms the catalog never states (percentages, NxM promos,
// foreign currency, spelled-out amounts, more installments than the catalog allows) always fail.

// NFKC turns fullwidth/compatibility digits into ASCII; accents are dropped so "envío" == "envio".
const fold = (s) =>
  s.normalize('NFKC').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const words = (s) => fold(s).replace(/[^a-z0-9 ]+/g, ' ').trim().split(/\s+/).filter(Boolean);

const STOPWORDS = new Set(['de', 'del', 'con', 'en', 'la', 'el', 'y', 'a']);
const NOT_ALIASES = new Set(['cargo']); // "sin cargo", "a cargo de"

// alias -> { kind: 'product' | 'shipping', values: Set of amounts valid for it, ids: products it names }
const aliases = new Map();
function addAlias(text, kind, values, id) {
  const alias = words(text).join(' ');
  if (!alias || NOT_ALIASES.has(alias)) return;
  const entry = aliases.get(alias) || { kind, values: new Set(), ids: new Set() };
  for (const v of values) entry.values.add(v);
  if (id) entry.ids.add(id);
  aliases.set(alias, entry);
}
for (const p of CATALOG.products) {
  const w = words(p.name);
  const price = [p.price_ars];
  addAlias(p.name, 'product', price, p.id);
  addAlias(w[0], 'product', price, p.id); // "remera" covers every remera: any of their prices
  if (w[1] && !STOPWORDS.has(w[1])) {
    addAlias(`${w[0]} ${w[1]}`, 'product', price, p.id);
    if (w[1].length >= 4) addAlias(w[1], 'product', price, p.id); // "la oversize"
  }
  // Category singular ("pantalones" -> "pantalon"); the matcher accepts the plural.
  addAlias(p.category.replace(/(?<=[nlrd])es$/, '').replace(/s$/, ''), 'product', price, p.id);
}
const shippingCosts = CATALOG.shipping.zones.map((z) => z.cost_ars).filter((c) => c > 0);
addAlias('envio', 'shipping', shippingCosts);
for (const zone of CATALOG.shipping.zones) {
  const cost = zone.cost_ars > 0 ? [zone.cost_ars] : [];
  const [main, inner] = zone.name.split('(');
  addAlias(main, 'shipping', cost);
  if (inner) {
    addAlias(inner, 'shipping', cost); // "envío en moto"
    const last = words(inner).pop();
    if (last && last.length >= 4) addAlias(last, 'shipping', cost); // "moto", "correo"
  }
}
const ALIAS_LIST = [...aliases.entries()]
  .sort((a, b) => b[0].length - a[0].length)
  .map(([alias, info]) => ({
    re: new RegExp(`(?<![a-z0-9])${alias.split(' ').join('\\s+')}(?:e?s)?(?![a-z0-9])`, 'g'),
    kind: info.kind,
    values: info.values,
    // A generic alias ("remera", "abrigo") names several products: it can carry a range or a
    // list of prices, but a single price on it cannot tell which product it belongs to.
    generic: info.kind === 'product' && info.ids.size > 1,
  }));

// Longest alias wins where two overlap ("remera basica de algodon" over "remera").
function findMentions(t) {
  const out = [];
  for (const { re, kind, values, generic } of ALIAS_LIST) {
    for (const m of t.matchAll(re)) {
      const start = m.index;
      const end = start + m[0].length;
      if (!out.some((o) => start < o.end && end > o.start)) out.push({ start, end, kind, values, generic });
    }
  }
  return out.sort((a, b) => a.start - b.start);
}

// Clauses: split on sentence ends, ";", ":", ", " and conjunctions, never inside a mention
// ("Ciudad y alrededores") or a number ("12.900").
const CLAUSE_RE = /[.!?;:]+(?=\s|$)|\n|,(?=\s)|\s(?:y|e|o|u|pero|aunque|mientras)\s/g;
const SENTENCE_RE = /[.!?]+(?=\s|$)|\n/g;
function segments(t, re, mentions) {
  const cuts = [0];
  for (const m of t.matchAll(re)) {
    if (!mentions.some((o) => m.index > o.start && m.index < o.end)) cuts.push(m.index);
  }
  cuts.push(t.length);
  return cuts.slice(0, -1).map((start, i) => ({ start, end: cuts[i + 1] }));
}

const MULT = '(?:mil|k|lucas)';
// $N, N pesos/ARS, N mil/k/lucas, and numbers with thousands separators or 4+ digits.
// Small bare numbers (30 dias, 10 a 19 horas, 3 cuotas) are not prices.
const PRICE_RE = new RegExp(
  `\\$\\s*(\\d[\\d.,]*)(?:\\s*(${MULT})(?![a-z]))?` +
    `|(\\d[\\d.,]*)\\s*(?:(${MULT})\\s*)?(?:pesos|ars)(?![a-z])` +
    `|(\\d[\\d.,]*)\\s*(${MULT})(?![a-z])` +
    `|\\b(\\d{1,3}(?:[.,]\\d{3})+|\\d{4,})\\b`,
  'g',
);
function toValue(token, mult) {
  token = token.replace(/[.,]+$/, '');
  if (mult) {
    const dec = /^(\d+)[.,](\d{1,2})$/.exec(token); // "52,9 mil"
    const n = dec ? Number(`${dec[1]}.${dec[2]}`) : Number(token.replace(/[.,]/g, ''));
    return Math.round(n * 1000);
  }
  token = token.replace(/[.,]\d{1,2}$/, ''); // cents
  return Number(token.replace(/[.,]/g, ''));
}

const NUM_WORD =
  '(?:un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|' +
  'dieci[a-z]+|veinte|veinti[a-z]+|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|' +
  'cien|ciento|[a-z]+cientos|[a-z]+cientas|quinientos|mil)';
const NUM_VALUE = { un: 1, uno: 1, una: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9, diez: 10, once: 11, doce: 12 };
// "doce mil pesos", "quince dolares", "mil pesos", "veinte por ciento"
const SPELLED_AMOUNT_RE = new RegExp(
  `(?<![a-z])${NUM_WORD}(?:\\s+(?:y\\s+)?${NUM_WORD})*\\s+` +
    '(?:mil|millon(?:es)?|pesos?|ars|lucas|dolar(?:es)?|usd|euros?|por\\s*ciento)(?![a-z])',
);
const FOREIGN_RE =
  /(?:usd|u\$s|us\$|u\$d|eur|euros?|€|dolar(?:es)?|reales?)\s*\d|\d[\d.,]*\s*(?:usd|u\$s|u\$d|eur|euros?|€|dolar(?:es)?|reales?)(?![a-z])/;
const NON_ASCII_DIGIT_RE = /(?![0-9])\p{Nd}/u;
const PERCENT_RE = /\d[\d.,]*\s*(?:%|por\s*ciento)/;
const MATERIAL_PERCENT_RE = /100\s*(?:%|por\s*ciento)\s*(?:de\s+)?(?:algodon|lana|lino|cuero)/g;
const PROMO_RE = /(?<![a-z0-9])\d+\s*x\s*\d+(?![a-z0-9])/;
const INSTALLMENTS_RE = new RegExp(`(?<![a-z0-9])(\\d+|${NUM_WORD})\\s+(?:cuotas?|pagos)(?![a-z])`, 'g');
const MAX_INSTALLMENTS = (() => {
  const m = /hasta\s+(\d+)\s+cuotas/.exec(fold(CATALOG.payment_methods.join(' ')));
  return m ? Number(m[1]) : 0;
})();
const DISCOUNT_RE = /descuent|rebaj|bonific|promo|oferta|liquidac|precio especial/;
const FREE_RE = /gratis|sin cargo|sin costo|bonificad/;
const OVER_RE = /(?:superior(?:es)?|mas de|supera\w*|a partir de|desde|por encima de|mayor(?:es)? a)\s*(?:a|los|de)?\s*$/;
const THRESHOLD = CATALOG.shipping.free_shipping_over_ars;

// The subject of a clause is the nearest product it names; shipping only when it names no product.
// ("Por correo la campera sale $6.800" is about the campera, so a shipping cost cannot pass.)
// Wording alone cannot tell "the shipping of the campera costs X" from "the campera costs X", so a
// shipping cost in a clause that names a product is always handed off (see README Limitations).
function clauseSubject(ms, pos) {
  const pick = (list) => {
    const before = list.filter((m) => m.end <= pos);
    return before.length ? before[before.length - 1] : list.find((m) => m.start >= pos);
  };
  const products = ms.filter((m) => m.kind === 'product');
  return pick(products.length ? products : ms.filter((m) => m.kind === 'shipping'));
}

// Words that may surround a bare price without naming anything ("Claro, sale $33.400.").
// Never add nouns here: an unknown noun ("la chaqueta") must not borrow the customer's product.
const FILLER = new Set([
  'si', 'sale', 'salen', 'cuesta', 'cuestan', 'vale', 'valen', 'esta', 'estan', 'es', 'son', 'queda',
  'quedan', 'tiene', 'el', 'la', 'los', 'las', 'lo', 'te', 'su', 'un', 'una', 'de', 'del', 'por', 'a',
  'en', 'y', 'precio', 'costo', 'valor', 'pesos', 'ars', 'mil', 'k', 'lucas', 'hola', 'claro', 'dale',
  'ok', 'perfecto', 'genial', 'gracias', 'buenas', 'ese', 'esa', 'eso', 'este', 'esto', 'ahora',
  'hoy', 'actualmente', 'reservo', 'reservamos', 'queres', 'quieres', 'que', 'para', 'vos', 'ti',
]);

function breaksCommercialTerms(reply, message) {
  const t = fold(reply);
  if (NON_ASCII_DIGIT_RE.test(t)) return true;
  if (FOREIGN_RE.test(t) || SPELLED_AMOUNT_RE.test(t) || PROMO_RE.test(t)) return true;
  if (PERCENT_RE.test(t.replace(MATERIAL_PERCENT_RE, ''))) return true;
  for (const m of t.matchAll(INSTALLMENTS_RE)) {
    const n = /^\d+$/.test(m[1]) ? Number(m[1]) : NUM_VALUE[m[1]];
    if (!n || n > MAX_INSTALLMENTS) return true;
  }

  const mentions = findMentions(t);
  const clauses = segments(t, CLAUSE_RE, mentions);
  const sentences = segments(t, SENTENCE_RE, mentions);
  const inside = (seg) => mentions.filter((m) => m.start >= seg.start && m.start < seg.end);
  const messageMentions = findMentions(fold(message || ''));
  const priceMatches = [...t.matchAll(PRICE_RE)];
  // The customer's message (attacker-written) may only resolve a reply that names nothing at all.
  const namesSomething = words(reply).some((w) => !/^\d/.test(w) && !FILLER.has(w));

  // A generic subject ("abrigo") must carry two or more DISTINCT prices across the reply ("entre
  // $38.900 y $41.500", "$9.800, $12.900 y $17.500"); repeating one price does not make a range.
  const genericPrices = new Map(); // mention -> Set of values attributed to it
  for (const match of priceMatches) {
    const pos = match.index;
    const value = toValue(match[1] || match[3] || match[5] || match[7], match[2] || match[4] || match[6]);
    const ci = clauses.findIndex((c) => pos >= c.start && pos < c.end);
    const clause = clauses[ci];
    if (DISCOUNT_RE.test(t.slice(clause.start, clause.end))) return true;

    const sentence = sentences.find((s) => pos >= s.start && pos < s.end);
    if (
      value === THRESHOLD &&
      inside(sentence).some((m) => m.kind === 'shipping') &&
      FREE_RE.test(t.slice(sentence.start, sentence.end)) &&
      OVER_RE.test(t.slice(Math.max(sentence.start, pos - 40), pos))
    ) {
      continue;
    }

    let subject = null;
    for (let k = ci; k >= 0 && !subject; k--) {
      const ms = inside(clauses[k]);
      if (ms.length) {
        subject = clauseSubject(ms, k === ci ? pos : Infinity);
      }
    }
    if (subject) {
      if (!subject.values.has(value)) return true;
      if (subject.generic) {
        if (!genericPrices.has(subject)) genericPrices.set(subject, new Set());
        genericPrices.get(subject).add(value);
      }
    } else if (namesSomething || !messageMentions.length || !messageMentions.every((m) => m.values.has(value))) {
      // The reply names nothing: the price must fit everything the customer asked about.
      return true;
    }
  }
  return [...genericPrices.values()].some((values) => values.size < 2);
}

let answer = parseAnswer();
if (answer && breaksCommercialTerms(answer.reply, input.message)) answer = null;
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
