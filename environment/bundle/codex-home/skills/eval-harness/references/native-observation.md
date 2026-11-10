# Native observation and artifact acceptance

Installed modules:

- {{CODEX_HOME}}\harness\native-observer\native_observer.py
- {{CODEX_HOME}}\harness\native-eval-bridge\native_eval.py

Use these for authorized CLI experiments or resumable jobs, not to duplicate a
running desktop chat. No new API key/provider is configured; the selected Codex
client uses its normal account and configuration. A real run uses account quota.

## Choose the lane

For one of the eight installed synthetic regressions, the bridge prepares a new
trial by default. Add --execute only when model execution is authorized. It
records dispatch and observer metadata beside the immutable receipt, then grades
actual artifacts. PASS requires both execution success and artifact PASS.

For a selected custom job, the observer takes explicit absolute executable,
workspace and new result-directory paths, and prompt text through stdin. The
default is ephemeral/read-only. Persistent=True and an exact recorded UUID are
needed for cross-process resume. Do not use --last, which may select unrelated
work. Check the installed client's help before changing versions.

## Interpret evidence correctly

The observer requires ordered thread/start/terminal events and normal exit.
Top-level errors, malformed/truncated streams, mismatched resume IDs, timeouts
and output limits do not pass. Nonfatal item errors remain visible even when the
turn succeeds. A returned answer or exit zero alone is insufficient.

Item counters count lifecycle events, not unique tool invocations. Missing token
fields are unknown, not zero. In the verified 0.166.0-alpha.6 source, terminal
usage copies cumulative thread totals; resumed snapshots must not be added as
if each were a turn delta. The recorded CLI-version source matters: a supplied
version is a declaration, not independent verification. Other releases require
rechecking their actual semantics.

Raw prompts, reasoning, commands, outputs and error text are not stored by the
observer. The Codex client may still retain normal persistent session history.
Do not label this metadata policy a privacy guarantee for all client storage or
an OS sandbox. Windows process-tree ownership bounds the local launched process;
it does not establish a provider-side billing cutoff.

Reference: https://learn.chatgpt.com/docs/non-interactive-mode
Pinned accounting implementation:
https://github.com/openai/codex/blob/rust-v0.166.0-alpha.6/codex-rs/exec/src/event_processor_with_jsonl_output.rs

For targeted skill-routing diagnostics, the local skill-read-evidence library
can recognize supported content-read events. It deliberately marks unsupported
or ambiguous operations inconclusive; do not turn unknown reads into a negative
PASS or run this diagnostic for every ordinary task.
