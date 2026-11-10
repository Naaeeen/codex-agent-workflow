> Source implementation notes: historical `results.json` references below refer to the original installation report, which is not included. For the exported package's 2026-11-10 test results, see [current verification](https://github.com/Naaeeen/codex-agent-workflow/blob/main/config/tooling/verification.json).

# Portable handoff and execution planning

This is a small, standard-library-only **data movement contract**, installed locally.
It has no provider SDK, account, upload, network request, executor, scheduler, or
global configuration change. A bundle's command and runtime recipe are data for
review. Preparing, verifying, or extracting a bundle never runs them.

## Advisory local/cloud/hybrid planning

`execution_plan.py` adds a pure `plan(task, capabilities, now=...)` function and a
read-only CLI. It does not dispatch a job. It has no hardcoded repository; the
caller supplies a fresh observed match between the current task repository and
the selected Codex Cloud environment.

```json
{
  "local_ui": false,
  "local_private_state": false,
  "os": "linux",
  "remote_separable": false,
  "linux_reproducible": true
}
```

The capability snapshot schema is:

```json
{
  "observed_at": "2026-11-06T01:00:00Z",
  "codex_cloud": {"available": false, "repo_match": false, "execution_authorized": false},
  "vercel": {"available": true, "execution_authorized": false}
}
```

These example values represent the declared preparation-only situation, not
live discovery; the example timestamp will expire. Do not refresh a timestamp
without refreshing observations. Run `python execution_plan.py task.json
capabilities.json` to receive `route`, `provider`, `reasons`, `gates`, and
`advisory_only`. Snapshots older than 15 minutes or over one minute in the future
produce a local plan with a refresh gate.

Local UI, private-state access and Windows/macOS work cannot migrate as a whole.
An explicitly separable, Linux-reproducible remote unit can produce a hybrid
plan, while the remaining parts stay on the machine. A separable-unit claim alone
never establishes that the whole task can move. A whole task declared Linux
reproducible with no local requirement and `remote_separable: false` can produce a cloud plan. The planner
prefers an available, repository-matched, execution-authorized Codex Cloud
environment, then an available execution-authorized Vercel capability. Missing
readiness or permission produces a local plan and explanatory gates.

Every boolean is an **unverified input claim**, including
`execution_authorized`: a true value is not a grant of safe execution. Before
actual execution the caller must verify live provider/environment/repository
IDs, runtime compatibility, scoped user permission, current budget and billing
authorization, and the input/output data boundary. A provider's availability or
a preparation request does not permit paid execution. This module cannot
perform these checks or authorize spending. `test_execution_plan.py` contains
eight table-driven routes/counterexamples and schema rejection checks.

## Contract and limits

`spec.json` names every input explicitly and declares the runtime recipe, command
argv, relative cwd, timeout (1–60 seconds), exact allowed outputs, per-output byte
limit and expected SHA-256, and human-readable acceptance statements. Inputs are
read individually; source trees, home, and `.codex` are never auto-collected.
`fixture.bundle.json` contains the contract plus each file's relative path, size,
SHA-256 and base64 bytes. It is self-contained and independent of this machine's
paths. Packages are limited to 12 MiB, decoded files to 1 MiB each / 8 MiB total,
and 64 files per input/output set. JSON duplicate keys are rejected.

Paths use portable slash-separated names. Absolute, traversal, UNC, Windows
device/ADS, reserved-name, case-collision, file/directory-collision and common
secret/private-state paths are rejected. Reads reject symlinks, Windows junctions
and reparse points, hardlinks, oversized files and changes detected during reads.
The safety helpers were copied without modification from the local task ledger;
`safe_io.py` records the source and source hash. No global import is required.

Every member is validated before extraction starts. Extraction requires an
absent destination under an existing parent and uses exclusive creation, so an
existing directory or file is never overwritten. A later I/O failure can leave an
incomplete newly created directory; delete it only after inspecting it, then
retry into a new destination. Collection rejects missing/unexpected files and
directories, changed input bytes, links, and nonmatching output sizes/hashes.
Results are bound to the canonical bundle SHA-256; `verify-result` and
`extract-result` validate the binding, output allowlist, bytes and expected hashes.

## Local commands

Run from this directory with an existing Python 3.11+ interpreter. Targets below
must not already exist; use new names for each replay.

```powershell
python handoff.py prepare fixture spec.json candidate.bundle.json
python handoff.py verify candidate.bundle.json
python handoff.py extract candidate.bundle.json new-clean-workspace
```

Execution is an explicit separate step. Inspect the locally authored fixture
first; the checked-in proof used `subprocess.run([sys.executable, '-I', 'main.py'],
cwd=clean_directory, timeout=5, capture_output=True, check=True)`. This executes
only the known fixture and enforces a five-second parent wait timeout. Then:

```powershell
python handoff.py collect candidate.bundle.json new-clean-workspace candidate.result.json
python handoff.py verify-result candidate.bundle.json candidate.result.json
python handoff.py extract-result candidate.bundle.json candidate.result.json new-return-directory
python -m unittest -v test_handoff.py
```

The reusable non-sensitive provider test input is `fixture.bundle.json` (two
files, sum 13 + 29). `evidence/` records a real local replay in another clean
directory and verified return. `results.json` records tests and limitations.
A future cloud adapter must separately obtain execution/upload authorization,
inspect provider isolation and runtime, honor declared timeout and output
allowlist, and verify the returned package. No cloud execution has been run. A separate Windows-to-WSL Linux replay also passed; WSL remains local execution.

## What these checks do not establish

SHA-256 detects changed bytes relative to a contract; it does not authenticate
who wrote the contract. Anyone able to rewrite an entire bundle can rewrite its
hashes. Human acceptance statements are carried as text, while only declared
output hashes/sizes are mechanically checked. The common secret filename filter
is deliberately incomplete: it cannot detect secrets placed in ordinary files,
command arguments, recipes, or output text. Review selected bytes before sharing.

This is not an OS sandbox or a permission boundary. A timeout is not process-tree
containment. Extraction/read checks assume trusted, quiescent local parent
directories; an adversary concurrently replacing filesystem entries can race
path-based checks. A separate executor/provider must supply isolation, resource
limits, network policy and process-tree cleanup appropriate to untrusted code.
The code does not run untrusted bundle commands at all.

## Acceptance and evidence loop

The chosen representation is bounded JSON/base64 instead of ZIP: it avoids
archive link metadata and ambiguous extraction rules with only stdlib, at the
cost of base64 overhead and whole-package memory. The candidate is intentionally
small; it does not try to package dependencies or infer runtime requirements.
Checks cover a deterministic clean replay/return and negative path, link,
integrity, size, missing, overwrite and unexpected-output cases. Review findings
are reconciled in `results.json`. These are local functional and model review
results, not evidence of cloud behavior or general agent quality.
