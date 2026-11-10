# Full environment reproduction

[简体中文](full-environment.zh-CN.md)

This package restores the shareable settings, 62 user Skills, four roles, controllers, harness source and dependency recipes in a separate directory. The dependency reference targets Windows x64. Files are checked against a manifest, dependencies come from pinned artifacts, and each installed group gets an integrity receipt.

## Prepare

1. Back up projects and existing agent configuration outside the repository. Confirm recovery is possible.
2. Provide Git, PowerShell 7 and Python. The dependency set uses official Windows x64 [Python 3.13.7](https://www.python.org/downloads/release/python-3137/) and [Python 3.14.3](https://www.python.org/downloads/release/python-3143/).
3. Rebuilding exact original wheel bytes also requires the recorded compression runtime. Serena uses Python 3.14.3 with zlib `1.3.1.zlib-ng`; Semgrep uses Python 3.13.7 with zlib `1.3.1`. Preflight stops on a mismatch.
4. Choose a new directory under an existing parent, outside a Git checkout. Keep the original environment.

Model assets total approximately 3 GB, with additional space for programs and Python/npm dependencies. Check interpreter metadata with:

If `py -3.13` or `py -3.14` selects another patch release, pass the exact required interpreter's full `python.exe` path to `-Python313` or `-Python314`. Preflight checks the version before installation.

```powershell
py -3.13 -c "import sys,zlib; print(sys.version.split()[0], zlib.ZLIB_RUNTIME_VERSION)"
py -3.14 -c "import sys,zlib; print(sys.version.split()[0], zlib.ZLIB_RUNTIME_VERSION)"
```

## Restore in three stages

- **Preview and stage files.** `reproduce.py` checks files and paths, renders explicit placeholders, and creates the separate Codex home, initial project and launcher. Preview is the default.
- **Restore dependencies.** `install_dependencies.py` processes selected groups in dependency order, verifies download hashes, safely extracts archives, disables npm lifecycle scripts and creates separate Python venvs. Reviewed GitNexus native activation and exact wheel rebuilding have explicit rules.
- **Connect your accounts and host.** Sign in through the new launcher, then complete your client, plugins and project parameters below.

Select groups to start smaller. Their prerequisites are included.

```powershell
$py313 = py -3.13 -c "import sys; print(sys.executable)"
$py314 = py -3.14 -c "import sys; print(sys.executable)"

pwsh -NoProfile -File ./setup.ps1 -Destination ../my-codex-environment `
  -Group codex-cli,npm-agent-kit,python-harness-python

pwsh -NoProfile -File ./setup.ps1 -Destination ../my-codex-environment `
  -Python313 $py313 -Python314 $py314 `
  -Group codex-cli,npm-agent-kit,python-harness-python -Apply
```

Omit `-Group` for all automatic groups. `-SkipModelWeights` defers only `qmd-models` and `docling-models`. Add them when needed. Group IDs and versions are in the [dependency manifest](../environment/dependencies.json).

## Restoration coverage

| Component | Handling |
| --- | --- |
| Model, effort, search and permission defaults | Restored in portable configuration. Host/session overrides still apply, and the selected model must be available to your account |
| 62 user Skills | Installed under the new `CODEX_HOME/skills`, retaining adaptations and licenses with selected path templates |
| System Skills and 17 recorded hosted plugins | Reinstall through your own official client and plugin directory. Use the [host reference](../environment/bundle/tooling/host-settings.reference.json). The client generates its own bridges and caches |
| Public documentation MCP | Context7, OpenAI Docs and Microsoft Learn are configured. Confirm tool discovery and run a public documentation query |
| Serena MCP | Uses its pinned dependency group and relocated navigation configuration |
| Supabase, Exa and other account services | Supply your own project parameters and credentials. Incomplete services stay disabled until you choose to configure them |
| Browser | Isolated automation uses pinned Chromium. Your signed-in tabs use your client's own browser connection |
| Recorded disabled STDIO MCP entries | Legacy Playwright, GitHub, memory and sequential-thinking remain disabled. Some use `bunx`, requiring Bun only if you choose to enable them. Restored Playwright CLI and Chromium are a separate route |
| Git hooks | Source and notices are included. Inspect existing hooks before setting project-local `core.hooksPath`, and retain the prior setting for recovery |
| Approved-command history, project folders, chats and memory content | Recreated by the reader. Private source content and command fingerprints are excluded |
| Cloud execution | Configure your repository, environment, permissions and budget. Handoff tools package and verify inputs; dispatch needs an available remote environment |

The [coverage map](../environment/bundle/tooling/settings-coverage.json) accounts for the original 24 top-level configuration categories. The [sanitized snapshot](../config/config.sanitized.toml) is a reference. The runnable file is the installed `codex-home/config.toml`.

## Adopt it in your desktop client

Use the separate launcher to validate the setup and keep a recovery point. To adopt it in the desktop client, give this guide to your own Codex and follow this migration checklist.

1. Back up your configuration, user Skills, roles and relevant hooks outside the repository, recording whether each original file existed.
2. Compare the generated Codex home with your user directories. Merge selected Skills, agreements and roles, preserving copies of existing same-name files.
3. Merge the model, search, permission and tool settings you intend to use. Programs can remain in the isolated tool directory, using its rendered paths. For desktop-launched MCP, add the relevant venv Scripts and pinned Node directories to that connection's child PATH, followed by your own PATH. Retain your own account parameters, project trust and sign-in configuration.
4. Install corresponding plugins through the official directory and connect your accounts. Retain your own client-generated `node_repl`, browser trust values, notification bindings and local communication pipes. Snapshot placeholders are reference-only. Apply desktop preferences from the host reference one by one.
5. Reload the client and verify Skills, roles and MCP in a new session, then run a small task. Record applied settings, version-specific differences and recovery steps.

The installer manages the separate directory. Desktop merging is an explicit reader action in their environment. Private chats, memories, indexes and approval history remain reader-owned.

## Explicit changes from the source machine

- Personal paths become installation paths or reader-supplied project locations.
- The four role files use the compatible schema and retain their instructions. Permissions remain under the parent session and runtime.
- Four Python environments move into venv subdirectories. Beads and Worktrunk executables move into `bin`. Controllers use the relocated paths.
- The older restricted `docx` Skill is replaced with an official pinned Apache revision. The optional paper PDF is linked upstream.
- Sign-in state, tokens, caches, indexes, data and historical approvals are generated in the reader's environment.

See the [portability record](../environment/portability.json) and [third-party notices](../THIRD_PARTY_NOTICES.md).

## Use and verify

```powershell
$py313 = py -3.13 -c "import sys; print(sys.executable)"
& $py313 ../my-codex-environment/launch.py -- login
& $py313 ../my-codex-environment/launch.py -- --version
& $py313 ../my-codex-environment/launch.py --project C:/path/to/my-project
```

The launcher uses an explicitly selected Codex binary or the installed, checked pinned CLI before its documented fallback. Sign-in is stored in the separate home. The process still runs as your normal OS account, with access governed by that account and Codex's permissions.

Try a small real task. Check Skill discovery, required tools, MCP availability and the delivered result. Select tests and independent review appropriate to that task. See [recorded verification](reproduction-verification.md).

When installed, the checked pinned Node directory is added to the Codex child process's PATH. Use `launch.py --inherit-node-path` when you want the project's own Node selection, then follow that project's runtime manager.

## Retry, customize and recover

Keep the error when an install fails. Completed groups can be reused after receipt verification. Incomplete or modified directories are rejected instead of overwritten. Inspect differences and running processes before handling a failed directory you created.

Install required groups before personalizing managed configuration. Verification compares against the release, so deliberate edits are reported as differences. For an upgrade, create another environment and merge your changes while retaining the working version.

To recover, switch back to your original launcher and configuration. Restore any manually changed plugins or project settings from your own backup. Keep credentials, accounts and run records outside public repositories.
