import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const evidence = path.resolve(process.argv[2]);
fs.mkdirSync(evidence); // Preserve all earlier checks; refuse existing evidence.
const script = fileURLToPath(new URL('./trial.mjs', import.meta.url));
const run = value => spawnSync(process.execPath, [script, value], { encoding: 'utf8', timeout: 30000 });
const snapshot = folder => {
  const result = {};
  const visit = dir => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const name = path.join(dir, entry.name);
      if (entry.isDirectory()) visit(name);
      else result[path.relative(folder, name)] = crypto.createHash('sha256').update(fs.readFileSync(name)).digest('hex');
    }
  };
  visit(folder); return result;
};
const existing = path.join(evidence, 'existing-sentinel');
fs.mkdirSync(path.join(existing, 'home', '.pi', 'agent'), { recursive: true });
fs.writeFileSync(path.join(existing, 'summary.json'), 'KEEP ORIGINAL SUMMARY\r\n');
fs.writeFileSync(path.join(existing, 'events.jsonl'), '{"sentinel":true}\n');
fs.writeFileSync(path.join(existing, 'home', '.pi', 'agent', 'auth.json'), 'INVALID JSON: MUST NEVER BE READ\n');
const before = snapshot(existing);
const rejected = run(existing);
assert.notEqual(rejected.status, 0);
assert.match(rejected.stderr, /OUTPUT_PATH_EXISTS/);
assert.deepEqual(snapshot(existing), before);
const invalidPaths = ['relative-trial', '\\\\server\\share\\trial', '\\\\?\\C:\\trial', 'C:\\', 'C:\\parent\\..\\trial', 'C:\\bad:name', 'C:\\NUL'];
const invalid = invalidPaths.map(value => {
  const result = run(value);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /OUTPUT_PATH_INVALID/);
  return { value, exitCode: result.status, lexicalRejection: true };
});
const fresh = run(path.join(evidence, 'fresh'));
assert.equal(fresh.status, 0, fresh.stderr);
const summary = JSON.parse(fs.readFileSync(path.join(evidence, 'fresh', 'summary.json'), 'utf8'));
assert.equal(summary.tests, 'PASS'); assert.equal(summary.networkAttempts, 0);
const result = { existingRejected: true, sentinelHashesBefore: before, sentinelHashesAfter: snapshot(existing), sentinelBytesUnchanged: true, invalid, fresh: summary };
fs.writeFileSync(path.join(evidence, 'guard-summary.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
