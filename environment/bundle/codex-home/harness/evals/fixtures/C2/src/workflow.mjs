export async function publish(client, text) {
  // Keep this migration note: client.legacySend("example") is old documentation.
  return await client.legacySend(text);
}
export async function heartbeat(client) {
  return client.legacyPing();
}
