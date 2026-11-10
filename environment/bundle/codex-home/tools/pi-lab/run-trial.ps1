param([string]$OutputPath)
$ErrorActionPreference = 'Stop'
if (-not $OutputPath) { throw 'Supply a new absolute local trial directory; its parent must exist.' }
& (Join-Path $PSScriptRoot '../agent-kit/runtime/node-v24.22.2-win-x64/node.exe') (Join-Path $PSScriptRoot 'trial.mjs') $OutputPath
exit $LASTEXITCODE
