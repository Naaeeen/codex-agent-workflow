# Native artifact-evaluation bridge

This stdlib Python 3.11+ bridge connects the existing local artifact runner's
`prepare()` and `grade()` functions to the sibling frozen native observer.
It creates a new trial for every invocation. The default prepares a trial and
records its plan; it does not invoke Codex or inspect authentication.

## Commands

```powershell
# Prepare only. No model process or version probe runs.
python .\native_eval.py --case N1 `
  --runs-root 'C:\absolute\synthetic-trials' `
  --executable 'C:\absolute\pinned\codex.exe'

# Explicitly run one authorized synthetic trial in a fresh workspace.
python .\native_eval.py --case N1 `
  --runs-root 'C:\absolute\synthetic-trials' `
  --executable 'C:\absolute\pinned\codex.exe' `
  --cli-version 'codex-cli 0.166.0-alpha.6' --execute --timeout 120
```

Known cases are `C1`, `C2`, `C3`, `D1`, `D2`, `L1`, `R1`, `N1`. An optional
`--profile NAME` passes an existing validated profile name through
the observer. There are no arbitrary model, permission, argument or
configuration overrides. `--execute` is required for model invocation; it must
represent authorization already obtained by the caller. A subsequent command
always creates another trial, rather than silently continuing a prepared plan.

The runner is loaded from sibling `../evals/runner.py` in this package; the observer is
loaded from sibling `../native-observer/native_observer.py`. The bridge does not
change either module, the suite, or global configuration. The Python API is:

```python
run_case("N1", absolute_runs_root, absolute_executable,
         execute=True, profile=None, timeout_seconds=120,
         cli_version="codex-cli 0.166.0-alpha.6")
```

`execute` must be an actual boolean and defaults to `False`. Dependency and
observer-call injection parameters exist for deterministic tests, not as CLI
features. API results include the trial path for locating artifacts; saved
metadata identifies the trial by its generated ID.

## What is dispatched and saved

The native run uses `workspace-write`, ephemeral mode and the observer's
`--no-daemon` owned-process execution. Its prompt contains the prepared
`TASK.txt` text and minimal scope instructions listing only the allowed edit
paths. It does not contain the receipt, grader source, golden outputs, or other
cases. Existing TASK/AGENTS fixture files are produced by the established runner.

Beside the unchanged `receipt.json`, the bridge adds:

- `dispatch.json`: immutable request metadata, receipt/dependency/prompt hashes,
  selected case, execution gate, declared profile and fixed execution policy.
- `observer/metadata.json`: the observer's bounded allowlisted metadata, created
  only on actual execution and hash-linked from the evaluation.
- `evaluation.json`: allowlisted combined status and artifact-grade summary.

No new raw prompt copy, model answer, reasoning, command output or grader output
is stored. In particular, arbitrary grader check details and optional final
answers are discarded from the bridge summary. The runner's existing synthetic
workspace and the task's intentional artifact files remain available for review.
The bridge never rewrites a receipt or an old trial.

## Acceptance

`PASS` requires **both** a successful native observer result and `PASS` from the
actual artifact grader, plus an unchanged receipt and frozen controller,
observer and suite inputs. Correct files cannot convert a timeout, invalid
JSON, failed turn or nonzero native process into a pass. Conversely, native
completion cannot convert a wrong artifact or scope violation into a pass.
Missing/mismatched observer metadata is an infrastructure error. Changed
receipts or trusted inputs invalidate the trial.

Other statuses are `PREPARED`, `FAIL`, `INVALID_TRIAL`, and `INFRA_ERROR`. CLI
exit codes are 0 for PREPARED/PASS, 1 for FAIL, and 2 for invalid/infrastructure
errors. A PREPARED exit code is never evidence that a model ran or an artifact
passed. Artifact code execution follows the existing runner's current-OS-rights
policy; neither trial folders nor scope instructions are an OS security sandbox.
This bridge does not establish general model reliability, cost or workflow
compliance.

## Verification

```powershell
python -m unittest -v test_native_eval.py
python -m py_compile native_eval.py test_native_eval.py
```

Tests copy the real local suite to temporary storage and use its actual N1
artifact grader. Only the model observer is replaced with a deterministic
injected callback. They cover prepare-only and CLI gates, correct N1 output,
native failure despite correct output, wrong output despite native success,
scope violation, receipt/grader drift, observer exceptions/missing metadata,
and prompt/grader-output privacy canaries. No model, network, installation, or
global configuration changes are performed by these tests.

The local-analysis experiment profile was removed after showing no stable benefit; it is not installed by this bridge.
