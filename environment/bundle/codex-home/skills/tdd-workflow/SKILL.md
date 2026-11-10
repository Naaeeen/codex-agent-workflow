---
name: tdd-workflow
description: Use red-green-refactor for new production behavior and bug fixes, and protect substantive refactors with meaningful regression tests using the project's existing test tools.
---

# Test-Driven Development

Use this for new production behavior, bug fixes and substantive refactors. Read
the applicable instructions, implementation, manifests and CI first. Use the
project's language, test runner and existing commands; examples from another
framework are not a reason to replace its tooling.

## Choose meaningful coverage

For a bug, first reproduce the wrong behavior with a failing regression test.
For new behavior, define its observable result, relevant error paths and boundaries
before implementation. Confirm the failure is the intended missing behavior,
not a broken fixture, unavailable dependency or syntax error.

A pure refactor can reuse adequate existing behavioral tests. Add a characterization
test only where a relevant gap exists; do not duplicate assertions solely to claim
that a new test was written. For documentation, configuration or a reversible
low-impact change, use its native checks and focused review where appropriate.

Honor the project's coverage requirement, including stricter thresholds. For new
production behavior target at least 80% where coverage tooling is supported, and
report measured scope and gaps. Do not invent a percentage, install a framework
solely to produce one, or treat high line coverage as proof that behavior is correct.

## Red, green, refactor

1. For new behavior or a bug fix, write or identify the smallest relevant behavioral
   test; run it and inspect the intended failure. For a covered pure refactor, run
   the existing green baseline and keep it green; do not manufacture a failure.
   Documentation/configuration uses its applicable native checks. Define expected
   values independently of the implementation.
2. Implement a cohesive fix without weakening assertions, suppressing errors or
   skipping failing tests to obtain green output.
3. Rerun the affected tests. Refactor when useful while preserving their behavior.
4. Run required checks and relevant integration/user-flow checks. For an interactive
   change, use a real browser when available; mocked tests or a build do not establish
   end-to-end success. Review the diff and obtain independent review for substantive
   code changes. After a fix, rerun affected checks.

Preserve unrelated edits and baseline failures. Existing skipped tests are reported
as skipped, never counted as passing; a pre-existing skip does not by itself justify
changing unrelated tests. New skips require a concrete reason and leave a stated
validation gap. A flaky failure is evidence to investigate, not something erased by
repeating until one run passes.

## Test design

- Assert observable behavior rather than private implementation details. Multiple
  assertions are useful when they describe one coherent behavior.
- Cover the affected boundaries and likely failure modes; avoid claiming all possible
  edge cases have been exhausted. Keep each case independent with controlled fixtures.
- Use mocks to isolate units, and real integrations where the affected boundary
  requires them. Distinguish mocked external success from a real service check.
- For browser tests, prefer accessible locators and condition-based waiting supported
  by the installed runner. Do not use arbitrary sleeps to conceal unstable behavior.
- Make dates, clocks and generated data deterministic when the scenario permits.
  Fixed dates in an old example must not silently become invalid current fixtures.
- Keep tests fast enough for the repository's feedback loop; use measured project
  budgets rather than universal millisecond limits. Never weaken required checks
  merely to label a run "fast".

Use existing watch mode or CI when it helps the task. Do not install hooks, add a
coverage-upload service or create remote jobs simply because an example suggests it.
If CI changes are requested, verify the action/API against its current primary
documentation and the project's pinning policy.

## Evidence

Preserve each command's actual exit status, including when capturing logs. Use
`verification-loop` if available for the detailed verification procedure. Report the
affected checks, counts, measured coverage if available, baseline failures, skipped
cases and what remains unverified. Stop repeating successful checks once the relevant
change and review findings have been verified.
