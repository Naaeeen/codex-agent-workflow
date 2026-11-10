# Deliberately not an advanced PowerShell function: common parameters such as
# --error/--verbose belong to the selected native tool and must pass unchanged.
$ErrorActionPreference = 'Stop'
$supported = @('rea','repomix','ast-grep','serena','docling','marimo','inspect','task','eval','audit','observe','eval-native','duckdb','hyperfine','typos','lychee','trafilatura','pdf-layout','gitnexus','beads','worktrunk','qmd','mise','pixi','mcp-inspector','semgrep','improvement-verify','browser','pi-lab','handoff','execution-plan')
$arguments = @($args)
# Preserve the legacy named-parameter order with ToolArguments before Tool.
if ($arguments.Count -gt 0 -and [string]$arguments[0] -match '^-{1,2}ToolArguments(?::(.*))?$') {
    $inlineArgument = $Matches[1]
    $marker = -1
    for ($index = 1; $index -lt $arguments.Count; $index++) {
        if ([string]$arguments[$index] -match '^-{1,2}Tool(?::.*)?$') { $marker = $index; break }
    }
    if ($marker -gt 0) {
        $namedArguments = @()
        if ($inlineArgument) { $namedArguments += $inlineArgument }
        if ($marker -gt 1) { $namedArguments += $arguments[1..($marker-1)] }
        $toolTokens = @($arguments[$marker..($arguments.Count-1)])
        $toolEnd = if ($toolTokens[0] -match '^-{1,2}Tool:.+') { 1 } else { 2 }
        if ($toolTokens.Count -ge $toolEnd) {
            $tail = if ($toolTokens.Count -gt $toolEnd) { @($toolTokens[$toolEnd..($toolTokens.Count-1)]) } else { @() }
            $arguments = @($toolTokens[0..($toolEnd-1)]) + @('-ToolArguments') + $namedArguments + $tail
        }
    }
}
if ($arguments.Count -eq 0 -or $arguments[0] -in @('--help','-h','-?')) {
    Write-Output ('Usage: agent-tool.ps1 TOOL [arguments]; tools: ' + ($supported -join ', '))
    exit 0
}
$toolPosition = 0
$inlineTool = $null
if ([string]$arguments[0] -match '^-{1,2}Tool:(.+)$') {
    $inlineTool = $Matches[1]
} elseif ($arguments[0] -in @('-Tool','--tool','-Tool:','--tool:')) { $toolPosition = 1 }
$selectedTool = if ($inlineTool) { $inlineTool } elseif ($arguments.Count -gt $toolPosition) { $arguments[$toolPosition] } else { $null }
if ($selectedTool -notin $supported) {
    [Console]::Error.WriteLine('Expected a supported tool name. Run agent-tool.ps1 --help.')
    exit 2
}
$Tool = [string]$selectedTool
$ToolArguments = @()
if ($arguments.Count -gt $toolPosition + 1) {
    $remaining = @($arguments[($toolPosition + 1)..($arguments.Count - 1)])
    if ($remaining[0] -in @('-ToolArguments','--ToolArguments','-ToolArguments:','--ToolArguments:')) {
        $remaining = if ($remaining.Count -gt 1) { @($remaining[1..($remaining.Count-1)]) } else { @() }
    } elseif ([string]$remaining[0] -match '^-{1,2}ToolArguments:(.*)$') {
        $remaining[0] = $Matches[1]
    }
    # Preserve array-valued -ToolArguments from PowerShell callers as well as
    # the ordinary flat argv received from powershell -File.
    $ToolArguments = [string[]]@($remaining | ForEach-Object { $_ })
}
$toolsRoot = Split-Path -Parent $PSScriptRoot
$codexRoot = Split-Path -Parent $toolsRoot
$nodeDir = Join-Path $PSScriptRoot 'runtime\node-v24.22.2-win-x64'
$node = Join-Path $nodeDir 'node.exe'
$python = Join-Path $codexRoot 'harness\runtime\Scripts\python.exe'
$saved = @{}
$updates = @{}
if ($Tool -in @('browser','pi-lab')) {
    $updates['NODE_OPTIONS'] = $null
    $updates['NODE_PATH'] = $null
}
if ($Tool -eq 'serena') {
    $updates['SERENA_HOME'] = Join-Path $toolsRoot 'serena\state'
    $updates['PATH'] = (Join-Path $toolsRoot 'serena\venv\Scripts') + ';' + $nodeDir + ';' + $env:PATH
}
if ($Tool -eq 'docling') {
    $updates['HF_HOME'] = Join-Path $toolsRoot 'docling\model-cache'
    $updates['DOCLING_ARTIFACTS_PATH'] = Join-Path $toolsRoot 'docling\models'
    $updates['HF_HUB_DISABLE_TELEMETRY'] = '1'
    $updates['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
}
$code = 1
try {
    foreach ($key in $updates.Keys) {
        $saved[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $updates[$key], 'Process')
    }
    switch ($Tool) {
        'rea' { & $node (Join-Path $PSScriptRoot 'node_modules\rea-agents\scripts\rea.mjs') @ToolArguments }
        'repomix' { & $node (Join-Path $PSScriptRoot 'node_modules\repomix\bin\repomix.cjs') @ToolArguments }
        'ast-grep' { & (Join-Path $PSScriptRoot 'node_modules\@ast-grep\cli-win32-x64-msvc\ast-grep.exe') @ToolArguments }
        'serena' { & (Join-Path $toolsRoot 'serena\venv\Scripts\serena.exe') @ToolArguments }
        'docling' { & (Join-Path $toolsRoot 'docling\venv\Scripts\docling.exe') @ToolArguments }
        'marimo' { & (Join-Path $toolsRoot 'marimo\venv\Scripts\marimo.exe') @ToolArguments }
        'inspect' { & (Join-Path $toolsRoot 'inspect-ai\venv\Scripts\inspect.exe') @ToolArguments }
        'task' { & $python (Join-Path $codexRoot 'harness\task_ledger.py') @ToolArguments }
        'improvement-verify' { & $python (Join-Path $codexRoot 'harness\improvement_bundle.py') @ToolArguments }
        'browser' { & (Join-Path $toolsRoot 'browser-lab\browser-lab.ps1') @ToolArguments }
        'pi-lab' { & (Join-Path $toolsRoot 'pi-lab\run-trial.ps1') @ToolArguments }
        'handoff' { & $python '-E' '-s' (Join-Path $codexRoot 'harness\portable-handoff\handoff.py') @ToolArguments }
        'execution-plan' { & $python '-E' '-s' (Join-Path $codexRoot 'harness\portable-handoff\execution_plan.py') @ToolArguments }
        'eval' { & $python (Join-Path $codexRoot 'harness\evals\runner.py') @ToolArguments }
        'audit' { & $python (Join-Path $PSScriptRoot 'env_audit.py') 'audit' @ToolArguments }
        'observe' { & $python (Join-Path $codexRoot 'harness\native-observer\native_observer.py') @ToolArguments }
        'eval-native' { & $python (Join-Path $codexRoot 'harness\native-eval-bridge\native_eval.py') @ToolArguments }

        'duckdb' { & (Join-Path $toolsRoot 'utility-kit\duckdb\2.0.0\bin\duckdb.exe') '-no-agent' @ToolArguments }
        'hyperfine' { & (Join-Path $toolsRoot 'utility-kit\hyperfine\2.0.0\bin\hyperfine.exe') @ToolArguments }
        'typos' { & (Join-Path $toolsRoot 'utility-kit\typos\1.52.0\bin\typos.exe') @ToolArguments }
        'lychee' { & (Join-Path $toolsRoot 'utility-kit\lychee\0.24.2\bin\lychee.exe') @ToolArguments }
        'trafilatura' { & (Join-Path $toolsRoot 'utility-kit\trafilatura\2.3.1\venv\Scripts\trafilatura.exe') @ToolArguments }
        'pdf-layout' { & (Join-Path $toolsRoot 'pdf-layout\venv\Scripts\python.exe') (Join-Path $toolsRoot 'pdf-layout\layout_extract.py') @ToolArguments }

        'gitnexus' { & (Join-Path $toolsRoot 'gitnexus\run-gitnexus.ps1') -ToolArgs $ToolArguments }
        'beads' { & (Join-Path $toolsRoot 'beads\run-bd.ps1') @ToolArguments }
        'worktrunk' { & (Join-Path $toolsRoot 'worktrunk\run-wt.ps1') @ToolArguments }
        'qmd' { & (Join-Path $toolsRoot 'qmd\qmd-workflow.ps1') @ToolArguments }
        'mise' { & (Join-Path $toolsRoot 'mise\mise.ps1') @ToolArguments }
        'pixi' { & (Join-Path $toolsRoot 'pixi\pixi.ps1') @ToolArguments }
        'mcp-inspector' { & (Join-Path $toolsRoot 'mcp-inspector\run-inspector.ps1') -ToolArguments $ToolArguments }
        'semgrep' { & (Join-Path $toolsRoot 'semgrep\candidate\venv\Scripts\python.exe') '-I' (Join-Path $toolsRoot 'semgrep\candidate\semgrep-local.py') @ToolArguments }
    }
    $code = $LASTEXITCODE
} finally {
    foreach ($key in $saved.Keys) {
        [Environment]::SetEnvironmentVariable($key, $saved[$key], 'Process')
    }
}
exit $code
