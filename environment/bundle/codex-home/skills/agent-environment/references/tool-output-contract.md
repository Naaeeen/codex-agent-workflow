# Tool output contracts

Keep the full relevant evidence available without loading every intermediate
record into model context. In an existing code environment, select the needed
fields, aggregate counts, and return a bounded sample plus stable source IDs or
paths. Retain error and truncation flags. Do not summarize missing text as absent.

For example, filter the available tool catalogue by the service AND operation,
then return a small name/description subset. Do not print every tool whose long
boilerplate happens to contain a generic keyword. For local SQL, use DuckDB to
join/aggregate a selected dataset and show counts plus representative rows.

Public documentation MCPs have separate search/list/fetch output budgets in
config.toml. The tested client applies these to model-facing direct MCP output,
with a serialization allowance. They are not limits on server traffic, process
memory, all client history, or raw Code Mode results. A multi-item response can
lose its later items; a single-item response retains head/tail around a marker.
On any truncation/omission marker, narrow the query, fetch a specific page/range,
or inspect the retained artifact before drawing a completeness conclusion.

Errors should include an explicit short error status and actionable next step
near the start. Exit 0 or a completed model turn is not proof a tool succeeded.
The local deterministic integration test exercised long text, omitted later
items, narrow-range recovery and explicit error text; it was not model QA.

Sources:
- https://www.anthropic.com/research/writing-tools-for-agents
- https://www.anthropic.com/research/code-execution-with-mcp
- https://learn.chatgpt.com/docs/extend/mcp
- https://github.com/openai/codex/blob/rust-v0.166.0-alpha.6/codex-rs/core/src/tools/context.rs
