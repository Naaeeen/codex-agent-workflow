export async function resend(client, values) {
  const results = [];
  for (const value of values) results.push(await client.send(value));
  return results;
}
