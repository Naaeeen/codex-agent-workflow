export async function publish(client, text) {
  // Keep this migration note: client.legacySend("example") is old documentation.
  return client['send'](text);
}
export async function heartbeat(client) {
  return await client['ping']();
}
