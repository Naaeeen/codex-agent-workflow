[CmdletBinding(SupportsShouldProcess)]
param([Parameter(Mandatory)][string]$ManifestPath,
      [Parameter(Mandatory)][string]$SourceRoot,
      [Parameter(Mandatory)][string]$DestinationRoot)
$ErrorActionPreference='Stop'
foreach($row in (Import-Csv -LiteralPath $ManifestPath -Encoding UTF8)) {
    $source=Join-Path $SourceRoot $row.source
    $destination=Join-Path $DestinationRoot $row.destination
    if(-not (Test-Path -LiteralPath $source -PathType Leaf)) {throw 'missing'}
    if($PSCmdlet.ShouldProcess($destination,'Copy')) {
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination)) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}
