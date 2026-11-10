# Native Codex metadata observer

Python 3.11+ stdlib only. No installation, provider SDK, authentication file
access, global configuration mutation, model selection, or remote dispatch is
performed by the observer. Invoking a real Codex executable does start an actual
Codex turn, using that client's existing authentication and configuration.
The caller must already have authorization for that run.

## Public API

```python
from pathlib import Path
from native_observer import Limits, ObserverConfig, run_observer

result = run_observer(
    ObserverConfig(
        executable=Path(r"C:\absolute\pinned\codex.exe"),
        workspace=Path(r"C:\absolute\existing-workspace"),
        result_dir=Path(r"C:\absolute\existing-parent\new-result"),
        cli_version="codex-cli 0.166.0-alpha.6",
        # profile="your-profile",    # optional, existing simple profile name
        # persistent=True,           # default is ephemeral
        # resume_id="01234567-89ab-cdef-0123-456789abcdef",
        # sandbox="workspace-write", # default is read-only
        limits=Limits(timeout_seconds=120),
    ),
    prompt_text,                     # in memory, delivered only through stdin
    expected_final={"ok": True},    # optional in-memory JSON; never saved
)
```

`result_dir` must not exist and its parent must exist. Executable, workspace,
result path and their existing ancestors must be absolute and contain no `..`,
symlink or Windows reparse point. The process is launched with `shell=False`.
The API does not accept extra CLI arguments, arbitrary configuration overrides,
approval bypass flags, or a resume selector such as `--last`. The optional profile
name is caller-declared metadata and is passed through without reading its file.

Omit `cli_version` to run a bounded, owned `--version` check. Supplying a version
records its source as `supplied`; it is a declaration, not an independently
verified claim. Versions have a strict bounded `codex-cli` version syntax.

## Command line

Read prompt text from standard input (there is deliberately no prompt option):

```powershell
$promptText | python .\native_observer.py `
  --executable 'C:\absolute\pinned\codex.exe' `
  --workspace 'C:\absolute\existing-workspace' `
  --result-dir 'C:\absolute\existing-parent\new-result' `
  --cli-version 'codex-cli 0.166.0-alpha.6' --timeout 120
```

The CLI prints only the metadata JSON. Its exit code is 0 for observed successful
turn completion, 1 for a completed observation with a non-success outcome, and
2 for rejected configuration or failed result storage. The API additionally
supports expected JSON comparison; the CLI deliberately has no expected-answer
file or argument option.

## Invocation contract and help verification

Installed help was read from the pinned native `codex-cli 0.166.0-alpha.6` on
2026-11-05, using top-level help, `exec --help` and `exec resume --help`.
The top-level `--no-daemon` option explicitly disables use of a shared background
server, so a run cannot silently continue outside the owned child process tree.
Parent-only options
`--sandbox`, `--cd`, `--color`, and `--profile` precede the optional `resume`
subcommand. Shared execution options follow it:

```text
<exe> --no-daemon exec --sandbox read-only --cd <workspace> --color never
      [--profile <simple-name>] [resume] --json --skip-git-repo-check
      [--ephemeral] [<exact-resume-UUID>] -
```

`--ephemeral` is present unless `persistent=True`. It controls Codex session
persistence; it does not isolate filesystem access. A persistent run or resume
can cause the Codex client itself to retain normal session files. The observer
does not read those files. The chosen CLI and its configured tools remain
responsible for their own policy enforcement. Recheck help before using a
different client release; runtime help is not fetched for every invocation.

## Stored metadata and interpretation

Exactly one `metadata.json` is created. The schema is a positive allowlist:

- `schema_version`, generated `run_id`, UTC times and monotonic elapsed seconds.
- bounded version and its `supplied`/`checked` source; declared sandbox,
  persistence, optional profile, exact resume UUID and validated observed UUID.
- `outcome`, `success`, native process `exit_code`, fixed event and item counts,
  fixed item status counts, and bounded numeric item exit-code counts.
- unknown event/item **counts only**, invalid JSON line count, terminal count,
  truncation/timeout flags and fixed limit-reason labels.
- allowlisted integer token fields, with absent/invalid values represented as
  `null`: input, cached input, cache-write input, output and reasoning output
  tokens. `usage_source_event` identifies `turn.completed`.
- stream byte counts, SHA-256 of the received stderr prefix, and fixed boolean
  stderr categories (`auth`, `permission`, `failed`, `unsupported`, `error`).
- `expected_final_matched` (`null` if disabled; otherwise boolean) and the fixed
  statement `raw_streams_saved: false`.

No prompt, argv, executable/workspace path, message text, reasoning, command,
tool arguments, command output, diff, arbitrary event field, final answer, raw
stderr or raw event stream is saved. When comparison is enabled, the latest
completed agent message is parsed transiently as JSON and compared canonically
with the in-memory expected value; neither value is recorded. This comparison
does not itself define successful turn execution.

