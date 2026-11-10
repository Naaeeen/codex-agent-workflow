# The Codex setup behind this workflow

Full reproduction now includes the isolated installer, all user Skills, controllers and pinned recipes. Start with the [full guide](full-environment.en.md). The snapshot explanations below retain their original audit scope.

This is a **2026-11-10 snapshot of inspected local configuration**, with actual role instructions, profiles, hooks, tool manifests and a runnable source package. Private directories, project references, environment values and app-generated connection details are replaced. An installed tool, an enabled configuration entry and a successful runtime invocation are different kinds of evidence.

The [Chinese guide](settings.md) contains the expanded field-by-field commentary. This English guide covers the same setup layers, reproduction steps and limitations.

## What the package contains

| Artifact | What it provides |
| --- | --- |
| [config.sanitized.toml](../config/config.sanitized.toml) | All 24 top-level keys from the actual global file, including 11 MCP entries, 17 plugin toggles, desktop preferences with private project trust entries omitted |
| [strict.config.toml](../config/strict.config.toml), [yolo.config.toml](../config/yolo.config.toml) | Actual standalone profile files |
| [agents](../config/agents/) | The four original role files, with complete instructions |
| [agents-current-schema](../config/agents-current-schema/) | Explicitly adapted versions for the current standalone custom-agent schema |
| [redaction manifest](../config/redaction-manifest.json) | Which fields were replaced and why |
| [toolkit inventory](../config/tooling/toolkit-inventory.json) | Observed versions, upstream sources, intended uses and excluded tools |
| [portable tooling](../config/tooling/README.md) | Runnable workflow sources, tests, npm lockfiles and remaining third-party installation dependencies |
| [Git hooks](../config/git-hooks/) | Actual pre-commit and pre-push scripts, provided without installing them |
| [rules inventory](../config/rules/history-inventory.json) | Exclusion and reader-side restoration notes for private command history, with separate read-only examples |

The sanitized full configuration is a comparison document, **not an overwrite-and-run installer**. Angle-bracket placeholders are literal placeholders, not automatic environment-variable expansion.

## Model, permissions and runtime precedence

The inspected global file specifies:

```toml
model = "gpt-6.1-sol"
model_reasoning_effort = "max"
model_context_window = 872000
service_tier = "default"
personality = "pragmatic"
approval_policy = "on-request"
approvals_reviewer = "auto_review"
sandbox_mode = "workspace-write"
web_search = "live"

[sandbox_workspace_write]
network_access = true

[windows]
sandbox = "elevated"
```

These values describe this installation. They do not establish that this model is best for every task, that a manually specified context size increases the model's actual capacity, or that `service_tier = default` produces a particular speed mode. Account access and client-supported model settings must be checked locally.

`on-request` and `auto_review` route eligible approval requests to automatic review. They do not remove sandbox constraints or authorize publishing. The Windows value selects an implementation; its name is not proof that all commands run as an administrator. See the official [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) and [advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced).

The host supplied different effective permissions for the session producing this package: full access / `danger-full-access` and `approval_policy = never`. That observation does not mean the global file changed. This work did not modify global settings. Session, host and managed policy must be distinguished from disk defaults.

## Profiles

The `strict` file contains only `on-request`, `read-only` and `web_search = cached`. The `yolo` file contains only `never`, `workspace-write` and `web_search = live`. Despite its name, this yolo profile does not declare an unrestricted filesystem. Neither profile changes the model; unspecified settings can inherit from the global layer, including workspace network access.

The current documented format uses `$CODEX_HOME/strict.config.toml` and `$CODEX_HOME/yolo.config.toml` with ordinary top-level keys. Select them using `codex --profile strict` or `codex --profile yolo`. Since Codex 0.134.0, nested `[profiles.name]` tables and the top-level `profile` selector are no longer the profile mechanism. The PATH CLI checked during this work reported **0.157.1**; the desktop app's embedded executor can differ. No new model session was launched to test these profiles. [Official profile documentation](https://learn.chatgpt.com/docs/config-file/config-advanced#profiles)

