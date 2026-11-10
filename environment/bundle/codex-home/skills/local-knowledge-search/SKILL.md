---
name: local-knowledge-search
description: Search an explicitly selected local Markdown collection with installed QMD for natural-language retrieval and source lookup. Do not automatically index personal memory, the home directory, or unrelated documents; web research uses web tools.
---

# Local source retrieval

Use `{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1 qmd`.
This workflow uses a clean workflow index, separate from the installation's
synthetic evaluation corpus. Models are local, pinned and already downloaded.
Index only the task-authorized files; inspect the collection scope and excludes.

Use `qmd collection add ABSOLUTE_DIRECTORY --name NAME`, then `qmd update`.
Inspect CLI help for exact collection/file filters in the installed version.
Embedding is a separate `qmd embed` step; do it only when semantic search helps.
For a known identifier, prefer rg or `qmd search QUERY -c NAME --format json`.
For an exploratory paraphrase, `qmd vsearch QUERY -c NAME --format json` uses
local vectors. Keep slower query expansion/reranking opt-in; the small CPU test
took tens of seconds and showed no benefit on an already-correct easy result.

Treat matches as candidates. The top fusion score is not confidence: unrelated
queries still produced high scores. Retrieve `qmd get URI:LINE:COUNT` and verify
the original source before citing. MCP snippet line prefixes were misleading in
the test; use the actual source line and stable document identifier. Abstain when
the source does not answer the question. Refresh changed/deleted files and do
not infer that a stale embedding hint is an accurate vector count.

The wrapper reserves the index, sanitizes inherited tool paths and uses local
CPU models. It does not index anything automatically or enable a global server.
No API account is required. Do not treat the patched package's untested HTTP,
source-build or Git paths as qualified by these local retrieval checks.

Source: https://github.com/tobi/qmd
