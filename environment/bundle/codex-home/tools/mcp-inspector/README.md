# Local MCP Inspector CLI

Use the shared launcher: `agent-tool.ps1 mcp-inspector ...`.
The pinned package is @modelcontextprotocol/inspector 2.14.0, using the existing
isolated Node runtime. This entry calls the CLI directly; it never selects the
default web UI. Client/catalog/OAuth paths are tool-local, new secrets are kept
in memory, automatic browser opening and Node preload variables are disabled.
Caller environment values are restored. This does not erase pre-existing secrets
or turn arbitrary remote tools into read-only operations.

Examples:

```text
mcp-inspector --config SESSION.json --server NAME --method tools/list --strict --format json
mcp-inspector --config SESSION.json --server NAME --method tools/call --tool-name TOOL --tool-arg key=value --format json
mcp-inspector ABSOLUTE_SERVER_COMMAND SERVER_SCRIPT --method tools/list --strict --format json
```

Only invoke an authorized server/command. Read-only --config is not changed by
the inspector. Tool calls can have the side effects the selected server permits.
An explicit isError produced exit5 in the controlled test; an unportable bare
boolean schema produced exit6. --strict is not a complete schema verifier: a
missing local reference was not caught. Keep SDK/runtime validation as well.

Preserve the package LICENSE: this upstream release is in a MIT/Apache-2.0
transition; documentation is CC-BY-4.0. Do not relabel it as simply MIT.
Source: https://github.com/modelcontextprotocol/inspector
