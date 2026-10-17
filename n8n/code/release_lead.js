// If the leads sink call failed, release today's claim so the next lead message retries.
const result = $input.first().json;
const contactId = $('Parse & Guard').first().json.contactId;

if (result && result.error) {
  const state = $getWorkflowStaticData('global');
  if (state.leads && state.leads.contacts) delete state.leads.contacts[contactId];
}
return [{ json: { released: Boolean(result && result.error) } }];
