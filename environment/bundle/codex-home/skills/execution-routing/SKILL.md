---
name: execution-routing
description: Choose local, WSL, cloud or hybrid execution for a substantial task and prepare verified handoffs. Use when remote execution or parallel local/cloud work would help; do not treat installed cloud tools as a ready environment.
---

# Local and cloud execution routing

Choose the execution location from the task, not a fixed repository or model.
Keep live desktop/browser sessions, local private state and Windows-specific work
local. Consider cloud for a separable, Linux-reproducible build/test/analysis unit.
Use hybrid execution when local investigation and an independent remote unit can
run together. Small tasks need no handoff ceremony.

Read {{CODEX_HOME}}\workflow\execution-policy.json for current preferences.
The user prefers Codex Cloud; Vercel currently permits preparation only. Refresh
real service/environment state before execution; the saved capability record is
a dated inventory, not permission or availability proof.

For Codex Cloud, discover published environments with available native tools and
match the current project's remote/revision. Do not ask the user to pick a cloud
for every task if an already authorized matching environment exists. Reuse scoped
authorization, but do not invent environment IDs or assume different API/CLI ID
types are interchangeable. If no suitable environment exists, continue local
work and identify the one-time project setup needed. Do not use a user-owned new
chat as an internal subagent when the host prohibits that operation.

For a remote unit, create a minimal explicit input allowlist or exact Git base
plus reviewed patch. Do not copy .codex, auth files, browser cookies, whole home
directories or unrelated documents. The shared launcher provides `handoff` for
pack/verify/extract/collect and `execution-plan` for pure routing advice. The
planner never grants permission or starts a remote job.

Inspect the runtime recipe, command argv, time/resource limits, network policy,
authorized output paths and budget. Large codebases usually fit exact Git revision
handoff better than the bounded JSON file bundle. See
[provider workflow](references/providers.md) for current execution distinctions.

Record a remote task ID with the parent acceptance checks to avoid duplicate
dispatch. Keep independent local work moving. On return, validate the package or
patch/base/path scope, use an isolated worktree and run relevant local checks.
A remote success message alone cannot complete the parent task. Never auto-push,
publish or send results to others without the corresponding authorization.
