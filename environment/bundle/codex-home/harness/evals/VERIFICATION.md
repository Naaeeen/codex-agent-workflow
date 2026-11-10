# Historical verification record — 2026-11-05

This preserves the source implementation's earlier record. Timing and review chronology below are historical claims, not the new package run. The exported package was retested on 2026-11-10; see the sanitized [current verification summary](https://github.com/Naaeeen/codex-agent-workflow/blob/main/config/tooling/verification.json). Original generated coverage files and raw test output are not included because they contain local paths. Running verify.py creates new reports for the reader's own environment.

## Implemented scope

Only the staged `eval-suite/` subtree was authored. All inputs are synthetic.
No actual model was invoked, no network request was made, no package was
installed, and no private project, credential store or conversation was read.

Implemented: eight fixed case fixtures/prompts, grader-owned behavior checks,
four calibration overlays per case, preparation with unique workspaces and
frozen-input hashes, bounded final-answer ingestion, scope comparison, explicit
failure categories, selftests and an optional local coverage wrapper.

## Observed final verification

Command: `python -B verify.py`

- Python 3.14.3; Node 24.15.0; the available `pwsh` is PowerShell 7.6.9.
- 28 unittest methods passed; zero failures, errors or skips.
- The calibration method exercised all 8 cases × 4 overlays = 32 artifact
  outcomes. Every good/alternative result passed; every plausible-bad and
  out-of-scope result failed.
- C1/C2/C3 behavior was executed through real Python/Node/PowerShell subprocesses.
- The controlled timeout test confirmed the child actually started, then released
  its write condition only after the timeout handler returned. It did not survive
  to write its marker. This verifies that controlled process tree, not arbitrary
  detached-process containment.
- Elapsed time under coverage: 46.606 seconds in the recorded final run.
- Executable-line coverage: `runner.py` 91.4% of 220 lines;
  `graders/checks.py` 92.3% of 259 lines. This is stdlib line coverage, not branch
  coverage, test quality, model reliability or user-task coverage.
- Model calls: zero. No UI/visual review or independent real-agent task trial was
  performed by this implementation worker.

The original run wrote `verification/results.json`, unittest output and source-line reports. Those historical generated files are not included. The wrapper preserves the test
exit status. A preliminary invocation of `python -m trace --module unittest`
returned a misleading shell status despite test failures, so it is not used as
the pass/fail gate.

## Red/green refinements preserved in the tests

1. The initial contract test run failed because the runner did not yet exist.
2. The first eight-case implementation passed its original ten tests and 32
   calibration outcomes. Further negative examples exposed false passes; that
   first green result was not accepted as sufficient.
3. New tests first demonstrated wrong HTML activity labels, inline handlers,
   remote inline CSS/srcset and missing attendee facts were accepted. Grading now
   checks time/activity relationships, static resources and the omitted facts.
4. Document count matching accepted `112/20` for `12/0`. Numeric boundaries fixed
   it; a subsequent valid prose alternative ending in a period exposed an
   overstrict boundary, which was corrected without changing the task or golden.
5. Independent review reproduced C1/C2 early `exit(0)` bypasses. Fresh grader-owned
   completion markers are now required after the assertions; regression examples
   preserve the comment where needed so they test completion rather than another
   unrelated check.
6. Independent review reproduced C3 timeout exits being accepted as a successful
   rejection. Every negative subprocess case now requires normal completion,
   excluding timeouts and output-limit termination.
7. Independent review reproduced a later output interval retaining an input alias.
   C1 now mutates each mutable result interval, checking original input after each.
8. Independent review reproduced `PYTHONOPTIMIZE=1` disabling Python assertions.
   C1 now uses explicit checks and isolated Python; hook/optimization environment
   variables are removed from the grader's copied subprocess environment without
   reading or logging their values.
9. The controlled child test was changed from a timing-only marker to a ready/
   release handshake: coverage overhead had allowed the original child workload
   to finish before the timeout. The revised test distinguishes surviving after
   termination from finishing before it.
10. Coverage initially omitted the controller because stdlib trace cached an
    ignore decision by the shared `runner` basename. `verify.py` filters exact
    source paths and includes import execution and I/O threads.

## Remaining boundaries

- The fixture directory and receipt are integrity checks, not an OS security
  boundary or a signature. They cannot prevent malicious reads, hostile races or
  changes outside the tracked workspace under unrestricted permissions.
- A completion marker is a guard against accidental/early termination, not an
  adversarial grader-isolation mechanism.
- HTML is not visually verified. Prose checks enforce explicit factual contracts;
  they do not establish full semantic quality, naturalness or teaching efficacy.
- Workflow compliance and native model settings/usage must be captured by the
  parent dispatcher. They are not inferred from the artifact.
- Current-environment task outcomes and guidance A/B remain NOT RUN here.
- Final independent review is owned by the parent agent; targeted reviewer
  reproductions and fixes are documented above, but this file does not substitute
  for the parent's final acceptance.
