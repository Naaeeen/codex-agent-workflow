param([Parameter(Mandatory=$true,Position=0)][ValidateSet('pw','ab')][string]$Tool,[Parameter(Mandatory=$true,Position=1)][string]$Workspace,[Parameter(Mandatory=$true,Position=2)][string]$Session,[Parameter(ValueFromRemainingArguments=$true)][string[]]$CommandArgs)
& '{{CODEX_HOME}}\tools\agent-kit\runtime\node-v24.22.2-win-x64\node.exe' (Join-Path $PSScriptRoot 'runner.mjs') $Tool $Workspace $Session @CommandArgs
exit $LASTEXITCODE
