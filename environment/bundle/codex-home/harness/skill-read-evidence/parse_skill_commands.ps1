# Fixed parser bridge. Input text is parsed as data, never invoked or dot-sourced.
$ErrorActionPreference = 'Stop'
$request = [Console]::In.ReadToEnd() | ConvertFrom-Json
$tokens = $null
$parseErrors = $null
$tree = [System.Management.Automation.Language.Parser]::ParseInput(
    [string]$request.command, [ref]$tokens, [ref]$parseErrors
)
$commands = [System.Collections.Generic.List[object]]::new()
$directOffsets = [System.Collections.Generic.HashSet[int]]::new()
$complexCount = 0
$pipelineId = 0

function Convert-CommandElement($element) {
    if ($element -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
        return @{ kind = 'literal'; value = [string]$element.Value }
    }
    if ($element -is [System.Management.Automation.Language.ConstantExpressionAst]) {
        if ($element.Value -is [string] -or $element.Value -is [int] -or $element.Value -is [long]) {
            return @{ kind = 'literal'; value = [string]$element.Value }
        }
    }
    if ($element -is [System.Management.Automation.Language.CommandParameterAst]) {
        $argument = $null
        if ($null -ne $element.Argument) { $argument = Convert-CommandElement $element.Argument }
        return @{ kind = 'parameter'; name = [string]$element.ParameterName; argument = $argument }
    }
    return @{ kind = 'dynamic' }
}

foreach ($statement in $tree.EndBlock.Statements) {
    $pipelineId += 1
    if ($statement -isnot [System.Management.Automation.Language.PipelineAst]) {
        $complexCount += 1
        continue
    }
    $pipelineIndex = 0
    foreach ($element in $statement.PipelineElements) {
        if ($element -isnot [System.Management.Automation.Language.CommandAst]) {
            $complexCount += 1
            continue
        }
        [void]$directOffsets.Add($element.Extent.StartOffset)
        $elements = [System.Collections.Generic.List[object]]::new()
        foreach ($part in $element.CommandElements) {
            $elements.Add((Convert-CommandElement $part))
        }
        $commands.Add(@{
            name = $element.GetCommandName()
            elements = @($elements.ToArray())
            redirected = ($element.Redirections.Count -gt 0)
            dot_sourced = ($element.InvocationOperator -eq [System.Management.Automation.Language.TokenKind]::Dot)
            pipeline_id = $pipelineId
            pipeline_index = $pipelineIndex
            pipeline_length = $statement.PipelineElements.Count
        })
        $pipelineIndex += 1
    }
}

$hiddenReads = 0
$hiddenReadCommands = [System.Collections.Generic.List[object]]::new()
$nested = $tree.FindAll({ param($node) $node -is [System.Management.Automation.Language.CommandAst] }, $true)
foreach ($command in $nested) {
    if ($directOffsets.Contains($command.Extent.StartOffset)) { continue }
    $name = [string]$command.GetCommandName()
    if ($name -match '^(?i:Microsoft\.PowerShell\.Management\\)?(?:Get-Content|cat|type|gc)$') {
        $hiddenReads += 1
        $parts = [System.Collections.Generic.List[object]]::new()
        foreach ($part in $command.CommandElements) {
            $parts.Add((Convert-CommandElement $part))
        }
        $hiddenReadCommands.Add(@{ name = $name; elements = @($parts.ToArray()) })
    }
}

$unsupportedReads = 0
$memberCalls = $tree.FindAll({ param($node) $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst] }, $true)
foreach ($call in $memberCalls) {
    if ($call.Member -is [System.Management.Automation.Language.StringConstantExpressionAst] -and
        $call.Member.Value -match '^(?i:ReadAllText|ReadAllLines|ReadLines|OpenText|OpenRead|ReadToEnd)$') {
        $unsupportedReads += 1
    }
}

@{
    parse_error = ($parseErrors.Count -gt 0)
    commands = @($commands.ToArray())
    hidden_read_count = $hiddenReads
    hidden_read_commands = @($hiddenReadCommands.ToArray())
    unsupported_read_count = $unsupportedReads
    complex_statement_count = $complexCount
} | ConvertTo-Json -Depth 12 -Compress
