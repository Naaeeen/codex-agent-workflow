param(
    [Parameter(Mandatory=$true)][string]$Config,
    [Parameter(Mandatory=$true)][string]$Target,
    [switch]$ErrorOnFindings
)
$runnerArgs = @((Join-Path $PSScriptRoot 'candidate\semgrep-local.py'), '--config', $Config, '--target', $Target)
if ($ErrorOnFindings) { $runnerArgs += '--error' }
& (Join-Path $PSScriptRoot 'candidate\venv\Scripts\python.exe') -I @runnerArgs
exit $LASTEXITCODE
