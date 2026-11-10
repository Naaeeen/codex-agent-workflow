---
name: reverse-engineer-anything
description: Inspect shipped binaries, archives, Electron/JavaScript packages, or recorded runtime evidence with the locally installed REA toolkit; skip ordinary source-repository analysis.
---

# REA local adapter

Use REA when the question depends on a shipped artifact or requested runtime
evidence. Start with the caller's explicit target and an operation that answers
the question with the least side effect. Normal source navigation belongs to
repository tools.

Pinned Windows launcher:
`{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1`

```powershell
& '{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1' rea --version
& '{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1' rea analyze-javascript-application 'C:\path\owned-app' --format json
& '{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1' rea inspect-artifact 'C:\path\package.zip' --format json
```

Read command help/schema before choosing flags. Preserve complete evidence in
the task's scratch directory; return a compact finding with its source, digest,
limits and evidence path. Static inspection does not establish runtime behavior;
decompiler output and reconstruction are inferences, not original source.

The complete upstream workflow ships at
`{{CODEX_HOME}}\tools\agent-kit\node_modules\rea-agents\skills\reverse-engineer-anything\SKILL.md`.
Read that entrypoint only for an actual REA task, then the relevant linked
reference. The local launcher replaces upstream `npx` examples; do not run setup,
update, install a provider or replace global configuration as an incidental step.
Existing scoped authorization still applies; do not ask again just because an
upstream example asks for confirmation.

This kit has REA CLI installed. Its large MCP catalog is not globally enabled.
Windows JavaScript/static artifact inspection has a local smoke test; Ghidra/JDK,
IDA, Hopper, JADX, Frida, runtime attachment and device operations have not been
installed or qualified. A missing backend limits that route, not all REA routes.
Inspect `capabilities` when availability is material; do not run diagnostics on
every task. Do not silently substitute a different target or claim unavailable
analysis completed. Native target execution, attachment and mutations require
authorization covering their actual side effects.
