# Data access, transactions and caching

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

## Database Patterns

Provider-specific fragments below were retained from the local source to explain
query shape and atomic failure behavior. Use the dedicated Supabase skill before
adapting them. The SQL assumes the stated schema; execution grants and RLS are
part of the real deployment, not established by this example.

### Query Optimization

```typescript
// PASS: GOOD: Select only needed columns
const { data } = await supabase
  .from('markets')
  .select('id, name, status, volume')
  .eq('status', 'active')
  .order('volume', { ascending: false })
  .limit(10)

// FAIL: BAD: Select everything
const { data } = await supabase
  .from('markets')
  .select('*')
```

### N+1 Query Prevention

```typescript
// FAIL: BAD: N+1 query problem
const markets = await getMarkets()
for (const market of markets) {
  market.creator = await getUser(market.creator_id)  // N queries
}

// PASS: GOOD: Batch fetch
const markets = await getMarkets()
const creatorIds = markets.map(m => m.creator_id)
const creators = await getUsers(creatorIds)  // 1 query
const creatorMap = new Map(creators.map(c => [c.id, c]))

const enrichedMarkets = markets.map(market => ({
  ...market,
  creator: creatorMap.get(market.creator_id)
}))
```

### Transaction Pattern

```typescript
async function createMarketWithPosition(
  marketData: CreateMarketDto,
  positionData: CreatePositionDto
) {
  // One database function call is atomic; an uncaught SQL error becomes RPC error.
  const { data, error } = await supabase.rpc('create_market_with_position', {
    market_data: marketData,
    position_data: positionData
  })

  if (error) throw new Error('Transaction failed')
  return data
}

```

SQL sketch: adapt the column names and validated DTO fields to the project's schema;
this example assumes `markets(id uuid, name text)` and `positions(market_id uuid, quantity numeric)`.
Use the project's RLS and function execution grants; do not add `SECURITY DEFINER` to bypass them.

```sql
-- SQL function in Supabase
CREATE OR REPLACE FUNCTION create_market_with_position(
  market_data jsonb,
  position_data jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
  new_market_id uuid;
BEGIN
  INSERT INTO public.markets (id, name)
    VALUES ((market_data->>'id')::uuid, market_data->>'name')
    RETURNING id INTO new_market_id;
  INSERT INTO public.positions (market_id, quantity)
    VALUES (new_market_id, (position_data->>'quantity')::numeric);
  RETURN jsonb_build_object('success', true, 'market_id', new_market_id);
  -- Let failures propagate so the caller observes error and both writes roll back.
END;
$$;
```

See [PostgreSQL error propagation](https://www.postgresql.org/docs/current/plpgsql-control-structures.html#PLPGSQL-ERROR-TRAPPING) and [Supabase database functions](https://supabase.com/docs/guides/database/functions). If an existing RPC intentionally returns a business-result union, check its success discriminator as well as the transport error.

## Caching Strategies

### Redis Caching Layer

```typescript
class CachedMarketLookup {
  constructor(
    private baseRepo: MarketRepository,
    private redis: RedisClient
  ) {}

  async findById(id: string): Promise<Market | null> {
    // Check cache first
    const cached = await this.redis.get(`market:${id}`)

    if (cached) {
      return JSON.parse(cached)
    }

    // Cache miss - fetch from database
    const market = await this.baseRepo.findById(id)

    if (market) {
      // Cache for 5 minutes
      await this.redis.setex(`market:${id}`, 300, JSON.stringify(market))
    }

    return market
  }

  async invalidateCache(id: string): Promise<void> {
    await this.redis.del(`market:${id}`)
  }
}
```

### Cache-Aside Pattern

```typescript
async function getMarketWithCache(id: string): Promise<Market> {
  const cacheKey = `market:${id}`

  // Try cache
  const cached = await redis.get(cacheKey)
  if (cached) return JSON.parse(cached)

  // Cache miss - fetch from DB
  const market = await db.markets.findUnique({ where: { id } })

  if (!market) throw new Error('Market not found')

  // Update cache
  await redis.setex(cacheKey, 300, JSON.stringify(market))

  return market
}
```

## Cache contract to verify

- Use tenant/user scope in the key when results differ by caller. A cache hit must
  not bypass authorization. Cache only the intended projection.
- Validate deserialized cache values and handle corruption according to policy.
- Define invalidation after committed writes, maximum staleness, TTL, and how
  concurrent fills behave. Five minutes in the fragment is an example, not a SLO.
- Decide whether cache outage degrades to the database or fails the operation;
  ensure fallback cannot overload the database. Bound cache-key cardinality.
- `setex` and the client constructor are version/provider specific; consult the
  installed client's API. These fragments omit connection and disposal setup.
