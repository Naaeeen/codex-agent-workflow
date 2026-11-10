# A process-local entry point; does not install shell integration or change PATH.
# Clear inherited WORKTRUNK_* overrides as well as isolating all config files.
# Otherwise an environment hook or LLM command could override the empty files.
$saved = @{}
foreach ($entry in @(Get-ChildItem Env: | Where-Object Name -Like 'WORKTRUNK_*')) {
    $saved[$entry.Name] = $entry.Value
}
$overrides = @{
    WORKTRUNK_CONFIG_PATH = (Join-Path $PSScriptRoot 'config.toml')
    WORKTRUNK_SYSTEM_CONFIG_PATH = (Join-Path $PSScriptRoot 'system.toml')
    WORKTRUNK_PROJECT_CONFIG_PATH = (Join-Path $PSScriptRoot 'project.toml')
}
foreach ($name in $overrides.Keys) {
    $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
try {
    foreach ($entry in @(Get-ChildItem Env: | Where-Object Name -Like 'WORKTRUNK_*')) {
        Remove-Item -LiteralPath "Env:\$($entry.Name)"
    }
    foreach ($name in $overrides.Keys) {
        [Environment]::SetEnvironmentVariable($name, $overrides[$name], 'Process')
    }
    & (Join-Path $PSScriptRoot 'git-wt.exe') @args
    $commandExit = $LASTEXITCODE
} finally {
    foreach ($entry in @(Get-ChildItem Env: | Where-Object Name -Like 'WORKTRUNK_*')) {
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
