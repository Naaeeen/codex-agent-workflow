CodeGraphContext 0.6.13 — installed, opt-in structural candidate tool

Root: {{CODEX_HOME}}\tools\codegraph-context
Python: venv\Scripts\python.exe (CPython 3.13.7)
CLI: run_cgc.py
Read-only stdio MCP: readonly_mcp.py --repo ABSOLUTE_REPO --db ABSOLUTE_DATABASE
Database: embedded Kuzu 0.11.3; no daemon, accounts, API keys, or public listener.
Global PATH, Codex config, skills, launcher, and user repositories were not changed.

Workflow:
1. Use rg/ast-grep/Serena for exact source discovery and identities.
2. Explicitly index a selected repository into a per-project DB with:
   & '{{CODEX_HOME}}\tools\codegraph-context\venv\Scripts\python.exe' -X utf8 '{{CODEX_HOME}}\tools\codegraph-context\run_cgc.py' --path 'ABSOLUTE_DB_FILE' index 'ABSOLUTE_REPO' --no-progress
3. Query the repository-scoped read-only facade via its --repo/--db arguments.
   It exposes seven original tools/schemas and preserves original results.
   It blocks indexing, deletion, watching, downloads, raw Cypher, context changes,
   graph_name overrides, and path escapes. Third-party agent instructions are removed.
4. Treat relationships as candidates. Confirm source/imports and actual tests before
   refactoring or impact claims. Refresh after changes. Native `update` currently
   deletes the existing index and performs a full rebuild; it is not an incremental
   file-level update in the verified path. Stop MCP before rebuilding the same DB.

Observed limits (shared synthetic Python fixture, not a quality benchmark):
- 2 of 3 expected production CALLS edges were correct.
- An aliased import into service.py incorrectly targeted examples/pricing.py's
  identically named calculate_total. Incremental quote_order suffered the same error.
- A path-scoped find_callers silently fell back to same-name results and reported
  the decoy, so its apparently successful response did not establish identity.
- On Windows a path-scoped find_callees returned no matches; find_all_callers failed
  on Kuzu syntax `path_nodes[0].path`; the end-to-end call chain was consequently absent.
- A .zig-only directory returned success with 0 scanned files. Check coverage counts.
- A nonexistent path returned exit 1. Facade outside-repo/write requests were rejected.

Dependency audit:
86 exact installed package versions checked with OSV querybatch on 2026-11-05.
protobuf 3.20.3: CVE-2026-0994 and CVE-2025-4565 (4 alias advisory records total).
Upstream pins protobuf>=3.20,<3.21; the fixed branches are outside that constraint.
SCIP is explicitly disabled. The verified Python Tree-sitter path does not parse
SCIP protobuf. Reachability of advisories in all optional paths was not exhaustively
proved. Do not expose an HTTP endpoint or feed untrusted serialized bundles.
Keep this installed for opt-in evaluation, not as default authoritative impact tool.

Isolation:
USERPROFILE is overridden only inside the child Python process to root\state.
No $HOME, $CODEX_HOME, system PATH, or global runtime replacement.
SCIP, auto-watch, vector/inheritance resolution, external resolution, project .env
loading, and OpenTelemetry SDK disabled. First-party source scan found no CGC
analytics emitter; this was not packet capture. Some optional commands call network
services and are not exposed in the facade. Language-pack downloads grammar binaries
into the isolated parser cache on first indexing of a language. Current Python grammar
version/hash and all wheels/dependencies are recorded in manifest.json.

An initial isolated-home run printed success with zero functions because grammar cache
was unavailable, incorrectly surfaced as a Python 3.13 wheel error. Explicit private
TREE_SITTER_LANGUAGE_PACK_CACHE_DIR fixed the cause. No vendor source was patched.

Evidence:
<PROJECT_ROOT>\2026-11-05\z\work\graph-round\codegraph
- manifest.json / requirements.lock / install-report.json: provenance and dependencies
- mcp-tools.json: complete native handshake, upstream instructions, and tool schemas
- checks.json: machine-readable verdicts
- raw-edges-baseline.json and raw-edges-incremental.json: direct read-only DB evidence
- mcp-results-baseline.json / mcp-results-incremental.json: actual stdio tool responses
- incremental-update.json / error-cases.json / osv-audit.json: execution and audit results

No raw upstream source edits. Broad parser/backend changes were not attempted merely
for this fixture: alias identity, path fallback, Windows normalization, and Kuzu query
syntax are distinct upstream defects requiring wider language/backend regression tests.
Independent facade review is requested from the parent and remains pending here.
