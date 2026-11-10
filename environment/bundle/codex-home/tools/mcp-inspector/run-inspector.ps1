param([Parameter(ValueFromRemainingArguments=$true)][string[]]$ToolArguments)
$ErrorActionPreference = 'Stop'
$toolsRoot = Split-Path -Parent $PSScriptRoot
$node = Join-Path $toolsRoot 'agent-kit\runtime\node-v24.22.2-win-x64\node.exe'
$entry = Join-Path $PSScriptRoot 'node_modules\@modelcontextprotocol\inspector\clients\cli\build\index.js'
$settings = @{
    MCP_INSPECTOR_SECRET_STORE = 'memory'
    MCP_STORAGE_DIR = (Join-Path $PSScriptRoot 'state')
    MCP_CATALOG_PATH = $null
    MCP_CLIENT_CONFIG_PATH = (Join-Path $PSScriptRoot 'state\client.json')
    MCP_INSPECTOR_OAUTH_STATE_PATH = (Join-Path $PSScriptRoot 'state\oauth-state.json')
    MCP_AUTO_OPEN_ENABLED = 'false'
    NODE_OPTIONS = $null
    NODE_PATH = $null
}
$before = @{}
$hasConfig = @($ToolArguments | Where-Object { $_ -eq '--config' -or $_.StartsWith('--config=') }).Count -gt 0
if (-not $hasConfig) {
    # The CLI ignores this environment default for ad-hoc command/URL targets.
    # An explicit --catalog would conflict with those supported target forms.
    $settings['MCP_CATALOG_PATH'] = Join-Path $PSScriptRoot 'state\mcp.json'
}
try {
    foreach($key in $settings.Keys) {
        $before[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $settings[$key], 'Process')
    }
    & $node $entry @ToolArguments
    $code = $LASTEXITCODE
} finally {
    foreach($key in $before.Keys) {
        [Environment]::SetEnvironmentVariable($key, $before[$key], 'Process')
    }
}
exit $code
