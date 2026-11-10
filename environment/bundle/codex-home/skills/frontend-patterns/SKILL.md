---
name: frontend-patterns
description: Implement React or Next.js component composition, state, effects, forms and rendering behavior using the existing stack. Use frontend-design for visual direction and the installed React review skill for post-edit review.
---

# Frontend implementation patterns

Use this skill when choosing or changing frontend behavior. Start from existing
components and framework conventions; do not introduce another state/query library
merely because an example uses one.

## Working approach

1. Trace the user action through component state, data loading and rendering.
2. Identify ownership: local UI state, shared client state, server state or URL.
3. Read the relevant reference below and adapt the smallest fitting pattern.
4. Verify the changed interaction, including pending, empty and failure states,
   in the project's checks and a real browser when available.

## Read only what is needed

- Component APIs, composition, context or reducers:
  [components and state](references/components-and-state.md).
- Effects, cancellation, asynchronous loading or debounce:
  [effects and data](references/effects-and-data.md).
- A demonstrated rendering or bundle bottleneck:
  [performance](references/performance.md).
- Form behavior, error boundaries, motion or accessible interactions:
  [forms and interaction](references/forms-and-interaction.md).

## Implementation constraints

- Derive values from existing state when possible. Effects synchronize external
  systems; they are not a default way to derive render data.
- Preserve keyboard operation, accessible names, focus behavior and semantic HTML.
  A visual example is not proof of an accessible widget.
- Treat browser-visible data as public to that user. Use synthetic examples,
  redact sensitive logs, and keep authorization and authoritative validation on
  the server. Add third-party tracking only within the user's authorized scope.
- Confirm version-sensitive React/Next.js APIs against the installed version
  and current primary documentation when an implementation depends on them.

## Responsibility boundaries

- Visual direction or substantial styling: `frontend-design`.
- Post-edit React/TSX review: the installed `vercel:react-best-practices` skill;
  specialized composition/performance skills only when that concern applies.
- HTTP contracts: `api-design`; server layers: `backend-patterns`.
- Authentication, uploads or sensitive data changes: `security-review`; use the
  dedicated Supabase skill for Supabase integrations.

See [provenance and example status](references/provenance.md).
