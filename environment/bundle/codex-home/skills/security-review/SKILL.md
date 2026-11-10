---
name: security-review
description: Review the security boundaries affected by an implementation change, such as authentication, authorization, untrusted input, uploads, secrets or sensitive data. Use codex-security for repository/diff vulnerability scans and dedicated provider skills for setup.
---

# Affected-boundary security review

Use this skill while implementing or checking a change with a concrete trust or
sensitive-data boundary. It is focused engineering guidance, not a certification
or a requirement to audit unrelated parts of the repository.

## Working approach

1. Identify changed entry points, attacker-controlled values, protected resources
   and the trusted context needed to authorize the action.
2. Read only the matching reference below. Follow the project's security policy
   and existing framework/provider mechanisms.
3. Trace values through validation, authorization, storage and output; test the
   relevant denial/failure paths as well as the authorized path.
4. Report concrete findings, fixes and evidence with file/line context. Separate
   a plausible concern from a reproduced failure and state verification gaps.

## Choose the affected boundary

- Authentication, access checks, browser/native sessions or CSRF:
  [identity and sessions](references/identity-and-sessions.md).
- Input, queries, uploads, HTML output or CSP:
  [input and output](references/input-and-output.md).
- Secrets, logs, abuse limits, dependencies or deployment review:
  [operational checks](references/operational-checks.md).
- Only for actual wallet-signing/transaction changes:
  [wallet contracts](references/wallet-contracts.md).

## Boundaries that always matter within scope

- Derive requester identity from verified server/provider context. Apply the
  required action, resource and tenant policy before exposing data or mutating it.
- Validate untrusted input at the receiving boundary; use parameterized values
  and explicit output projections. Do not treat client validation as authorization.
- Keep secrets and sensitive data out of source, public responses and logs.
  Use the existing secret store and redaction mechanisms.
- Browser cookies, browser-held bearer tokens and native credential storage have
  different risks; choose controls from the real client and transport model.

## Routing and completion

- Requested repository or diff vulnerability scans: select the corresponding
  `codex-security:security-scan` or `codex-security:security-diff-scan` workflow.
  Explicit vulnerability fixes/verification use their focused workflows.
- Supabase auth, RLS or SDK behavior: use the dedicated Supabase skill. Do not
  copy generic RLS snippets into a project as a complete access policy.
- HTTP error/limit contract: `api-design`; operational implementation:
  `backend-patterns`. This review adds no unrelated services or approval gates.

See [provenance and example status](references/provenance.md).

For a relevant local source/sink rule, the pinned `agent-tool.ps1 semgrep` lane
adds deterministic CE taint checks with local YAML rules only. See
[local taint checks](references/local-taint-checks.md). It supplements source
review and tests; it does not replace the Codex Security scan workflow.
