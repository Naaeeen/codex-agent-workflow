# Improvement contract

Use the existing task ledger for work completion and the installed
`agent-tool.ps1 improvement-verify EXPERIMENT_DIRECTORY` to verify the declared
artifact/trial/review bundle. Read the local harness IMPROVEMENT.md for its exact
format. The verifier only checks structure, hashes and declared references. It
does not prove a trial ran, a citation supports a claim or a reviewer is independent.

Start from an observed issue, keep baseline bytes, state one changed factor and
define a useful falsifier. Freeze the task/grader/environment and preserve every
planned result. Use development cases for iteration, separate held-out cases for
acceptance, and negative controls for behavior that must remain intact. Do not
invent a held-out set after seeing results or optimize on the final test set.

Compare task success, regressions and cost, not just polish or a self-judge score.
Keep the original user task and its external checks outside the editable harness.
A limitation-free answer is not necessarily better; necessary input validation
is not redundant defense. Use blind prose comparisons where useful, and report
model judgments separately from actual human understanding.

Review the final revision and its evidence dependencies. Adopt only within the
tested scope and existing authorization, then verify the applied file hashes;
otherwise reject or defer. Re-run the bundle validator before using its result
in the ledger. It complements the ledger rather than changing complete into a
quality score. No daemon, automatic self-promotion or personal-memory write is
installed by this workflow. Revisit when new evidence warrants it, not after
every ordinary task.

Research compared: https://github.com/google-research/harness2 ;
https://github.com/google-research/rrsi ; https://github.com/gepa-ai/gepa ;
https://dspy.ai/current/api/optimizers/MIPROv2/
