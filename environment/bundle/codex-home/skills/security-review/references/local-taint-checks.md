# Local CE taint checks

Use `agent-tool.ps1 semgrep --config LOCAL_RULE.yml --target LOCAL_SOURCE --error`.
The wrapper requires local files, rejects UNC before resolution, disables remote
rules, metrics, version checks, Pro and autofix, and uses the qualified patched
dependency environment. The source is not uploaded by this lane.

Write rules for the actual source, sink and sanitizer behavior, and include a
known-positive and known-negative fixture before trusting results. The tested
CE route followed same-function assignments beyond a direct AST match. It did
not establish cross-function/cross-file coverage, and sanitizer exactness changed
results. A clean result is not proof of safety. Read the source-to-sink evidence
and use the project's security policy and focused scan workflow when required.

The installed version has an explicit local metadata-only dependency patch;
upstream CLI code bytes are unchanged. Local CE scanning was tested; MCP/trace
features of that distribution were not qualified. Do not run those through this
restricted entry point or expand its scope without revalidation.

Sources: https://docs.semgrep.dev/writing-rules/data-flow/taint-mode/overview ;
https://github.com/semgrep/semgrep
