param(
    [Parameter(Mandatory, Position = 0)]
    [string]$Destination,
    [string]$Python313,
    [string]$Python314,
    [string[]]$Group = @(),
    [switch]$Apply,
    [switch]$SkipModelWeights
)

$ErrorActionPreference = 'Stop'
$runner = if ($Python313) {
    (Resolve-Path -LiteralPath $Python313).ProviderPath
} elseif ($Python314) {
    (Resolve-Path -LiteralPath $Python314).ProviderPath
} else {
    (Get-Command python.exe -CommandType Application | Select-Object -First 1).Source
}

$arguments = @((Join-Path $PSScriptRoot 'install_dependencies.py'), $Destination, '--setup')
if ($Python313) { $arguments += @('--python313', $Python313) }
if ($Python314) { $arguments += @('--python314', $Python314) }
if ($Apply) { $arguments += '--apply' }
if ($SkipModelWeights) { $arguments += '--skip-model-weights' }
foreach ($value in $Group) {
    foreach ($name in $value.Split(',')) {
        $arguments += @('--group', $name.Trim())
    }
}
& $runner -E -s -B @arguments
exit $LASTEXITCODE
