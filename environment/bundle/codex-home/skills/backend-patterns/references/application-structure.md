# Application structure

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

## Repository responsibilities

A repository exposes the data operations the use case needs. Its implementation
must honor the authorization/tenant scope and error contract. This interface is
illustrative; the source's service called `findByIds` although it was absent from
the interface, which is corrected here.

```typescript
interface MarketRepository {
  findAll(filters?: MarketFilters): Promise<Market[]>
  findById(id: string): Promise<Market | null>
  findByIds(ids: readonly string[]): Promise<Market[]>
  create(data: CreateMarketDto): Promise<Market>
  update(id: string, data: UpdateMarketDto): Promise<Market>
  delete(id: string): Promise<void>
}
```

Keep provider implementation details behind this contract where it helps the
use case. A repository does not bypass row-level policy or establish identity.
For Supabase implementations, first use the dedicated Supabase skill and the
installed generated schema types; do not assume nullable data is `Market[]`.

## Service responsibilities

The original search use case combines an embedding search with a batch fetch.
Keep this behavior separate from HTTP serialization. Fetching by a set of IDs
does not guarantee the search rank order, so restore it explicitly.

```typescript
// Fragment inside a service whose dependencies already satisfy these contracts.
const embedding = await generateEmbedding(query)
const ranked = await vectorSearch(embedding, limit)
const markets = await marketRepo.findByIds(ranked.map(result => result.id))
const scores = new Map(ranked.map(result => [result.id, result.score]))
const ordered = [...markets].sort(
  (a, b) => (scores.get(b.id) ?? -Infinity) - (scores.get(a.id) ?? -Infinity)
)
```

This ordering assumes a higher score means greater similarity. Verify whether the
actual provider returns similarity or distance, how missing IDs are handled, and
whether source records still satisfy the caller's access scope. Validate and cap
the requested limit before expensive work. No embedding-provider call was run.

## Transport and middleware

Adapters parse/validate requests, obtain trusted context, call the use case, and
map outcomes to the existing API contract. Read [identity and middleware](identity-and-middleware.md)
for principal handoff. See `api-design` for HTTP semantics; there is no second
REST naming guide in this skill.
