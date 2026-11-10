---
name: api-design
description: Design or review HTTP API contracts, including resources, methods, statuses, response schemas, pagination, filtering, rate-limit responses and compatibility. Server layering and security scans use focused skills.
---

# HTTP API contracts

Use this skill for the observable contract between a client and server. Preserve
the project's existing conventions unless the task calls for a deliberate change.

## Working approach

1. Identify callers, current endpoints/schema, authentication transport and
   compatibility constraints before changing a contract.
2. Specify request fields, constraints, success/failure responses and repeated
   request behavior. Include examples only where they resolve ambiguity.
3. Read the relevant reference below; choose conventions from the real client
   needs rather than copying an example envelope or version policy.
4. Update the existing API specification and verify contract tests for changed
   behavior, including malformed requests and authorization failures.

## Read only what is needed

- Resource/method/status, response/error shape and access contract:
  [HTTP contracts](references/http-contracts.md).
- Collection limits, cursor/offset, query fields or ordering:
  [pagination and query](references/pagination-and-query.md).
- Rate-limit headers or breaking-change rollout:
  [limits and compatibility](references/limits-and-compatibility.md).
- Mapping an agreed contract to an existing route implementation:
  [adapter examples](references/adapter-examples.md).

## Contract invariants

- Keep safe methods free of state changes. Distinguish authentication,
  authorization, validation, conflict and internal failure outcomes.
- Define deterministic collection ordering, bounded page size and allowed query
  fields; specify the consistency clients can actually expect.
- State which fields a caller may read/write. Use explicit response projections,
  and avoid revealing internal exceptions or another caller's resource existence.
- Document idempotency and retry behavior for operations with side effects.
- Evolve contracts according to actual client compatibility and deprecation needs;
  do not assume an added field is harmless to every strict client.

## Responsibility boundaries

- Service/repository layering, queue durability and limiter implementation:
  `backend-patterns`.
- Changed authentication, authorization, uploads or sensitive-data boundaries:
  `security-review`; requested vulnerability audits use `codex-security`.
- Provider setup, such as Supabase or Vercel-specific APIs, uses its dedicated
  skill. API examples here do not choose or install a provider.

See [provenance and example status](references/provenance.md).
