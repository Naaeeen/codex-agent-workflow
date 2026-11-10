---
name: systematic-debugging
description: Investigate application bugs, failing tests, build failures, and integration regressions using reproduction, discriminating experiments, and root-cause evidence. Use for software faults; agent execution failures belong to agent-introspection-debugging, and comparative agent evaluations belong to eval-harness.
---

# Systematic Debugging

Explain the failure with evidence and verify a scoped repair. Scale the investigation
to the uncertainty and impact: an obvious local defect may need only a reproducer,
one correction, and a regression check. Complex failures benefit from a short record
of observations, hypotheses, experiments, and results. No fixed phase ceremony is
required.

## Establish what failed

- Capture expected versus actual behavior, the smallest relevant input, the failing
  command or user action, its real exit status, and the first useful error or trace.
  Record the tested revision and relevant uncommitted changes when comparisons depend
  on them. If a fresh reproduction is unavailable, identify what evidence is historical.
- Check the actual runtime, dependency versions, working directory, configuration
  source, and recent relevant changes. Separate application defects from toolchain,
  permission, network, authentication, or missing-service failures before editing code.
  An environment fault is a possible root cause, not proof that the application failed.
- Reproduce in the existing test setup or an isolated fixture. Keep assertions that
  express intended behavior. For an intermittent failure, record the conditions and
  observed failures/runs; a later passing attempt does not erase the failure.
- Inspect only relevant logs and configuration. Do not dump environment variables,
  tokens, request bodies, or personal data. For secret propagation, record presence
  and source only; redact sensitive values and paths before sharing diagnostics.
  Preserve test failures when filtering output or collecting logs.

## Choose the next discriminating experiment

Distinguish observations from hypotheses. State a candidate cause, what result it
predicts, and what result would weaken it. Compare with a known working case from
the same codebase and version; check primary documentation when behavior is uncertain.
Prefer the smallest experiment that separates plausible causes over a bundle of
speculative edits. Change one causal factor where practical, and record confounders
when isolation is impossible.

Trace suspicious values or state transitions to their origin, especially across
processes and service boundaries. Read [root-cause-tracing.md](references/root-cause-tracing.md)
when the visible exception is downstream of its trigger or tests contaminate each
other. Read [condition-based-waiting.md](references/condition-based-waiting.md) for
asynchronous or order-dependent failures.

A negative experiment is useful evidence. Remove only your obsolete diagnostic or
speculative changes, preserving unrelated work. Revisit assumptions when successive
attempts reveal new symptoms or stop producing information. Seek narrower evidence,
research, or an independent review; do not infer an architectural defect from a fixed
number of failed attempts. Ask for input only when a material fact or authorization
is missing.

## Repair and demonstrate the result

For a code defect, capture a meaningful failing regression before the repair when
the project supports it. Confirm that it fails for the reported behavior, then make
the smallest cohesive correction and rerun the affected checks. A configuration or
environment repair may instead require its native validation and the original
operation; do not invent application tests for it.

Verify at the boundary that originally failed. A unit test or mock can support a
claim about local logic, but cannot prove a live integration or user flow works.
Keep required project checks and unresolved failures visible. Retain diagnostic
instrumentation only if its ongoing value justifies its privacy and runtime cost.

When urgent, an already-authorized reversible mitigation may precede full diagnosis.
Label it as mitigation, explain its limits, and continue root-cause work. Do not add
retries to a state-changing operation without checking its duplicate-effect behavior.
If the cause remains unresolved, report the leading explanations, evidence gaps,
and the next useful experiment rather than claiming certainty.

Report the supported cause, change, actual verification, and remaining limits. Do
not turn upstream anecdotes or a small number of passing runs into reliability rates.