## Custom agents and cost choices

The original configuration declares `features.multi_agent = true`, `agents.max_threads = 6` and `agents.max_depth = 1`. Four registered roles reference external TOML files. Current documentation treats `max_threads` as a legacy concurrency alias; a host may expose a different runtime limit.

| Role | Actual instruction scope |
| --- | --- |
| explorer | Bounded codebase investigation; no edits; trace real execution paths; return files, symbols, lines and uncertainties |
| reviewer | Independently assess intended behavior, final diff and affected paths; prioritize correctness, security, regressions and missing meaningful tests |
| docs_researcher | Check current primary documentation against the requested or installed version; distinguish facts, observations and inference; no installs or external changes |
| computer_operator | Perform only the assigned UI task, read actual tool documentation, preserve open work, respect authorization and finish the tool's required handoff |

All four complete instruction blocks are included, not merely the table above. None sets `model` or `model_reasoning_effort`. Their guidance asks the parent to select an adequately capable, cheaper model or lower effort for bounded work. That instruction does not automatically route work or prove cost savings. Explicit spawn controls, inheritance and role overrides must be inspected in the actual runtime.

Three original role files contain `sandbox_mode = read-only`. **This is not evidence of an independently enforced child sandbox.** Current official documentation says `sandbox_mode`, `approval_policy`, `model_provider` and `mcp_servers` in a custom agent file do not override the parent session; service tier follows the root session. “Do not edit” remains a behavioral instruction. Enforced isolation requires real permission and tool boundaries.

Current standalone role files require `name`, `description` and `developer_instructions`. The original installation supplies description through global registration. The separate `agents-current-schema` directory adds the required metadata, preserves the full instructions and removes the misleading sandbox declaration. It does not replace the original files or pin a different model. Check actual role discovery in your own client. [Custom-agent schema](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agent-file-schema)

## MCP configuration

| Server | Transport and disk state | Relevant details |
| --- | --- | --- |
| supabase | HTTP; enabled not explicitly set | Project-scoped URL with private reference replaced; `execute_sql.approval_mode = approve` preserved. This is not an SQL read-only restriction |
| context7 | HTTP; enabled | 30-second startup; output limits 4000 for resolve-library-id and 12000 for query-docs |
| openaiDeveloperDocs | HTTP; enabled | 30-second startup; search/list/fetch/API-list limits 8000/6000/16000/8000 |
| microsoftLearn | HTTP; enabled | 30-second startup; documentation/code search limits 8000, fetch 16000 |
| exa | HTTP; disabled | Private URL withheld; not activated by this package |
| playwright | STDIO; disabled | `bunx @playwright/mcp@latest`, 30-second startup; the original latest tag is explicitly not a pinned installation |
| github | STDIO; disabled | `npx -y @modelcontextprotocol/server-github`; distinct from the GitHub connector plugin |
| memory | STDIO; disabled | `bunx @modelcontextprotocol/server-memory`; distinct from Codex memories |
| sequential-thinking | STDIO; disabled | `bunx @modelcontextprotocol/server-sequential-thinking` |
| node_repl | App-owned local STDIO; enabled not explicitly set | 120-second startup; executable, module paths, pipes, browser settings and environment values belong to the local app |
| serena | Local STDIO; enabled | 45-second startup, 90-second tool timeout; five navigation tools exposed |

