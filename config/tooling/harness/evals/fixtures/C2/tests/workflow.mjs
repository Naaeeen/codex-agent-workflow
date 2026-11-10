import test from 'node:test';
import assert from 'node:assert/strict';
import {publish} from '../src/workflow.mjs';
test('publishes through the current client', async () => {
  assert.equal(await publish({send: async text => text.toUpperCase()}, 'x'), 'X');
});
