export async function resend(client, values) {
  return await values.reduce(async (pending, value) => {
    const results = await pending;
    results.push(await client.send(value));
    return results;
  }, Promise.resolve([]));
}
