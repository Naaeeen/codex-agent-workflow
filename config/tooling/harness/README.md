# Local task evidence ledger

`task_ledger.py` is a Python 3.11+ standard-library CLI for persisting a task's
objective, fixed workspace, evidence records and next action. It does not run
commands, call models or networks, read environment variables or credentials,
or inspect other sessions. It does not change Codex configuration.

Use an existing absolute workspace directory and an absolute task directory.
`--checks` is the path to a JSON array like `checks.example.json`; each check
requires exactly `id`, `description`, `required` (a JSON boolean), and `type`
(`artifact` or `review`). Initialization never overwrites an existing state.

```powershell
python .\task_ledger.py init --task-dir C:\project\task-ledger --workspace C:\project --objective "Finish and verify the change" --checks .\checks.example.json
python .\task_ledger.py record --task-dir C:\project\task-ledger --check verification --result pass --artifact C:\project\test-results.txt --note "Command, exit status and observed results are in the report" --expected-revision 1
python .\task_ledger.py record --task-dir C:\project\task-ledger --check review --result pass --artifact C:\project\review.txt --note "Review evidence recorded" --expected-revision 2
python .\task_ledger.py checkpoint --task-dir C:\project\task-ledger --next-action "Inspect final output" --note "Evidence collected"
python .\task_ledger.py resume --task-dir C:\project\task-ledger
python .\task_ledger.py complete --task-dir C:\project\task-ledger
```

All successful commands emit JSON to stdout and exit `0`. Validation or file
errors emit a JSON error to stderr and exit `2`. Argument errors use argparse's
normal usage error and exit `2`. `status` and `resume` are informational: they
can exit `0` with missing or stale evidence, so callers must inspect
`ready_to_complete` or call `complete` for an enforced completion gate.

A `pass` requires a regular artifact within the recorded workspace or task
directory. An artifact path may be absolute or relative to the workspace.
The ledger stores its absolute path, SHA-256 and byte length. `fail` and
`not-run` may be recorded without artifacts. A note alone never passes a check.
Links, Windows reparse points/junctions, hard links, parent traversal, network
paths, alternate data streams and ledger metadata are rejected. Files are
limited to 64 MiB. These checks reduce accidental or static path substitution;
they are not a sandbox against another process maliciously racing filesystem
changes or directly editing the ledger.

`status`/`resume` show every check, required missing/stale/failed/not-run lists,
the next action, all events and the failure history. Optional failures remain
visible but do not block completion. Previously completed state retains its
historical `status: complete` if a report later changes, while
`completion_currently_valid` and `ready_to_complete` become false and its
check becomes stale. Recording a new result or checkpoint returns the task
to `active`.

`complete` rehashes the current evidence and requires every required check to
pass, including at least one required review check. A review artifact proves
only that review evidence was recorded and is still present. The ledger cannot
verify the review's quality, author, independence, human identity or approval;
it cannot prove that a report's commands ran or its claims are true.

Mutations and reads acquire an exclusive `.ledger.lock`. Mutation commands
also accept `--expected-revision` to reject decisions based on older state.
State writes use a flushed temporary file and atomic replacement; a failed
replacement keeps the previous state. Filesystem/power-loss durability beyond
the OS's guarantees is not claimed. A crashed process may leave a lock file;
inspect its PID and confirm no writer is active before manually removing it.
Never delete a live writer's lock. A crash before replacement may also leave
an unused `.ledger-tmp-*` file; it is never loaded as state.

State is capped at 4 MiB, 128 checks and 512 events. When a limit is reached,
the command fails without truncating history. Archive the completed task and
start a separate ledger if more events are needed. A ledger is not a signed,
tamper-proof audit log; direct edits with internally consistent data cannot be
authenticated. Back it up using the project's normal file backup procedure.

Run verification from this directory:

```powershell
python -m unittest -v
python -m py_compile task_ledger.py test_task_ledger.py
```

## Native execution adapters

The sibling native-observer module runs an explicitly chosen Codex executable
and retains bounded metadata, not raw prompts, reasoning or tool output.
The native-eval-bridge module couples this to evals/ with a separate --execute
gate. It requires both normal execution and passing artifact checks. See each
module's README before use. Neither observes this desktop chat automatically.

Persistent runs use the Codex client's normal session storage; the observer
does not read that storage. In verified CLI0.166.0-alpha.6, completion usage is
a cumulative thread snapshot. Never sum resumed completion snapshots as
per-turn cost or infer model context size from them.

The optional skill-read-evidence library identifies supported literal skill
content reads from controlled execution events. It is not enabled automatically
and is not an OS file-access monitor. See its COLLECTOR.md for limits.

## Candidate improvement evidence

IMPROVEMENT.md describes the optional read-only improvement_bundle.py contract.
It rechecks explicitly declared source, workload, grader, result and review
dependencies before an improvement decision. A valid reject/defer can complete
the process; contract_valid is not a quality claim. It does not schedule model
runs, automatically update global instructions, or write personal memory.
