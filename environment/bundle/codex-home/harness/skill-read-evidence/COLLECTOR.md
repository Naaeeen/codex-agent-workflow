# Bounded skill-read evidence collector

`skill_read_evidence.py` consumes completed command-execution events. It never
executes their command strings. It invokes only the fixed local
`parse_skill_commands.ps1` with JSON on stdin; that script uses PowerShell
`Parser.ParseInput` and AST inspection. The parser is launched without profiles,
noninteractively, with Windows `CREATE_NO_WINDOW` and hidden startup settings.
There are no model calls, network calls, package installs, or global changes.

## Public API

```python
from skill_read_evidence import SkillReadEvidenceCollector

# Trusted controlled configuration only; include every skill in scope.
collector = SkillReadEvidenceCollector({
    "example-skill": r"C:\trusted\example-skill\SKILL.md",
})

labels = collector.collect(command, aggregated_output, exit_code)
# Or collector.collect_event({"command": ..., "aggregated_output": ...,
#                            "exit_code": ...})
# Or collector.summarize(completed_events)
```

Every result has exactly these fields:

```json
{"confirmed_reads": ["example-skill"], "unknown_reads_count": 0, "classification": "CONFIRMED"}
```

Names are drawn only from the controlled configuration. Results never contain
raw commands, output, filesystem paths, parser diagnostics, or exception text.
Classification is `INCONCLUSIVE` whenever the unknown count is nonzero, including
when a different read was confirmed. Otherwise it is `CONFIRMED` when names were
confirmed and `NO_CONFIRMED_READS` when none were. The latter is a bounded absence
of evidence, not an OS-level assertion that no file access occurred.

The unknown count is the number of unresolved candidate signals, not a count of
actual file reads. One candidate may represent several runtime operations.

## Evidence requirements

A confirmed read requires all of the following:

1. The completed event has integer exit code zero.
2. A direct, unconditional literal `Get-Content`, `cat`, `type`, `gc`, or standard
   `Microsoft.PowerShell.Management\Get-Content` command identifies the exact
   absolute path of a configured file.
3. No detected definition, assignment, alias/environment mutation, redirection,
   or other unsupported execution context undermines attribution.
4. Output contains a matching body excerpt of at least 12 words and 80 characters.
   Frontmatter, headings, and fenced code do not supply these excerpts; whitespace
   and terminal ANSI formatting differences are tolerated.

Bodies are snapshotted when the collector is constructed. Reconstruct it after
changing a skill. The threshold can deliberately leave short files or truncated
output inconclusive. Duplicate confirmed labels are deduplicated and sorted.
For bounded `-TotalCount`/`-Tail` reads, the matching anchor must also exist in
the selected source lines. In a multiple-skill read batch, the anchor must be
unique among the other selected source bodies; shared boilerplate cannot
confirm either source. Ambiguity remains inconclusive.

## Supported syntax and unknowns

Single/double quoted literal paths, positional paths, `-LiteralPath`, `-Path`,
`-Raw`, common literal encodings, positive `-TotalCount`/`-Head`/`-First`/`-Tail`,
and common `-ErrorAction` values are supported. Exact colon parameter syntax is
supported. A literal `pwsh`/`powershell[.exe] -Command '...'` wrapper is recursively
parsed, to a depth of four, only for those native shell command names. Optional
`-NoLogo`, `-NoProfile`, and `-NonInteractive` flags are supported.
A wrapper must be the sole outer command. Direct read batches may contain only
known literal reads and a strict `Out-String` formatter at the end of the same
pipeline. Arbitrary output, output sinks, unknown sources, or ordinary document
reads mixed into a skill read event make attribution inconclusive.

