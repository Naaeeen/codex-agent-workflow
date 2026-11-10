#Requires -Version 7.0
# Scoped local CLI. No setup, remote services, embeddings, mutations, or MCP.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ToolArgs)

$ErrorActionPreference = 'Stop'
$toolRoot = $PSScriptRoot
$node = '{{CODEX_HOME}}\tools\agent-kit\runtime\node-v24.22.2-win-x64\node.exe'
$cli = Join-Path $toolRoot 'node_modules\gitnexus\dist\cli\index.js'
$registryPath = Join-Path $toolRoot 'workflow-state\registry.json'

function Fail([string]$Message) { throw "GitNexus wrapper: $Message" }
function Assert-SafePath([string]$Value) {
    if ($Value -match '[\x00-\x1f\x7f"''`&|<>^%!]') { Fail 'Path contains unsupported shell metacharacters or control characters.' }
}
function Read-Registry {
    if (!(Test-Path -LiteralPath $registryPath -PathType Leaf)) { return @() }
    return @(Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json)
}
function Assert-GraphOnlyIndex($Entry) {
    if ($null -eq $Entry.stats) { Fail 'Registered index lacks embedding-state metadata; use a separately reviewed workflow.' }
    $embeddingProperty = $Entry.stats.PSObject.Properties['embeddings']
    $embeddingCount = -1
    if ($null -eq $embeddingProperty -or ![int]::TryParse([string]$embeddingProperty.Value, [ref]$embeddingCount) -or $embeddingCount -ne 0) {
        Fail 'Registered index has embeddings or unknown embedding state; use a separately reviewed workflow.'
    }
}

