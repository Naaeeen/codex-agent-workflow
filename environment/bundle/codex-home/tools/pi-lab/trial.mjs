import fs from 'node:fs';
import path from 'node:path';
import net from 'node:net';
import http from 'node:http';
import https from 'node:https';
import assert from 'node:assert/strict';
// Validate lexically before touching the filesystem or importing the SDK. Only a
// newly created local directory may supply this experiment's home and auth state.
const rawOutput = process.argv[2];
if (process.argv.length !== 3 || typeof rawOutput !== 'string' || !/^[A-Za-z]:[\\/]/.test(rawOutput)) {
  throw new Error('OUTPUT_PATH_INVALID: supply one absolute local Windows path, not UNC or device paths');
}
const segments = rawOutput.slice(3).split(/[\\/]/);
if (!segments.length || segments.some(segment => !segment || segment === '.' || segment === '..' ||
  /[<>:"|?*\u0000-\u001f]/.test(segment) || /[. ]$/.test(segment) ||
  /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(segment))) {
  throw new Error('OUTPUT_PATH_INVALID: root, traversal, empty, reserved or invalid path segment');
}
const out = path.win32.normalize(rawOutput);
try {
  // Atomic, non-recursive creation rejects any existing directory, file or link.
  // The caller must create the parent directory first.
  fs.mkdirSync(out);
} catch (error) {
  if (error.code === 'EEXIST') throw new Error('OUTPUT_PATH_EXISTS: choose a new trial directory');
  throw error;
}
// Drop provider credentials and move every home/state root before importing Pi.
for (const key of Object.keys(process.env)) {
  if (!['SystemRoot', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATH', 'PATHEXT'].includes(key)) delete process.env[key];
}
const home = path.join(out, 'home');
const agentDir = path.join(home, '.pi', 'agent');
fs.mkdirSync(agentDir, { recursive: true });
Object.assign(process.env, { HOME: home, USERPROFILE: home, APPDATA: path.join(home, 'AppData'), LOCALAPPDATA: path.join(home, 'LocalAppData'), PI_CODING_AGENT_DIR: agentDir });
let networkAttempts = 0;
const deny = () => { networkAttempts++; throw new Error('PI_LAB_NETWORK_DENIED'); };
globalThis.fetch = deny;
net.Socket.prototype.connect = deny;
http.request = deny; http.get = deny; https.request = deny; https.get = deny;
const { createAgentSession, createExtensionRuntime, ModelRuntime, SessionManager, SettingsManager } = await import('@earendil-works/pi-coding-agent');
const { fauxProvider, fauxAssistantMessage, fauxToolCall } = await import('@earendil-works/pi-ai/providers/faux');
const cwd = path.join(out, 'workspace');
fs.mkdirSync(cwd, { recursive: true });
const runtime = await ModelRuntime.create({ authPath: path.join(agentDir, 'auth.json'), modelsPath: path.join(agentDir, 'models.json'), modelsStorePath: path.join(agentDir, 'catalog.json'), allowModelNetwork: false, refreshOnCreate: false });
const faux = fauxProvider({ provider: 'pi-lab-faux', api: 'pi-lab-faux-api', tokenSize: { min: 1000, max: 1000 } });
runtime.registerNativeProvider(faux.provider);
const resourceLoader = {
  getExtensions: () => ({ extensions: [], errors: [], runtime: createExtensionRuntime() }),
  getSkills: () => ({ skills: [], diagnostics: [] }), getPrompts: () => ({ prompts: [], diagnostics: [] }),
  getThemes: () => ({ themes: [], diagnostics: [] }), getAgentsFiles: () => ({ agentsFiles: [] }),
  getSystemPrompt: () => 'Deterministic harness test.', getSystemPromptSource: () => undefined,
  getAppendSystemPrompt: () => [], getAppendSystemPromptSources: () => [], extendResources() {}, async reload() {},
};
const settingsManager = SettingsManager.inMemory({ compaction: { enabled: false }, retry: { enabled: false } });
let callbackCount = 0;
const options = { cwd, agentDir, modelRuntime: runtime, model: faux.getModel(), thinkingLevel: 'off', resourceLoader, settingsManager, tools: ['lab_double'], customTools: [{
  name: 'lab_double', label: 'Double', description: 'Deterministically double one number.',
  parameters: { type: 'object', properties: { value: { type: 'number' } }, required: ['value'], additionalProperties: false },
  async execute(_id, args) { callbackCount++; return { content: [{ type: 'text', text: String(args.value * 2) }], details: { value: args.value * 2 } }; },
}] };
const events = [];
const { session } = await createAgentSession({ ...options, sessionManager: SessionManager.create(cwd, path.join(out, 'sessions')) });
session.subscribe(event => events.push(event));
faux.setResponses([fauxAssistantMessage(fauxToolCall('lab_double', { value: 21 }, { id: 'double-1' }), { stopReason: 'toolUse' }), fauxAssistantMessage('RESULT 42')]);
await session.prompt('Call lab_double with 21.');
fs.writeFileSync(path.join(out, 'initial-events.jsonl'), events.map(e => JSON.stringify(e)).join('\n') + '\n');
assert.equal(callbackCount, 1); assert.equal(session.getLastAssistantText(), 'RESULT 42');
assert(events.some(e => e.type === 'tool_execution_end' && !e.isError));
assert.equal(events.find(e => e.type === 'tool_execution_end').result.details.value, 42);
assert.deepEqual(session.getActiveToolNames(), ['lab_double']);
assert(events.some(e => e.type === 'agent_settled'));
const sessionFile = session.sessionFile;
const messageCount = session.messages.length;
session.dispose();
const { session: reopened } = await createAgentSession({ ...options, sessionManager: SessionManager.open(sessionFile, path.join(out, 'sessions'), cwd) });
assert.equal(reopened.messages.length, messageCount); assert.equal(reopened.getLastAssistantText(), 'RESULT 42');
reopened.subscribe(event => events.push(event));
faux.setResponses([fauxAssistantMessage('', { stopReason: 'error', errorMessage: 'LAB_INJECTED_FAILURE' })]);
await reopened.prompt('Inject failure.');
assert.equal(reopened.messages.at(-1).stopReason, 'error');
assert.equal(reopened.messages.at(-1).errorMessage, 'LAB_INJECTED_FAILURE');
faux.setResponses([fauxAssistantMessage('RECOVERED')]);
await reopened.prompt('Recover on next explicit user turn.');
assert.equal(reopened.getLastAssistantText(), 'RECOVERED');
reopened.dispose();
assert.equal(networkAttempts, 0);
fs.writeFileSync(path.join(out, 'events.jsonl'), events.map(e => JSON.stringify(e)).join('\n') + '\n');
const summary = { package: '@earendil-works/pi-coding-agent@1.5.0', provider: 'built-in fauxProvider; scripted responses, no model inference', callbackCount, persistedMessages: messageCount, reopened: true, injectedFailureObserved: true, explicitNextTurnRecovered: true, automaticRetryTested: false, networkAttempts, fauxCalls: faux.state.callCount, eventTypes: [...new Set(events.map(e => e.type))], sessionFile, tests: 'PASS' };
fs.writeFileSync(path.join(out, 'summary.json'), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
