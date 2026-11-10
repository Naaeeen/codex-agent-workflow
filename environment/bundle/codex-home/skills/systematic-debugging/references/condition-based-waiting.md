# Investigate timing and asynchronous state

When a test passes only after a sleep or under a different schedule, identify the
event or state transition it actually needs. Check whether the operation was awaited,
whether the observation is stale, and whether another task changes the same resource.
Increasing a delay can hide the symptom without identifying the synchronization bug.

Prefer the existing framework's event, readiness, or retrying-assertion facilities.
Match the condition to the intended behavior: a listening port is not proof a service
is ready to answer its required request, and a page load is not proof its asynchronous
result has rendered.

If polling is necessary:

- Bound it with a timeout appropriate to the operation, and honor cancellation.
- Re-read the relevant state on each attempt; avoid a value captured before the loop.
- Use an explicit predicate so valid results such as `0`, `false`, or an empty string
  are not mistaken for absence.
- Poll an observation, not an operation that repeatedly creates side effects. Surface
  terminal errors promptly; retry only failures known to be transient for that API.
- Select a reasonable interval for the environment instead of enforcing one universal
  value. On timeout, report elapsed time and the last useful, redacted observation.
- For event listeners, check for an already-satisfied condition and clean up listeners
  or timers on completion, failure, or cancellation.

When time itself is the contract, such as debounce or expiry behavior, use the
project's controlled clock if it models that contract accurately. Keep integration
coverage for scheduling behavior that fake timers or mocks cannot represent.

Recheck the failure-inducing conditions after the correction, including relevant
ordering or concurrent work. Report the observed runs and failures; repeated passing
runs increase evidence but do not prove that all races are impossible.
