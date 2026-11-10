---
name: repository-intelligence
description: Use local structural search, bounded repository bundles and qualified repository graph queries when ordinary text search or targeted source reads are insufficient.
---

# Repository intelligence

Start with `rg --files`, targeted `rg` and source reads. Use the installed pinned
CLI tools below when their added behavior answers the question. Do not run REA
for ordinary source architecture analysis.

Windows launcher:
`{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1`

## Structural search

Use ast-grep for syntax-aware patterns, such as finding actual calls across
formatting without matching comments or string contents. Check `ast-grep run
--help` for flags and select the correct language. In PowerShell quote metavariables
with single quotes so `$` stays literal:

```powershell
& '{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1' ast-grep run --lang javascript --pattern 'console.log($$$ARGS)' --json 'src'
```

Inspect matched ranges in context. Syntax matches do not prove runtime behavior,
symbol identity or data flow. Preview any rewrite, preserve the working tree and
run project checks; a search request does not authorize a bulk rewrite.

## Context packaging

Use Repomix for a requested handoff or cross-file review that benefits from one
artifact. Scope the repository and include patterns explicitly; inspect local
Repomix config before executing it. Preserve secret scanning and ignores, and do
not allow `fileProcessors` commands or remote collection by default.

```powershell
& '{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1' repomix 'C:\path\repo' --include 'src/**,README.md,package.json' --output 'C:\path\work\context.xml'
```

Check the emitted file list and actual contents before sharing. Ignores and
Secretlint are useful checks, not guarantees; omit credentials, env files,
private data and unneeded generated files. Keep output outside source inputs or
explicitly ignore it. Do not upload bundles without authorization. Compression
may omit details, so consult original source for consequential claims.

Versions and local security overrides live in the kit's package.json and lockfile.
The launcher uses its own Node; do not run a floating npx replacement if it fails.

## Symbol identity and references

The installed Serena server adds scoped semantic navigation when text or syntax
matching cannot distinguish aliases or same-named symbols. If its navigation tools are
available, obtain the current session from initial_instructions and activate the explicitly selected project and then use find_symbol,
get_symbols_overview or find_referencing_symbols with a relative source path.
Do not infer the project from the desktop process working directory. Project
activation may create local .serena configuration/cache; preserve project work.

This integration exposes navigation only, with the REPL, mutation and memory
operations absent from the host allowlist. That is a tool boundary, not a sandbox
for other host commands. The verified Python fixture resolved an import alias and
excluded a same-named decoy; reference results included the import edge, not a
complete transitive call graph. Follow aliases and dynamic-call uncertainty with
source evidence. Other languages and live project performance remain unqualified.
If the current session has not loaded Serena, continue with existing source tools;
a configured server alone does not prove a live connection.

## Indexed repository relationships

For a noncommercial repository where transitive relationships would help, the
installed GitNexus route can index and query a scoped graph. Read
[repository graph workflow](references/repository-graphs.md) before first use.
It complements source navigation; a graph result is not runtime truth. The
tested CodeGraphContext build is quarantined from normal workflow because the
shared fixture exposed wrong alias edges and its dependency set has known
advisories. Do not select it just because it is installed.