try {
    if (!$ToolArgs -or $ToolArgs.Count -eq 0) { $ToolArgs = @('--help') }
    foreach ($arg in $ToolArgs) {
        if ([string]::IsNullOrWhiteSpace($arg) -or $arg -match '[\x00-\x1f\x7f]') { Fail 'Arguments must be nonempty and contain no control characters.' }
    }
    $command = $ToolArgs[0]
    $allowedCommands = @('analyze', 'query', 'context', 'impact', 'trace', 'status', 'list', '--help', '-h', '--version', '-V')
    if ($command -notin $allowedCommands) { Fail "Unsupported command '$command'. Allowed: analyze, query, context, impact, trace, status, list, --help, --version. MCP is not exposed by this wrapper." }

    $helpOnly = $ToolArgs.Count -eq 2 -and $ToolArgs[1] -in @('--help', '-h')
    $forward = [System.Collections.Generic.List[string]]::new()
    foreach ($arg in $ToolArgs) { $forward.Add($arg) }
    if ($command -in @('--help', '-h', '--version', '-V', 'list')) {
        if ($ToolArgs.Count -ne 1) { Fail "'$command' accepts no additional arguments in this wrapper." }
    } elseif (!$helpOnly) {
        $positionCounts = @{ analyze = 1; query = 1; context = 1; impact = 1; trace = 2; status = 0 }
        $positionCount = $positionCounts[$command]
        if ($ToolArgs.Count -lt (1 + $positionCount)) { Fail "'$command' is missing required positional arguments." }
        for ($i = 1; $i -le $positionCount; $i++) {
            if ($ToolArgs[$i].StartsWith('-')) { Fail 'Required positional arguments must precede flags.' }
        }
        $valueFlags = @{
            analyze = @('--name', '--workers')
            query = @('--repo', '--limit')
            context = @('--repo', '--file', '--uid', '--limit')
            impact = @('--repo', '--file', '--direction', '--depth', '--limit')
            trace = @('--repo', '--from-file', '--to-file', '--depth')
            status = @('--repo')
        }
        $switchFlags = @{
            analyze = @('--index-only')
            query = @('--content')
            context = @('--content')
            impact = @('--include-tests', '--summary-only')
            trace = @('--include-tests')
            status = @('--json')
        }
        $parsed = @{}
        for ($i = 1 + $positionCount; $i -lt $ToolArgs.Count; $i++) {
            $flag = $ToolArgs[$i]
            if ($parsed.ContainsKey($flag)) { Fail "Duplicate flag '$flag'." }
            if ($flag -in $valueFlags[$command]) {
                $i++
                if ($i -ge $ToolArgs.Count -or $ToolArgs[$i].StartsWith('-')) { Fail "Flag '$flag' needs a value." }
                $value = $ToolArgs[$i]
                if ($flag -in @('--workers', '--depth', '--limit')) {
                    $number = 0
                    $maximum = if ($flag -eq '--workers') { 16 } elseif ($flag -eq '--depth') { 32 } else { 10000 }
                    if (![int]::TryParse($value, [ref]$number) -or $number -lt 1 -or $number -gt $maximum) { Fail "Invalid value for '$flag'." }
                }
                if ($flag -eq '--direction' -and $value -notin @('upstream', 'downstream')) { Fail 'Direction must be upstream or downstream.' }
                if ($flag -in @('--file', '--from-file', '--to-file')) { Assert-SafePath $value }
                $parsed[$flag] = $value
            } elseif ($flag -in $switchFlags[$command]) {
                $parsed[$flag] = $true
            } else { Fail "Flag '$flag' is not allowed for '$command'." }
        }

        $registry = @(Read-Registry)
        if ($command -eq 'analyze') {
            $repoPath = $ToolArgs[1]
            Assert-SafePath $repoPath
            if (![IO.Path]::IsPathFullyQualified($repoPath) -or $repoPath.StartsWith('\\')) { Fail 'Analyze requires an absolute local repository path.' }
            if (!(Test-Path -LiteralPath $repoPath -PathType Container)) { Fail 'Repository directory does not exist.' }
            $repoPath = (Resolve-Path -LiteralPath $repoPath).Path
            if (!(Test-Path -LiteralPath (Join-Path $repoPath '.git'))) { Fail 'Analyze requires the Git repository root (.git must exist).' }
            if (!$parsed.ContainsKey('--name') -or $parsed['--name'] -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$') { Fail 'Analyze requires a unique --name containing letters, digits, dot, underscore or hyphen.' }
            foreach ($entry in $registry) {
                if ($entry.name -eq $parsed['--name'] -and $entry.path -ne $repoPath) { Fail 'That --name already belongs to another repository.' }
                if ($entry.path -eq $repoPath) { Assert-GraphOnlyIndex $entry }
            }
            $configPath = Join-Path $repoPath '.gitnexusrc'
            if (Test-Path -LiteralPath $configPath) {
                $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json -AsHashtable
                $safeKeys = @('defaultBranch', 'branch', 'skipAgentsMd', 'skipContextFiles', 'skipAiContext', 'skipSkills', 'indexOnly', 'stats', 'noStats', 'name', 'maxFileSize', 'workerTimeout', 'workers')
                foreach ($section in @($config, $config['analyze'])) {
                    if ($null -eq $section) { continue }
                    if ($section -isnot [System.Collections.IDictionary]) { Fail '.gitnexusrc sections must be objects.' }
                    foreach ($key in $section.Keys) {
                        if ($key -ne 'analyze' -and $key -notin $safeKeys) { Fail ".gitnexusrc option '$key' is outside this wrapper's local graph-only scope." }
                    }
                }
            }
            $forward[1] = $repoPath
            if (!$parsed.ContainsKey('--index-only')) { $forward.Add('--index-only') }
        } else {
            if (!$parsed.ContainsKey('--repo')) { Fail "'$command' requires explicit --repo; implicit repository selection is disabled." }
            Assert-SafePath $parsed['--repo']
            $matchedRepos = @($registry | Where-Object { $_.name -eq $parsed['--repo'] -or $_.path -eq $parsed['--repo'] })
            if ($matchedRepos.Count -ne 1) { Fail '--repo must resolve to exactly one repository in the isolated registry.' }
            Assert-GraphOnlyIndex $matchedRepos[0]
        }
    }

    if (!(Test-Path -LiteralPath $node -PathType Leaf) -or !(Test-Path -LiteralPath $cli -PathType Leaf)) { Fail 'Pinned Node runtime or installed GitNexus CLI is missing.' }
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $node
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.ArgumentList.Add($cli)
    foreach ($arg in $forward) { $start.ArgumentList.Add($arg) }
    # Sanitize only the child copy; the caller's environment is never mutated.
    foreach ($key in @($start.Environment.Keys)) {
        if ($key.StartsWith('GITNEXUS_', [StringComparison]::OrdinalIgnoreCase) -or $key -in @('NODE_OPTIONS', 'NODE_PATH')) { [void]$start.Environment.Remove($key) }
    }
    $start.Environment['GITNEXUS_HOME'] = Join-Path $toolRoot 'workflow-state'
    $start.Environment['GITNEXUS_STORAGE_ROOT'] = Join-Path $toolRoot 'workflow-indexes'
    $start.Environment['GITNEXUS_NO_UPDATE_NOTIFIER'] = '1'
    $start.Environment['GITNEXUS_LBUG_EXTENSION_INSTALL'] = 'load-only'
    $start.Environment['GITNEXUS_MCP_READ_ONLY'] = '1'
    $start.Environment['USERPROFILE'] = Join-Path $toolRoot 'native-home'
    $process = [Diagnostics.Process]::Start($start)
    try {
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        if ($stdout.Length -gt 0) { Write-Output -NoEnumerate $stdout.TrimEnd() }
        if ($stderr.Length -gt 0) { [Console]::Error.Write($stderr) }
        $result = $process.ExitCode
    } finally { $process.Dispose() }
    exit $result
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
