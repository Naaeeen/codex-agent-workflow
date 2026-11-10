# Improvement evidence bundle

`improvement_bundle.py` validates the declared evidence dependencies of an offline
experiment. It uses Python 3.11+ and the existing `task_ledger.py` safety helpers.
This is the installed read-only validator; it does not replace the task ledger.

The CLI reads `improvement.json` and its declared artifacts. It emits only
`{"status":"contract_valid","defects":[]}` (exit 0), or `contract_invalid`
with the first defect code (exit 2). It does not run experiments, apply changes,
write ledgers, schedule work, call models/networks, or update personal memory.

From the `workflow-kit` directory, run the shipped portable launcher:

```powershell
pwsh -NoProfile -File ./config/tooling/workflow-tool.ps1 improvement-verify 'C:\path\to\experiment'
```

The validator lives beside the trusted task_ledger.py; it needs no third-party
dependencies or PYTHONPATH configuration. Use an absolute experiment path.
Relative child paths are allowed, but parent traversal (including ../) is rejected.
The bundled improvement-example directory is intentionally invented test data;
it is not an actual model experiment or evidence for a change.

## Format

All object keys are exact; unknown or missing keys fail validation. IDs use the
ledger's `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}` format. See `improvement-example/improvement.json`
for the full JSON. The example is **invented test data**, not model execution,
human research, or an actual independent review. Its decision is `reject`, with
an unknown negative-control result retained; it deliberately cannot be adopted.

| Field | Contract |
|---|---|
| `version` | Integer `1`. |
| `hypothesis`, `changed_factor` | Nonempty, bounded text. Narrative claims are not evaluated. |
| `acceptance` | `{"min_delta": 0.5}`: finite nonnegative minimum candidate-minus-baseline score, checked per dev and heldout trial on adoption. All trials use the same declared score meaning. |
| `artifacts` | Nonempty list of `{id,path,sha256,requires}`. SHA-256 is lowercase hex; `requires` lists IDs of declared dependencies. Every listed file is rehashed, including transitive dependencies and unused declared artifacts. Cycles and undeclared IDs fail. |
| `workload` | Nonempty list of `{id,split,fixture}`. `split` is `dev`, `heldout` or `negative`; all three are required only for `adopt`. `reject` and `defer` accept the nonempty set of splits actually available. A fixture ID cannot cross splits. |
| `plan` | Nonempty list of `{id,case}` describing every intended trial. Every workload case must appear. |
| `trials` | Exactly one record per planned trial: `{id,case,baseline,candidate}`. Missing/extra/duplicate trials fail; a failed arm must remain present. |
| Each arm | `{bindings:{source,fixture,grader,environment},result:{status,score,evidence}}`. Each binding and `evidence` names a frozen artifact. A trial's two arms must use the same fixture, grader and environment; fixture must match its case. Each arm has one source artifact across all trials (bundle all source dependencies under it). |
| Result | `status` is `pass`, `fail`, `unknown`, `error`, `aborted` or `not-run`. `pass` requires a finite numeric score; other statuses require `score:null`. Every status requires a retained evidence file. A negative-control `pass` means the declared control expectation was met, not that an unsafe action succeeded. |
| `review` | `{evidence,independent,supports,bindings,protocol_sha256}`. `evidence` names a frozen review file; `independent` is boolean; `supports` equals `decision`. `bindings` maps **every artifact ID except the review evidence itself** to its current hash. |
| `decision` | `adopt`, `reject` or `defer`. All can form a valid completed evidence contract. `adopt` additionally requires all three splits, the independent-review declaration, every baseline/candidate result `pass` (including negative controls), and dev/heldout deltas meeting `min_delta`. All decisions retain every planned trial. |

Numeric `min_delta` applies only to the declared comparable scoring scheme. It
is not statistical significance or a general rule for automatic promotion.
When an honest diagnostic has no unseen heldout cases, use `defer` or `reject`;
do not relabel development examples or invent heldout evidence to satisfy `adopt`.

`review.protocol_sha256` binds the declarations and all trial records. Compute
SHA-256 of UTF-8 JSON containing exactly `version`, `hypothesis`, `changed_factor`,
`acceptance`, `artifacts`, `workload`, `plan`, and `trials`, serialized by
`json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)`.
List order is significant. This includes the review artifact's frozen hash, but
not the `review` object or `decision`; `review.supports` separately binds the
decision. `protocol()` and `digest()` implement that exact operation.

Paths must be relative to the experiment directory. Parent traversal, absolute,
drive-relative, UNC/device paths, alternate streams, manifest-as-evidence,
symlinks, hardlinks, and Windows junction/reparse paths fail. Limits: 256 items
per main list, 4 MiB manifest, 64 MiB per file and 128 MiB total artifacts.

## What a valid contract does not establish

`contract_valid` is **not `quality_pass`**. The validator cannot prove that a
trial ran, a plan was preregistered, a score is true, a reviewer is independent,
the changed factor is isolated, or a heldout fixture is semantically unseen. It
checks declared IDs for split overlap, not equivalent contents or information
leakage. It does not parse source imports, report links, package dependencies,
or undeclared references. Authors must enumerate those in `requires` and freeze
an actual environment declaration. Review identity and evidence truth need
independent verification outside this tool.

This is not a signed, tamper-proof log or a hostile concurrent-writer sandbox.
Consistent rewrites of the manifest and evidence can pass. Imported ledger
helpers reject unsafe static paths and changes during individual reads, but do
not provide an atomic snapshot of an entire directory. Keep the directory
quiescent during validation. Import resolution must use the trusted ledger
module, not an untrusted module placed on `PYTHONPATH`.

## Verification record

Tests were run locally on Python 3.14.3 / Windows: 25 tests, 24 passed, one
symbolic-link creation test skipped because Windows denied creation (1314).
Real hardlink and directory-junction rejection tests passed. Standard-library
`trace` measured 93.2% executable-line coverage of this validator; this is not
branch coverage or evidence of model quality. Python compilation passed.
An independent reviewer ran the same suite. Current limitations above remain.
