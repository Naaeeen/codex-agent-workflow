---
name: project-workflow
description: Coordinate dependent repository tasks and isolated Git worktrees with installed Beads and Worktrunk for multi-part implementation. Preserve an existing project tracker; skip for small self-contained edits.
---

# Dependent work and isolated checkouts

Use the pinned launcher at {{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1.
Use native subagents for execution; these tools manage local state and checkouts,
not model selection or permission. Inspect project guidance, Git status and any
existing tracker before initializing anything.

For parallel edits, use `worktrunk switch --create BRANCH --no-hooks --format json`
from the selected repository. The wrapper isolates tool config and inherited
overrides. The command creates/selects a worktree; this launcher does not change
the parent agent's cwd. Read its path result and use that explicit workdir for
the assigned worker. Give each worker file ownership and preserve other edits.
Use `worktrunk list --format json` to inspect status. Do not force-remove a dirty
worktree or enable hooks/LLM commit generation merely to finish cleanup.

For a project explicitly using a dependency tracker, use Beads. If adopting it is
part of the task, initialize only the authorized repo/checkout with
`beads init --prefix PREFIX --skip-agents --skip-hooks --non-interactive --role maintainer`.
Initialization writes a project database and may create a local Git commit;
inspect staged changes and use an owned checkout so unrelated work is preserved.
`beads create TITLE --id ID --type task --description TEXT --json` creates a task;
`beads dep add BLOCKED_ID PREREQUISITE_ID --json` records an edge. Use ready/blocked
to choose runnable work and close only after its acceptance evidence is verified.
Do not replace the existing task ledger's evidence/review completion gates.

Always use the wrapped `beads` route: usage metrics, background flush and the
separate OpenTelemetry SDK are disabled there. It does not install project hooks
or auto-push. Beads is durable task state, not a proof that work is correct.
The dependency/claim tests are small local fixtures, not a distributed stress test.

Sources: https://github.com/gastownhall/beads ; https://github.com/max-sixty/worktrunk
