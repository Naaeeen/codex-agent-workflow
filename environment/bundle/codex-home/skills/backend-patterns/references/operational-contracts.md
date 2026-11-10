# Operational contracts

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

## Error propagation

Map expected domain outcomes at the transport boundary to the established API
contract. Unexpected failures receive a generic public error plus an internal
correlation ID. Log once at an appropriate boundary using approved redaction;
do not assume an arbitrary exception message is safe for a response or log.

## Bounded retries

Retry only classified transient failures of operations safe to repeat, or writes
protected by an idempotency contract. Define a positive attempt count, overall
deadline, per-attempt timeout, cancellation, capped backoff with jitter, and any
provider `Retry-After` handling. Preserve the final cause. Do not retry validation,
permission failures or unknown writes simply because they threw an exception.

## Rate-limit enforcement

The old raw `x-forwarded-for` plus an unbounded process-local Map is intentionally
removed. A production enforcement design must establish:

- **Identity:** authenticated principal/API-key identifiers from trusted context;
  anonymous client address only through the verified proxy topology. An arbitrary
  incoming `X-Forwarded-For` value is not a trusted identity.
- **Topology:** the proxy overwrites forwarded headers and the framework trusts
  only the configured proxy/hops; test direct and alternate routing paths.
- **Store:** atomic counters/windows shared across relevant workers/regions, with
  bounded key cardinality, expiry/eviction, and explicit outage behavior.
- **Policy:** cost-aware limits, burst/window semantics, concurrency controls where
  needed, and the advertised retry contract in `api-design`.
- **Evidence:** forged headers, concurrent requests, expiry, unique-key pressure,
  multiple workers and store outage tested under the actual topology.

A bounded in-process limiter can be a deliberately local development control; it
must not be presented as distributed enforcement. Use the installed library and
provider docs, such as [Express proxy trust](https://expressjs.com/en/guide/behind-proxies/).

## Jobs and queues

The prior array-backed `JobQueue` lost work on restart and returned success before
durable acceptance. Choose an existing queue only when the use case needs it.
Define these contracts before replying that a job was accepted:

- Validate and authorize the target before enqueueing. Persist the required job
  data or an appropriately scoped reference, not transient request context.
- Define durable acceptance, deduplication/idempotency, retry bounds, poison-job
  handling, acknowledgement and shutdown behavior.
- Bound queue size and worker concurrency; define backpressure and cancellation.
- Assume redelivery unless the provider proves stronger semantics; make side
  effects idempotent or coordinate them transactionally.
- Test restart after acceptance, failure before/after a side effect, retry
  exhaustion and duplicate delivery. A mock queue does not prove durability.

## Structured logging

Use the project's logger with level, event, timestamp and trusted correlation ID.
Whitelist useful fields; never spread an arbitrary request or context into the
log record. Redact credentials and personal data. Request IDs supplied by a client
are untrusted input and need appropriate validation or replacement.

```typescript
// Illustrative event shape, not a logger or logging configuration.
interface RequestEvent {
  readonly event: 'market.list.completed' | 'market.list.failed'
  readonly requestId: string
  readonly durationMs: number
  readonly status: number
}
```

The removed retry/limiter/queue/logger shortcuts are represented by contracts
because their safe implementation depends on the project's libraries and runtime.
