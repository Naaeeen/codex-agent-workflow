---
name: coding-standards
description: Apply cross-project naming, readability, type-safety and maintainability conventions during implementation or code-quality review. Framework architecture and security reviews use their focused skills.
---

# Coding conventions

Use the project's existing style and tools as the baseline. This skill owns
language-level readability and maintainability; it does not prescribe a stack.

## Working approach

1. Read the touched code, applicable instructions and existing lint/type rules.
2. Make the smallest cohesive change that expresses the intent clearly.
3. Keep names, types and error behavior consistent with adjacent code.
4. Use the project's relevant checks; report actual results and remaining gaps.

## Shared conventions

- Prefer descriptive names and direct control flow. Explain non-obvious reasons
  or constraints in comments; avoid narrating syntax.
- Prefer immutable updates for shared state. Local mutation is reasonable when
  ownership is clear and the choice improves simplicity or measured performance.
- Model valid states in types; narrow untrusted values instead of casting them
  into trusted types. Avoid `any` when an accurate type or `unknown` will work.
- Validate external data and permissions at real trust boundaries, then rely on
  established internal contracts. Do not repeat the same checks in every helper.
- Preserve useful error context and the caller's failure contract. Add a guard,
  fallback, retry or catch for an identified case; do not turn failures into empty
  or successful defaults, or wrap/log/rethrow at every layer by habit.
- Extract duplication when the shared concept is stable. Avoid speculative
  abstractions, fixed function-size rules and refactors unrelated to the request.
- Parallelize independent work only; preserve ordering and cancellation semantics
  when operations depend on each other.

Read [conventions and examples](references/conventions.md) only for concrete
naming, updates, comments, type, error, async or test-structure guidance.

## Responsibility boundaries

- React/state/rendering implementation: `frontend-patterns`.
- Server application layers and operational behavior: `backend-patterns`.
- HTTP resource and response contracts: `api-design`.
- Changed trust boundaries: `security-review`; repository vulnerability scans
  belong to the appropriate `codex-security` workflow.
- Use the project's testing workflow for behavior changes; this skill adds no
  universal test count, coverage target, architecture or dependency requirement.

See [provenance and example status](references/provenance.md).
