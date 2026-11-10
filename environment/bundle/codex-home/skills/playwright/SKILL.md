---
name: "playwright"
description: "Automate a browser with an existing Playwright CLI or a deliberately selected task-scoped CLI setup. Use for terminal browser workflows; prefer the host browser tools, configured MCP, or existing test framework when they already provide the required capability."
---


# Playwright CLI Skill

Drive a real browser using the capability available for the task. Reuse the host browser tool, configured Playwright MCP, or project test runner when it already fits; their syntax and sessions differ from this CLI. Use this skill's CLI recipes when Playwright CLI is the chosen interface.

## Runtime selection

1. Check the active environment and existing browser/test tooling. Reuse installed compatible executables and the project's package manager; do not assume Unix shell syntax works in PowerShell.
2. If `playwright-cli` is installed, inspect its version/help and use that executable. If the project already has Playwright tests, extend/run them when persistent regression coverage is needed.
3. If no CLI exists, use an available browser/MCP capability rather than making Node/npm installation a universal prerequisite. Only choose a CLI installation when it adds a capability the task needs; use a compatible scoped version.
4. The bundled [scripts/playwright_cli.sh](scripts/playwright_cli.sh) runs `npx --yes --package @playwright/cli playwright-cli`, which may download and execute an unpinned package. Do not use it as the default or treat `--yes` as authorization. For a specifically chosen temporary CLI, use a task-local reviewed launcher or install with an explicit verified package version; never silently install globally.

## CLI examples

Examples below assume `PWCLI` resolves to an already available, selected CLI executable or reviewed launcher in the active environment. Resolve its real path first; do not redefine `CODEX_HOME` or infer a Windows path for WSL. The optional Bash wrapper needs both Bash and npx, but missing either does not block other browser capabilities.

```bash
"$PWCLI" open https://playwright.dev
"$PWCLI" snapshot
"$PWCLI" click e15
"$PWCLI" type "Playwright"
"$PWCLI" press Enter
"$PWCLI" screenshot
```

Keep task sessions and artifacts scoped to the workspace. Use headed mode only when the task requires a visible browser; screenshots can support visual inspection in headless mode too.

## Core workflow

1. Open the page.
2. Snapshot to get stable element refs.
3. Interact using refs from the latest snapshot.
4. Re-snapshot after navigation or significant DOM changes.
5. Capture artifacts (screenshot, pdf, traces) when useful.

Minimal loop:

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" snapshot
```

## When to snapshot again

Snapshot again after:

- navigation
- clicking elements that change the UI substantially
- opening/closing modals or menus
- tab switches

Refs can go stale. When a command fails due to a missing ref, snapshot again.

## Recommended patterns

### Form fill and submit

```bash
"$PWCLI" open https://example.com/form
"$PWCLI" snapshot
"$PWCLI" fill e1 "user@example.com"
"$PWCLI" fill e2 "password123"
"$PWCLI" click e3
"$PWCLI" snapshot
```

### Debug a UI flow with traces

```bash
"$PWCLI" open https://example.com --headed
"$PWCLI" tracing-start
# ...interactions...
"$PWCLI" tracing-stop
```

### Multi-tab work

```bash
"$PWCLI" tab-new https://example.com
"$PWCLI" tab-list
"$PWCLI" tab-select 0
"$PWCLI" snapshot
```

## References

Open only what you need. The runtime selection above governs these legacy reference recipes too; their wrapper/global-install suggestions and repository-specific output paths are examples, not prerequisites:

- CLI command reference: `references/cli.md`
- Practical workflows and troubleshooting: `references/workflows.md`

## Guardrails

- Always snapshot before referencing element ids like `e12`.
- Re-snapshot when refs seem stale.
- Prefer explicit commands over `eval` and `run-code` unless needed.
- When you do not have a fresh snapshot, obtain one before acting. Placeholder
  refs belong only in illustrative documentation and must not be executed.
- Choose headless or headed mode deliberately; do not launch an unsolicited visible helper window on Windows.
- Put temporary browser artifacts in the current task's scratch/output locations, following the project and host conventions.
- Use CLI recipes for one-off browser interaction. Use existing project tests when the task calls for repeatable regression coverage; verify current commands against the selected installed version.

## Qualified local CLI entry

This machine now has a pinned isolated route:
`agent-tool.ps1 browser pw ABSOLUTE_WORKSPACE SESSION open URL`.
Use the same workspace/session for snapshot and subsequent commands; close the
owned session in finally. The optional `ab` route has known download and error
reporting gaps and is not the default. Read
[local browser routing](references/local-browser-routing.md) before first use.
