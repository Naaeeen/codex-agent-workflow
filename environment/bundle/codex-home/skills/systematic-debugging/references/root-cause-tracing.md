# Trace the failing value or state

Use this when the exception occurs after the original mistake, or when one test or
process changes state that a later operation consumes.

Start at the failing operation. Identify its relevant input, expected invariant,
actual value or state, and caller. Follow that input backward through transformations
until evidence explains the first divergence from the intended invariant. Read the
necessary implementation and contracts, including validation and error handling;
do not assume a similarly named example has the same contract.

For a multi-component path, use an existing safe correlation identifier or an
isolated fixture to connect observations. Inspect the smallest useful boundary:
whether the producer emitted the expected shape/state, whether the receiver got it,
and whether the intended configuration reached that process. Log types, presence,
state transitions, or safe synthetic identifiers instead of raw secrets or payloads.
Absence of a log is not proof an operation did not execute unless logging coverage
and collection are established.

Example: a file appears in the wrong directory. Confirm the operation's resolved
working directory and the caller's path source. An empty setting, premature fixture
access, or a relative path resolved in another process could explain it. Test the
candidate with an isolated temporary directory before performing another write.

Place the correction where the invariant should be established. Add boundary
validation where an independent entry path could bypass that guarantee or where a
trust boundary requires it. Do not duplicate checks at every layer without a reason;
logging by itself does not prevent a bug.

For test-state contamination:

- Compare the failing test alone with the relevant ordered group, using the project's
  installed runner. Record the actual order or seed, parallelism, and shared resources.
- Narrow the responsible preceding set when useful, but verify candidate interactions:
  a failure may require several tests together, so simple bisection can miss it.
- Use isolated state between experiments; verify the baseline rather than silently
  deleting an unexpected directory or reusing a contaminated fixture.
- Preserve runner exit status and distinguish an executed passing test from no tests
  collected, a setup failure, or an unavailable command.

A causal claim is stronger when the experiment isolates the trigger and the targeted
repair prevents the same failure while preserving the intended behavior. If only
correlation is established, say so.
