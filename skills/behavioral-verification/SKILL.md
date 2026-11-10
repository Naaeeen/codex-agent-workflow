---
name: behavioral-verification
description: Reproduce and verify production behavior changes with the existing project's tests, native checks and real user-flow boundaries while preserving failures and scope.
---

# Behavioral verification

Choose checks from applicable project rules, manifests, lockfiles, CI and the affected behavior. Do not install a test framework simply to satisfy a generic checklist.

For bugs, capture expected versus actual behavior with minimal input, relevant revision/runtime and real failure. Separate application faults from missing services, permissions, network and toolchain faults. State a hypothesis, predicted outcome and falsifier; use the smallest experiment that distinguishes causes rather than bundling speculative edits.

For new production behavior or bugs:

1. Define expected behavior independently of implementation. Run a meaningful regression test and confirm it fails for the intended reason.
2. Make a cohesive change using current project style, types and failure contracts. Do not weaken assertions, silently catch failures or skip tests to achieve green.
3. Run the affected tests; refactor if useful. Covered pure refactors can preserve an existing green baseline without inventing a red test.
4. Run required build/type/lint/integration checks and inspect the final staged, unstaged and untracked scope. Preserve unrelated work and baseline failures. Obtain independent review for substantive changes and rerun affected checks after fixes.

Use actual coverage tooling and project thresholds; the owner's default target for supported new behavior is at least 80%, with measured scope and gaps. Percentage alone does not prove correctness. Documentation/configuration uses native validation, not invented application coverage.

Changed interactive flows need actual browser operations when available. Claims about service/storage require checks at that boundary. Render visual artifacts and inspect actual content and dimensions. Mocks, builds, browser checks and human evaluations support different conclusions.

Preserve original exit status before formatting logs. A timeout, missing command or truncated result is not PASS. Retain failed/flaky outcomes; one later pass does not erase them. Report PASS, FAIL, NOT RUN, ABORTED, INFRASTRUCTURE FAILURE or NOT APPLICABLE with scope and reasons.

Example: date-range export must pass boundary fixtures, actual download and content checks; a success toast cannot prove file correctness. Stop repeating green checks absent new changes or unresolved evidence.
