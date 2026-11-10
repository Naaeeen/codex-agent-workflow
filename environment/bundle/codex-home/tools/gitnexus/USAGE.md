# Scoped GitNexus CLI

This optional route is for eligible noncommercial work under the preserved PolyForm-Noncommercial-1.0.0 license. Installation is not a commercial-use grant.

Run with PowerShell 7+:

```powershell
& '{{CODEX_HOME}}\tools\gitnexus\run-gitnexus.ps1' analyze 'C:\path\to\repository' --name unique-project-name
& '{{CODEX_HOME}}\tools\gitnexus\run-gitnexus.ps1' query 'authentication' --repo unique-project-name --limit 5
& '{{CODEX_HOME}}\tools\gitnexus\run-gitnexus.ps1' context function_name --file src/module.py --repo unique-project-name
& '{{CODEX_HOME}}\tools\gitnexus\run-gitnexus.ps1' impact function_name --file src/module.py --repo unique-project-name --depth 3
```

`analyze` requires an absolute local Git root and a unique `--name`; the wrapper always adds `--index-only`. Indexing still writes `.git/info/exclude` and external index metadata/runner/cache. It does not generate AGENTS.md, CLAUDE.md or skills. Refresh explicitly after source edits. Parse exact context/impact paths and warning/error/ambiguity fields; keyword ranking can favor an unrelated same-name definition.

The production registry and indexes are separate from experiment evidence: `workflow-state` / `workflow-indexes`. The old `state` / `indexes` contain the synthetic comparison only. The FTS binary is shared from isolated `native-home`.

The wrapper clears every inherited `GITNEXUS_*` variable and `NODE_OPTIONS` / `NODE_PATH` in the child environment, sets fixed local paths, disables update checks and extension installs, and never changes the parent environment. Unknown flags, setup, serve, update, publish, wiki, rename and MCP are refused. Graph queries require explicit registered `--repo`. Indexes with nonzero or unknown embedding counts are refused, as are repository settings outside the wrapper's graph-only scope.

MCP was tested separately as an experiment. The historical run-cli.mjs helper and direct MCP environment examples are not the production route; they are retained for reproducibility. This wrapper deliberately exposes no MCP because read-only mode alone does not restrict access to a single registered repository or suppress every upstream instruction.

This wrapper is not an OS/network sandbox. It trusts the isolated registry and upstream package, and does not prove graph completeness. The pinned package has three moderate npm audit entries and no reported high/critical entries at installation time. See install-manifest.json and the evaluation report for exact provenance and limits.
