[CmdletBinding(SupportsShouldProcess)]
param([Parameter(Mandatory)][string]$ManifestPath,
      [Parameter(Mandatory)][string]$SourceRoot,
      [Parameter(Mandatory)][string]$DestinationRoot)
$ErrorActionPreference = 'Stop'
$sourceBase = [IO.Path]::GetFullPath($SourceRoot)
$destinationBase = [IO.Path]::GetFullPath($DestinationRoot)
$rows = @(Import-Csv -LiteralPath $ManifestPath -Encoding UTF8)
$seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$plans = [Collections.Generic.List[object]]::new()
foreach ($row in $rows) {
    foreach ($value in @($row.source, $row.destination)) {
        if ([string]::IsNullOrWhiteSpace($value) -or [IO.Path]::IsPathRooted($value) -or
            $value.Contains(':') -or (@($value -split '[\\/]' | Where-Object { $_ -eq '..' }).Count -gt 0)) {
            throw 'Unsafe relative path.'
        }
    }
    $source = [IO.Path]::GetFullPath([IO.Path]::Combine($sourceBase, $row.source))
    $destination = [IO.Path]::GetFullPath([IO.Path]::Combine($destinationBase, $row.destination))
    if (-not [IO.File]::Exists($source)) { throw 'Source file missing.' }
    if ([IO.File]::Exists($destination) -or [IO.Directory]::Exists($destination)) { throw 'Destination exists.' }
    if (-not $seen.Add($destination)) { throw 'Duplicate destination.' }
    $plans.Add([pscustomobject]@{Source=$source; Destination=$destination})
}
foreach ($plan in ($plans | Sort-Object Destination -Descending)) {
    if ($PSCmdlet.ShouldProcess($plan.Destination, 'Copy receipt')) {
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($plan.Destination)) | Out-Null
        [IO.File]::Copy($plan.Source, $plan.Destination, $false)
    }
}
