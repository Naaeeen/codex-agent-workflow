# Local artifact evaluation suite

Eight fixed synthetic tasks for coding, documents, tutoring and research. The
controller uses Python's standard library. It does **not** call a model, install
packages, select a provider, read credentials, inspect chat history, or upload
anything. The parent agent dispatches each prepared task using native agents.

This suite checks artifacts and observable behavior. A `PASS` means the declared
deterministic checks passed; it is not proof of general agent quality, workflow
compliance, writing quality, educational effectiveness, or safe containment.

## Commands

Run from this directory with Python 3.11 or newer:

```powershell
python -B runner.py selftest
python -B verify.py
python -B runner.py prepare --case C1 --runs-root .\runs
python -B runner.py grade-existing --trial .\runs\C1-RETURNED_ID
```

`prepare` prints JSON containing the new trial, workspace and task-prompt paths.
It always creates a unique directory and never resets an existing trial. It
copies only synthetic case files, `TASK.txt`, and a scope-specific `AGENTS.md`.

The parent should give a **fresh native agent** the returned workspace and
`TASK.txt`, retain the user's current main model/effort, and collect the final
artifacts. The grading code, goldens, receipt and other cases are outside the
permitted edit scope. Native/CLI/desktop results must not be silently pooled.

The parent may save the final answer as exactly one of these files, beside
`receipt.json` and outside `workspace/`:

- `final-answer.txt`: UTF-8 text.
- `final-answer.json`: a UTF-8 JSON object.

The limit is 16 KiB. The answer is optional, bounded, ingested as data, and never
executed or treated as evidence that the task succeeded. Having both formats,
malformed JSON, an unsafe link or an oversized answer fails that check. Final
answer fields containing commands are inert data.

`grade-existing` emits JSON to stdout and does not write into the workspace.
Exit codes are 0 for `PASS`, 1 for `FAIL`, and 2 for `INVALID_TRIAL` or
`INFRA_ERROR`. Redirect the JSON to an operator-chosen report path if wanted.

## Fixed tasks and outputs

| Case | Required artifact / behavior | Deterministic checks |
| --- | --- | --- |
| C1 | `src/intervals.py` | Real Python execution, 8 input cases, 2 error cases, input mutation and output aliasing |
| C2 | `src/workflow.mjs`, `src/retry.mjs` | Real Node execution, returned values and call order, preserved string behavior |
| C3 | `Copy-ReceiptSet.ps1` | Real PowerShell execution on temporary synthetic files: Unicode/nesting, WhatIf, traversal, absolute path, missing source, duplicate destination, existing target, original preservation |
| D1 | `brief.html` | Source facts, time/activity relationships, semantic structure, print CSS, mailto contact, static offline resource checks |
| D2 | `release-notes.md`, `revision.json` | Source-linked status/count facts, unknown date, preservation of owner comment |
| L1 | `feedback.md`, `progress.json` | Chain-rule values, Chinese feedback, pending retest, no invented mastery |
| R1 | `synthesis.md`, `analysis.json` | Measured percentage changes, source IDs, claim classification, ignored synthetic instruction injection |
| N1 | `README.md` | Exact single typo correction, every other byte preserved |

Every file outside each case's explicit `allowed_edits` is protected, including
new unrequested files. `notes/keep.txt` is an unrelated-work sentinel. Workspace
hashes before and after grading also expose grader/runtime side effects.

## Calibration and frozen inputs

`golden/<case>/` contains four artifact overlays: `good`, `alternative`, `bad`,
and `scope-violation`. Selftests apply each overlay to a new prepared workspace.
Good and alternative must pass; plausible bad and scope violation must fail.
N1 has one byte-exact valid answer, so its two positive overlays are identical.

The golden overlays are **grader calibration**, not agent trials. Do not give
them to the evaluated agent. `build_assets.py` documents the synthetic inputs
and one-time construction; it refuses to overwrite existing files and should
not be rerun on a populated suite.

Preparation records SHA-256 hashes of the case fixture, prompt, suite manifest,
runner and all grader Python modules. Grading refuses changed/missing frozen
inputs or a mismatched receipt. A change requires a fresh prepared trial.
Receipts are checked against current canonical inputs; they are not signatures
and must not be represented as tamper-proof under unrestricted OS access.

## Boundaries and missing evidence

- Unique folders and checksums provide repeatability and contamination detection.
  They are **not a filesystem or network security sandbox**. Model-generated
  Python/JavaScript/PowerShell executes with current OS permissions. Only use
  trusted, authorized synthetic tasks in this environment.
- The runner does not inspect real configuration, credentials, environment
  values, conversations or projects. Subprocesses inherit the runtime environment
  needed to execute normally; this is not credential isolation.
- Fixed grader commands use argument arrays, timeouts, bounded captured output
  and process-tree termination. This limits common runaway cases but is not an
  adversarial execution service or a race-free multi-file transaction.
- C1 uses isolated Python with explicit checks that remain active under
  optimization. C1/C2 require a grader-owned fresh completion marker after all
  behavioral checks; a target calling exit(0) is not a successful test run.
  Grader subprocesses remove PYTHONOPTIMIZE/PYTHONPATH/PYTHONHOME and
  NODE_OPTIONS/NODE_PATH from their copied environment; values are not logged.
- C3's negative tests require a normal nonzero exit. A timeout or output-limit
  termination never counts as successfully rejecting an invalid request.
- C3 needs an installed PowerShell; C2 needs an installed Node. Missing runtimes
  produce `INFRA_ERROR`, never a pass. C1 uses the invoking Python.
- D1's structural checks do not establish page count, layout quality, contrast,
  clipping or accessibility in a real browser. Actual visual review is `NOT_RUN`
  until the parent obtains a permitted UI-capable subagent or human check.
  Select the subagent using current capability, relative cost and task complexity;
  a lower-cost model or lower reasoning effort is suitable when quality permits.
- D2/L1/R1 checks accept different prose around explicit factual contracts. They
  cannot detect every contradictory sentence, misleading implication, or weak
  explanation. Independent content review remains `NOT_RUN` until performed.
- A correct artifact does not prove tests were written before the fix, sources
  were consulted, or forbidden external actions did not occur. Tool-event review
  is separate; `workflow_compliance` remains `NOT_VERIFIED`.
- Grading time is measured. Model latency, token usage, model identity and
  reasoning effort are not inferred. The parent must record actual native
  dispatch metadata separately; unavailable values stay unknown.
- Failures and infrastructure errors must remain visible. A retry is a new trial;
  repairing the same workspace is not an independent sample or pass@k evidence.

## Comparison protocol

Start with eight single current-environment trials. For a specific guidance
decision, preregister a small matched A/B subset and its stopping rule, freeze
all shared inputs, alternate order, and use fresh workspaces. Retain every first
attempt and failure. A suggested diagnostic subset is C2, C3, R1 and N1, with
at most two differing cases receiving one additional matched pair each.

Both variants sharing today's global rules/tools constitute a **guidance
increment comparison under the current environment**, not a replay of the old
environment. Do not claim general reliability from this small synthetic suite.

## Verification

See `VERIFICATION.md` for actual commands, outcomes and remaining limitations.
No model trial is run by selftests or asset construction.
`verify.py` additionally saves a machine-readable result, full test output and
stdlib executable-line coverage under `verification/`, preserving test failure
exit status. This is line coverage of the controller/graders, not branch coverage
or agent-quality coverage.
