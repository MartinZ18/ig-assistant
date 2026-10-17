// One lead per contact per day. The claim is written before the POST so two quick messages do not
// both send; "Release Lead On Error" gives the claim back if the sink call failed.
// Static data keeps only today's claims, so it cannot grow without bound.
const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Argentina/Mendoza' });
const item = $input.first().json;

const state = $getWorkflowStaticData('global');
if (!state.leads || state.leads.day !== today) state.leads = { day: today, contacts: {} };

const send = !state.leads.contacts[item.contactId];
if (send) state.leads.contacts[item.contactId] = true;

return [{ json: { ...item, send } }];