`success` requires exactly one valid `thread.started`, one later `turn.started`,
then exactly one `turn.completed`, exit 0, and no stream/protocol failure.
The observed UUID must equal the requested UUID for a resume. Duplicate thread
starts, terminals without the required starts, and out-of-order lifecycle
events are rejected. Exit 0 by itself produces `incomplete`. `item:error` is counted but does
not force failure: optional tool errors can coexist with successful completion.
This includes startup item errors between `thread.started` and `turn.started`.
Duplicate/conflicting terminal events produce `protocol_error`. Distinct
outcomes also include `turn_failed`, `nonzero_exit`, `invalid_json`,
`truncated_stream`, `limit_exceeded`, `timeout`, `launch_error`, `io_error`, and
`stream_error`. The latter is a top-level `error` event, which the
[version-pinned official event schema](https://github.com/openai/codex/blob/rust-v0.166.0-alpha.6/sdk/typescript/src/events.ts)
describes as unrecoverable; it can never silently produce a successful result.
Multiple simultaneous problems can occur; flags/counts remain visible, while
the outcome precedence is timeout, limit, launch, I/O, truncation, JSON, protocol,
native nonzero exit, failed turn, stream error, successful turn, incomplete.

Token fields retain the unmodified numbers from this invocation's terminal
event. For exactly `codex-cli 0.166.0-alpha.6`, `usage_scope` is
`cumulative_thread_snapshot`: the version-pinned implementation's
[`usage_from_last_total`](https://github.com/openai/codex/blob/rust-v0.166.0-alpha.6/codex-rs/exec/src/event_processor_with_jsonl_output.rs)
copies `usage.total`. These snapshots must **not be added across resumed
invocations**. Other versions are labeled `unknown_do_not_sum` until their
semantics are verified. This annotation does not calculate deltas or rewrite
old metadata. The numbers do not establish billing/cost, causal attribution to
any profile setting, or model quality. Fixed stderr category matches are diagnostic
signals, not validated root causes; for example `auth=True` is not proof the
main model request failed authentication.

## Bounds and process ownership

Defaults are 120 seconds, 128 KiB per JSONL line, 4 MiB stdout, 1 MiB stderr,
10,000 parsed events, 1 MiB prompt and 64 KiB expected JSON. Callers may lower
these or raise them within finite hard ceilings. Stdout/stderr drain concurrently,
stdin writes separately, and no full output transcript is accumulated. Temporary
memory is proportional to bounded line/event storage, not a complete stream.
Limit detection may read one extra 4 KiB chunk; hashes cover only bytes actually
received before the pipe closes. A final non-newline line is marked truncated.

On Windows, `CREATE_NO_WINDOW` hides the process, and `CREATE_SUSPENDED` prevents
it from running before assignment to an unnamed Job Object with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Documented Toolhelp and `ResumeThread` APIs
resume only the owned suspended process. If assignment fails, execution fails
closed. Closing the job kills its owned descendants, including after parent
exit. On POSIX, a new process session/group is created and only that owned group
is killed. Cleanup applies to version checks too. No process-name-wide kill is
used. Local path validation does not promise protection against an administrator
replacing directories concurrently during the run.

## Verification

```powershell
python -m unittest -v test_native_observer.py
```

The initial red run failed because the implementation module did not exist.
The final synthetic suite has 25 tests and no external services. A fake CLI uses
the current Python executable and a workspace-local `exec` script. Its launch
adapter records the full production argument vector, removes only
`--no-daemon` (which Python itself cannot parse), and then invokes the real
owned-process implementation. A separate assertion verifies that the production
command includes `--no-daemon` before `exec`; no native Codex turn is needed.
Coverage
includes normal success, exit-zero incompleteness, failed turns, nonzero exit,
invalid and truncated JSON, line/total/event/stderr bounds, blocked stdin,
concurrent large streams, timeout with a real child and grandchild, hostile
unknown/sensitive fields, null usage, duplicate terminals, exact UUID resume,
profile placement, no overwrite, reparse rejection, unchanged parent environment,
version rejection, disabled output capture, required lifecycle ordering,
matching resumed UUIDs, fatal top-level stream errors and nonfatal startup item
errors, missing cache-write usage, and preserved cumulative snapshot semantics.
Windows tests created a junction
without changing global settings and verified actual descendant termination.

Test output must be reported by the caller; these synthetic tests establish
observer plumbing and privacy boundaries, not real-model reliability. No formal
coverage percentage is claimed. Independent review and real Codex
persistent/resume trials are separate parent-owned acceptance steps.

The first independent review reproduced false successes for a bare terminal,
out-of-order/duplicate starts and mismatched resume UUIDs. Regression tests
reproduced those failures before the lifecycle checks were added. The public
API remains unchanged; `stream_error` is an additional non-success outcome.

## Interpretation safeguards from real local trials

The local-analysis profile used in the A/B experiment was rejected and removed;
it is not an installed recommendation. Profiles remain an explicit caller choice.

Item counts count lifecycle events, not deduplicated tool calls: one command can
produce both started and completed records. Do not label these counts as the
number of executed commands. Usage-scope annotation follows the recorded CLI
version; a caller-supplied version is not runtime attestation. Never sum resumed
completion snapshots as separate turn costs. The observer does not call a model
provider SDK, but its Codex child can use network access and account quota.
