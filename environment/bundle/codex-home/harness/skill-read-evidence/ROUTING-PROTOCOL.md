# Attributable skill reads

Choose skills using the task and normal available descriptions. Read selected
SKILL.md content in a dedicated literal Get-Content -LiteralPath event; do not
mix it with project-file reads, assignments, tests, formatting or arbitrary
output. Do not name extra skills just to satisfy an audit. The unchanged
collector deliberately treats mixed/ambiguous sources as inconclusive.

routing_diagnostics.RoutingDiagnosticCollector adds hashes and fixed structural
counts/flags to the existing labels. It does not retain raw commands, output or
parse trees and does not relax the underlying classification. Unknown native
event/item types also prevent a conclusive negative result in a probe runner.

One fresh native debugging probe using this protocol confirmed a relevant skill,
preserved protected files and passed artifact checks with zero unknown reads.
The previous P1 remains inconclusive; its exact old commands were not retained.
The new defect fixture differs, so this is a protocol qualification, not a matched
accuracy A/B. Diagnostic unit tests include mixed reads and output contamination.
This is an opt-in audit protocol, not a full filesystem monitor or automatic hook.
