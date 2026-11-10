# Portable entry for the source-backed commands included in this package.
# No global configuration, installations or model calls occur on --help.
$ErrorActionPreference = 'Stop'
$routes = @{
    'task' = 'harness/task_ledger.py'
    'improvement-verify' = 'harness/improvement_bundle.py'
    'eval' = 'harness/evals/runner.py'
    'observe' = 'harness/native-observer/native_observer.py'
    'eval-native' = 'harness/native-eval-bridge/native_eval.py'
    'handoff' = 'harness/portable-handoff/handoff.py'
    'execution-plan' = 'harness/portable-handoff/execution_plan.py'
}
$arguments = @($args)
if ($arguments.Count -eq 0 -or $arguments[0] -in @('--help', '-h')) {
    Write-Output ('Usage: workflow-tool.ps1 TOOL [arguments]; tools: ' + (($routes.Keys | Sort-Object) -join ', '))
    Write-Output 'Requires Python 3.11+ on PATH. observe/eval-native run an explicitly supplied CLI; review authorization and cost before invoking.'
    exit 0
}
$tool = [string]$arguments[0]
if (-not $routes.ContainsKey($tool)) {
    [Console]::Error.WriteLine('Unsupported tool. Run workflow-tool.ps1 --help.')
    exit 2
}
$python = Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1
$remaining = @($arguments | Select-Object -Skip 1)
if ($tool -eq 'improvement-verify' -and $remaining.Count -eq 1 -and $remaining[0] -in @('--help', '-h')) {
    Write-Output 'Usage: workflow-tool.ps1 improvement-verify BUNDLE_DIRECTORY'
    Write-Output 'Validates improvement.json and declared artifacts inside the selected directory. Does not run a model.'
    exit 0
}
& $python.Source -B (Join-Path $PSScriptRoot $routes[$tool]) @remaining
exit $LASTEXITCODE
