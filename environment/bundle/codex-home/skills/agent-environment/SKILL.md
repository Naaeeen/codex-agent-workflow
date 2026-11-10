---
name: agent-environment
description: Audit, upgrade, or repair this user's local Codex skills, MCP configuration, agent roles, and pinned tool installation.
---

# Maintain the agent environment

Use for local Codex configuration and toolchain work. Application debugging belongs
to the application's own workflow. Consult current OpenAI Docs and installed CLI
help before changing a version-sensitive setting.

The local toolkit is `{{CODEX_HOME}}\tools\agent-kit`. Its
`env_audit.py` uses the Python standard library; see `--help` for the current CLI.
Audit output intentionally omits configuration values. Do not read auth files,
session databases or private chat history to inventory tools.

1. Record the requested outcome and inspect the current effective tool catalog,
   relevant config, instructions, installed versions and overlapping capabilities.
   Cached plugins are not proof of active tools. A parsed TOML is not proof of
   client support. A reachable endpoint is not proof the active session loaded it.
2. Compare material alternatives against a real task. Prefer native tools and
   focused additions; avoid duplicate frameworks, blanket skill installs, floating
   executable versions and global PATH/runtime replacement.
3. Before a write, back up the exact affected files and their hashes. Keep package
   versions, source URLs, licenses, integrity/lockfile and any local overrides.
   Preserve model, permissions, auth, memory and unrelated project settings.
4. Verify syntax and actual operation, including one relevant failure case; audit
   dependencies and obtain independent review for consequential changes. Do not
   install a provider just because another tool's setup suggests it.
5. Report applied vs staged changes, measured results, restart/new-session needs,
   rollback path and untested capabilities. Never translate tool count, stars or
   a small smoke test into a general intelligence/accuracy claim.

For this installation, the three public documentation MCPs are OpenAI Docs,
Microsoft Learn and Context7. Send only sanitized public documentation queries.
Their servers are remotely managed; local package pins cannot freeze their
versions. Existing GitHub/Office/browser tools usually cover those integrations.

`snapshot`/`rollback` handle explicitly listed files only, not installed directory
trees. Rollback validates all expected hashes before writing; it is not atomic
against concurrent writers or crashes. Close other config writers first and
inspect conflicts instead of forcing an overwrite. Keep backups outside outputs.

For native CLI execution/recovery diagnostics, the local eval-harness reference
documents metadata-only observation. Preserve its distinction between an
invocation result, a thread usage snapshot and an artifact grader. Validate a
profile on its real task before recommending it; do not assume fewer servers
always improve speed or context use.

For machine-specific compatibility warnings, read [dated local runtime notes](references/local-runtime.md) and verify them again before changing settings.

The pinned utility kit adds DuckDB, Hyperfine, Typos, Lychee and Trafilatura to
the same launcher, plus pdf-layout for qualified text-PDF reading order.
Use their focused workflow references, not every tool for every task.
See [tool output contracts](references/tool-output-contract.md) for per-tool
budgets, filtering and recovery from incomplete results.

Additional qualified workflows now use GitNexus (eligible noncommercial graph
analysis), Beads/Worktrunk (dependent work and isolated checkouts), QMD (selected
local knowledge), mise/pixi (project environments), Inspector (MCP checks), and
local Semgrep CE. Use the focused skills and the shared launcher. The experimental
CodeGraphContext installation is not qualified for default graph/impact use.
Read [workflow selection](references/workflow-selection.md) when choosing lanes.

For a substantive repeated harness issue, retain the baseline and an experiment
bundle before promoting a general rule. The installed improvement-verify route
checks declared evidence dependencies; eval-harness describes the comparison.
Use direct checks for simple edits. This does not enable background self-updates.

For multi-environment work, execution-routing connects local/WSL work with a
ready authorized cloud environment using portable task/output contracts. For
cross-service work, connected-workflows selects existing document, mail,
calendar and project tools. Browser automation has a qualified local pw route.
Pi is installed as an optional offline SDK lab, not a replacement primary agent.