The public configuration retains only endpoints matched to official sources: [Context7](https://github.com/upstash/context7), [OpenAI Docs](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Microsoft Learn](https://learn.microsoft.com/en-us/training/support/mcp) and [Supabase](https://supabase.com/docs/guides/ai-tools/mcp). Supabase's project reference is a placeholder. No private endpoint or credential value is published.

Serena exposes `initial_instructions`, `activate_project`, `get_symbols_overview`, `find_symbol` and `find_referencing_symbols`. Dashboard and GUI logging are disabled, using the included context/mode files. Full reproduction uses the pinned upstream wheel and [rebuild recipe](../environment/bundle/tooling/wheels/serena.json) to produce **2.1.0+codex.1**, checked against the original output digest. The parent environment still controls permissions.

The node_repl configuration preserves four inherited environment-variable names and 17 explicit env keys while replacing every value. These include module and executable paths, trusted code, app version, browser backends and communication pipes. Serena's `SERENA_HOME` and `PATH` values are also replaced. Let your own app create its runtime bridge; do not import another installation's pipes, identity or trust hashes.

Configured enablement, tool discovery and successful calls are separate checks. OpenAI Docs was used for the documentation verification here. This work did not authenticate or connect every MCP server, and did not execute SQL merely to populate a checklist.

## Plugins, memories and desktop settings

The two recorded local marketplaces are openai-bundled and openai-primary-runtime, with local paths replaced. All 17 plugin switches remain: documents, spreadsheets, presentations, github, linear, teams, computer-use, google-drive, openai-developers, hugging-face, chrome, pdf, template-creator, visualize, browser, unified-computer-use and codex-app-tools. This disk list is not necessarily the runtime's complete plugin catalog or proof of account authorization.

Memory flags enable generation and use; `disable_on_external_context = false` does not exclude threads simply because external context was used. Only flags are exported. No memory content was read or copied.

`notify` preserves the app bridge's `turn-ended`, `--previous-notify`, `[]` arguments while replacing the executable path. It is an app-associated notification program, not the Git hooks below. The app's desktop preferences also remain: ambient suggestions, steps/commands detail, context usage, plugged-in remote-control wake behavior, steering follow-ups, shortcut window, confetti, import sync, effort choices, empty branch prefix, avatar and editor preference. These are observed saved values, not a promise of stable public APIs.

Private project paths and per-project editor preferences are omitted, retaining empty fields. Trust your own projects deliberately. Notice and TUI onboarding state are retained for completeness, not as necessary workflow instructions. The five Windows allowed-app identifiers remain, while the browser-client trust hash is replaced. These app settings do not substitute for scoped authorization to act.

## CLI tools and reproducibility

The [inventory](../config/tooling/toolkit-inventory.json) records every tool and all 31 original launcher routes. Major groups are:

- Structural inspection: ast-grep 0.51.1, Repomix 1.18.1, REA 6.8.0 and patched Serena. Use ordinary targeted search before heavier indexing or repository packaging.
- Task and environment management: Beads 1.3.4, Worktrunk 0.81.0, mise 2026.11.1 and pixi 0.84.1. Preserve an existing project tracker and package manager.
- Retrieval and graphs: QMD 2.8.3 and GitNexus 1.6.12. Index only explicitly selected material. GitNexus's recorded noncommercial license remains relevant. CodeGraphContext 0.6.13 is explicitly held out of the default workflow because the local catalog records correctness/boundary issues.
- Documents and analysis: Docling 2.147.0, pdfplumber 0.11.9, marimo 0.25.2, Inspect AI 0.3.287, DuckDB 2.0.0, Hyperfine 2.0.0, Typos 1.52.0, Lychee 0.24.2 and Trafilatura 2.3.1.
- Integration and experiments: MCP Inspector 2.14.0, locally modified Semgrep 1.183.0+local.security1, Playwright CLI 0.1.23, agent-browser 0.41.2 and pi-coding-agent 1.5.0. The browser and pi experiments are not equivalent to the host UI tool or the current chat model.

Six npm projects include their actual paired package.json/package-lock.json, including dependency overrides. Five Python lockfiles are included. Versions are installation-manifest or lock observations; this work did not reinstall every dependency or repeat a full vulnerability audit. Binaries, virtual environments, model weights, indexes, the patched Serena wheel and Semgrep patch build are not distributed. Several specialized experimental controllers remain reference dependencies, explicitly listed in the [tooling guide](../config/tooling/README.md).

The original 31-route launcher is named `agent-tool.reference.ps1` because its dependencies are not all bundled. The new **workflow-tool.ps1 exposes only seven source-complete routes**:

| Route | Purpose and limit |
| --- | --- |
| task | Evidence ledger, revisions, checkpoints and completion checks; cannot prove evidence honesty or reviewer independence |
| improvement-verify | Validate the structure and declared evidence of an improvement bundle; does not prove the improvement works |
| eval | Eight synthetic artifact tasks with prompts, fixtures, graders and goldens; controller does not invoke a model |
| observe | Observe an explicitly supplied native CLI; real execution can consume resources and requires authorization |
| eval-native | Join synthetic tasks, observer and grader; explicit execution gate, no silent model dispatch |
| handoff | Package selected files with integrity checks; not remote execution or complete secret detection |
| execution-plan | Recommend local/cloud/hybrid from supplied facts; advice is not authorization or dispatch |

From the workflow-kit directory, start with:

```powershell
pwsh -NoProfile -File config/tooling/workflow-tool.ps1 --help
pwsh -NoProfile -File config/tooling/workflow-tool.ps1 task --help
pwsh -NoProfile -File config/tooling/workflow-tool.ps1 eval selftest
python -B config/tooling/harness/evals/verify.py
```

Use Python 3.11+, and Node/PowerShell for the relevant synthetic cases. Use a physical directory rather than a Windows junction alias: source integrity guards intentionally reject some reparse paths. Source hashes and documented adaptations are in [harness-source-map.json](../config/tooling/harness-source-map.json); the native bridge now loads the sibling packaged eval directory instead of a personal home installation.

## Hooks, command rules and checks

The actual global Git hooks include a staged-added-lines secret-pattern check and a pre-push verification runner. Pre-commit suppresses matched credential contents and fails on scan errors, but skips several binary/lockfile categories and supports explicit bypass controls. It is not exhaustive secret prevention.

Pre-push chooses the project's declared package manager or lockfile, then runs existing lint/typecheck/test/build scripts. Dependency audit is opt-in via `ECC_PREPUSH_AUDIT=1`. Go and Python checks depend on available runtimes; missing pytest is reported as skipped. Pure branch deletion is skipped. The scripts are supplied without altering global hooksPath.

Codex command rules are separate. The 113 historical prefix rules contain project-specific and one-off permissions, so their original argument values are withheld. The package preserves decision, argument count, executable family and pattern hash, plus separately labeled read-only examples. No history-derived allowlist is silently installed. No global hooks.json or inline hooks table was found in the selected locations; that does not audit every plugin's hooks. See the distinct official [lifecycle hooks](https://learn.chatgpt.com/docs/hooks) mechanism.

The package completed **134 unit tests: 132 passed and two symlink tests were skipped** because this Windows context cannot create those links; separate junction tests ran. Eight cases with four calibration variants each were checked. Executable-line coverage was 91.4% for the runner and 92.3% for graders, not branch coverage. All seven route help calls, multiword task initialization and unknown-tool rejection were exercised. Tests used fake observer/CLI implementations, with zero real model calls. [Current verification](../config/tooling/verification.json)

Initial failures were preserved in that record: a junction alias was correctly rejected; an overbroad UUID redaction initially erased a case-sensitivity negative control; and review caught single-argument PowerShell splatting. The physical-directory run, corrected synthetic UUID and explicit array handling resolved these without weakening the guards. Historical implementation notes are labeled separately from the new package run.

To reproduce the useful parts, first run the packaged source tests, then merge selected settings into a backed-up configuration, verify role discovery, install only needed pinned tools, and connect services using your own official configuration and credentials. Finally run one real task with explicit acceptance criteria. This snapshot does not establish general model-quality gains, all-service connectivity, every third-party tool's behavior, cloud readiness or human A/B outcomes.
