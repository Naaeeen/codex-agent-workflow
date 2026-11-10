---
name: backend-patterns
description: Structure server application layers, data access, caching, jobs, middleware and operational error handling in an existing backend. API contracts, provider-specific setup and security scans use focused skills.
---

# Backend application patterns

Use this skill for how a server implements a use case. Keep the project's existing
framework and layering; introduce abstractions only for a concrete responsibility.

## Working approach

1. Trace request or job entry through authentication context, business rules,
   data access and side effects; identify the transaction and failure boundaries.
2. Choose the relevant reference below. Preserve existing public contracts.
3. Make dependencies, resource limits and error propagation explicit.
4. Verify affected success and failure paths using the actual database or service
   boundary where available; distinguish mocks from integration evidence.

## Read only what is needed

- Repository/service responsibilities: [application structure](references/application-structure.md).
- Query shape, transactions and cache behavior: [data and caching](references/data-and-caching.md).
- Trusted principal handoff and request middleware:
  [identity and middleware contracts](references/identity-and-middleware.md).
- Retries, rate-limit enforcement, queues or logs:
  [operational contracts](references/operational-contracts.md).

## Server invariants

- Keep business rules independent of transport details when that makes the
  touched use case easier to verify. Avoid ceremonial layers for trivial work.
- Make writes atomic at the required boundary. Define repeated-request and
  retry behavior before adding a retry loop or background job.
- Bound work, memory and concurrency. Process-local state does not provide
  distributed consistency or durability across restarts.
- Keep cache keys and authorization scopes aligned, and define invalidation.
- Pass one verified principal shape through middleware and services; do not
  reconstruct identity from caller-supplied IDs or incompatible token casts.

## Responsibility boundaries

- Resource URLs, HTTP statuses, pagination and compatibility: `api-design`.
- Authentication validation and changed trust boundaries: `security-review`;
  repository/diff vulnerability scans use `codex-security` workflows.
- Supabase operations, auth/RLS and database setup: the dedicated Supabase skill;
  use its Postgres guidance for provider-specific query/schema decisions.
- Deployment-provider APIs and durable queues use the installed provider skill
  only when that provider is part of the actual project.

See [provenance and example status](references/provenance.md).
