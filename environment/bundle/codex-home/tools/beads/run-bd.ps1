# A process-local entry point. Do not dot-source this script.
# Disables usage metrics and the separate OpenTelemetry SDK for this invocation.
# Dolt auto-push is off. Caller environment is restored even if execution fails.
$saved = @{}
$overrides = @{
    BD_DISABLE_METRICS = '1'
    BD_DISABLE_EVENT_FLUSH = '1'
    DO_NOT_TRACK = '1'
    BD_OTEL_ENABLED = 'false'
    OTEL_SDK_DISABLED = 'true'
}
foreach ($entry in @(Get-ChildItem Env: | Where-Object Name -Like 'BD_OTEL_*')) {
    $saved[$entry.Name] = $entry.Value
}
foreach ($name in $overrides.Keys) {
    $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
try {
    foreach ($entry in @(Get-ChildItem Env: | Where-Object Name -Like 'BD_OTEL_*')) {
        Remove-Item -LiteralPath "Env:\$($entry.Name)"
    }
    foreach ($name in $overrides.Keys) {
        [Environment]::SetEnvironmentVariable($name, $overrides[$name], 'Process')
    }
    & (Join-Path $PSScriptRoot 'bin/bd.exe') --sandbox @args
    $commandExit = $LASTEXITCODE
} finally {
    foreach ($entry in @(Get-ChildItem Env: | Where-Object Name -Like 'BD_OTEL_*')) {
        Remove-Item -LiteralPath "Env:\$($entry.Name)" -ErrorAction SilentlyContinue
    }
    foreach ($name in $saved.Keys) {
        if ($null -eq $saved[$name]) {
            Remove-Item -LiteralPath "Env:\$name" -ErrorAction SilentlyContinue
        } else {
            [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process')
        }
    }
}
exit $commandExit
