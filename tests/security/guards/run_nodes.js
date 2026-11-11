// Runs Code-node source taken from the GENERATED workflow (n8n/workflows/assistant.json),
// i.e. exactly what n8n executes, with minimal stand-ins for $input, $env, $() and static data.
// stdin: {"workflow": path, "steps": [{"node": name, "input": json | {"$from": name}, "env": {...}}]}
// stdout: JSON array with the first output item of each step, plus the final static data.
const fs = require('fs');
const spec = JSON.parse(fs.readFileSync(0, 'utf8'));
const wf = JSON.parse(fs.readFileSync(spec.workflow, 'utf8'));
const staticData = { global: {} };
const lastOutput = {};

function source(name) {
  const node = wf.nodes.find((n) => n.name === name);
  if (!node || !node.parameters || typeof node.parameters.jsCode !== 'string') {
    throw new Error(`no Code node named ${name}`);
  }
  return node.parameters.jsCode;
}

const results = [];
for (const step of spec.steps) {
  const fn = new Function('$input', '$env', '$', '$getWorkflowStaticData', source(step.node));
  // {"$from": "Node"} feeds the previous output of that node, as an n8n connection would.
  const input = step.input && step.input.$from ? lastOutput[step.input.$from] : step.input;
  const $input = { first: () => ({ json: input }), all: () => [{ json: input }] };
  const $ = (name) => ({ first: () => ({ json: lastOutput[name] }) });
  const out = fn($input, step.env || {}, $, (kind) => staticData[kind]);
  lastOutput[step.node] = out[0].json;
  results.push(out[0].json);
}
process.stdout.write(JSON.stringify({ results, staticData }));
