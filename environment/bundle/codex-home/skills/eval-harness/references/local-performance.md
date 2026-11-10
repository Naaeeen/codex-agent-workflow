# Local performance comparisons

The pinned launcher route `agent-tool.ps1 hyperfine` runs the installed CLI.
Use it for authorized local commands after verifying their outputs are equivalent.
Do not time live model/API calls as an implicit paid benchmark. Declare fixtures,
warmup/cache conditions, repetitions and correctness criteria before measuring.

Example: `agent-tool.ps1 hyperfine --runs 5 --warmup 1 --metrics time_wall_clock --export-json TASK_DIR/bench.json "python baseline.py" "python candidate.py"`

This installed major version defaults to shell=none. Shell pipelines and setup,
prepare or cleanup commands execute code and need the same task authority as
the measured command. Exported JSON has schema_version=2, results[].measurements
and explicit summary metrics/units. Preserve failures; ignore-failure cannot
turn an invalid candidate into a winner. Windows peak RSS is unsupported.
Report median/dispersion and conditions; a delay-fixture test proves plumbing,
not real speedup. Never sum cumulative native thread usage as per-turn cost.

Source: https://github.com/sharkdp/hyperfine/releases/tag/v2.0.0