The native event command is a POSIX `shlex` display string even on Windows,
rather than a Windows `CreateProcess` command line. The pinned
[event builder](https://github.com/openai/codex/blob/rust-v0.166.0-alpha.6/codex-rs/app-server-protocol/src/protocol/item_builders.rs#L46-L60)
uses `redact_secrets(shlex_join(command))`, and the pinned
[join helper](https://github.com/openai/codex/blob/rust-v0.166.0-alpha.6/codex-rs/shell-command/src/parse_command.rs#L6-L12)
uses Rust `shlex::try_join`. At the outermost event boundary only, the collector
decodes that display as data with POSIX `shlex.split`, validates an absolute
native PowerShell path, optional `-NoLogo`, `-NoProfile`, and `-NonInteractive`
flags, and one final `-Command` script argument. Only that script enters the
existing PowerShell AST classifier. The display is never decoded again inside
a PowerShell script. Extra arguments, other switches, missing scripts, malformed
quotes, and NUL input are inconclusive. The pinned
[secret sanitizer](https://github.com/openai/codex/blob/rust-v0.166.0-alpha.6/codex-rs/secrets/src/sanitizer.rs#L15-L19)
inserts `[REDACTED_SECRET]`; any command containing that marker is inconclusive,
without attempting to reconstruct removed text. No decoded input is executed. The earlier
Windows-argv interpretation was incorrect for this event field and is retained
only in versioned baseline evidence.

Dynamic paths, wildcard paths, unresolved relative `SKILL.md` paths, unregistered
`SKILL.md` paths, unsupported flags, nonliteral wrappers, encoded/file wrappers,
cmd wrappers, nested/conditional read ASTs, selected .NET file-reader methods,
parser failure, and output missing the required body excerpt are inconclusive.
Failed commands never confirm reads; identifiable failed skill-read attempts are
inconclusive. Failed ordinary literal source/document reads are not skill reads.

Echoing a pathname or fake command, comments, file listings, `rg --files`, and
ordinary literal source/document reads produce no skill-read signal. Explicit
skill-content searches with `rg` or `Select-String` are unsupported partial
reads and therefore inconclusive, never confirmed. Python `-c` code is parsed
with Python's AST parser: recognized `open`/`read_text`/`read_bytes` calls on a
skill path or unresolved path are inconclusive; literal ordinary-document
reads do not count. Python code is never executed by this collector.

For Python only, a variable may identify an ordinary file when it has one
top-level assignment to a literal string or a literal, unmodified `pathlib`
constructor, and the assignment precedes the top-level read. The constructor's
import must be visible and unchanged. Reassignments, destructuring, alias chains,
unknown variables, control flow, nested scopes, dynamic namespace calls, and
attribute/subscript mutation do not receive this exclusion. Reads in functions
or comprehensions remain unknown. This is a small static binding rule, not
Python execution or general data-flow analysis.
The binding may be used only as a direct receiver of `read_text`, `read_bytes`,
`open`, `write_text`, or `write_bytes`, or as the first argument of an unmodified
built-in `open`. Passing it elsewhere, extracting a method, aliasing it, or using
another receiver method invalidates the exclusion. Dynamic namespace references
such as `vars` also invalidate it, including when assigned to an alias. These
rules preserve the path target; they do not assert that arbitrary Python is safe
or reconstruct unrecognized code.

The PowerShell parser also reports the literal arguments of nested read ASTs.
A literal ordinary-file read inside an assignment does not become an unknown
skill read solely because of the assignment. Nested skill-file or dynamic reads
remain unknown and can never be confirmed by this rule.

## Limits

This is a diagnostic grammar, not a sandbox, shell interpreter, or filesystem
audit. It cannot establish the behavior of arbitrary Python/Node/native scripts,
external tools, module internals, previous-session command shadowing, or shell
aliases changed outside the captured event. Native wrapper names and standard
PowerShell command meanings are assumed to refer to their expected executables
and cmdlets. Directory-recursive searches, renamed files, indirect APIs, or
obfuscated read code can fall outside the detectable signals. It cannot prove
causal provenance when outside-event activity fabricates identical body text.
Use clean, profile-free probe sessions and report this scope.

Raw inputs remain internal in memory and in the parser subprocess pipes. The
safe-output contract applies to the public result, not to arbitrary caller logs.
Configuration errors contain generic messages without paths; callers should not
log their own unredacted configuration or command events.

For the routing probes, any unknown signal makes the relevant negative case
`INCONCLUSIVE`; never interpret known-only labels plus an unknown count as a pass.

## Verification

Run from this folder:

```powershell
python -m unittest -v test_skill_read_evidence.py
python -m py_compile skill_read_evidence.py test_skill_read_evidence.py
```

All tests use temporary fake skill files. The native-output integration test uses
a fixed local `Get-Content` fixture reader, and the parser nonexecution test
verifies that an input command cannot create its sentinel file. No existing
skill, observer, global config, or probe fixture is changed by the tests.

The first four runtime probes predate the native-envelope correction and retain
their original inconclusive evidence. `collector-baseline-pre-envelope` records
the exact old source/parser/test hashes, reconstructed by reversing only the
known envelope patch and verified against the pre-edit SHA-256 record; its
provenance states this explicitly. New probes must use new evidence and the
new collector version, rather than rewriting the original reports.
`collector-baseline-pre-literal-bindings` separately preserves direct copies of
the 47-test version before the limited Python/PowerShell literal-target change.
`collector-baseline-pre-shlex-display` preserves direct copies of the 55-test
version before the pinned event-display codec correction. Prior probe reports
remain attached to their actual classifier versions; they are not rewritten.
