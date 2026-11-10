# Isolated pixi entrypoint. Use pwsh -NoProfile -File <this file> <pixi args>.
$root=$PSScriptRoot
$overrides=@{PIXI_HOME="$root\data";PIXI_CACHE_DIR="$root\cache";RATTLER_CACHE_DIR="$root\cache";RATTLER_HOME="$root\config";RATTLER_AUTH_FILE="$root\config\empty-credentials.json";PIXI_NO_CONFIG='true';PIXI_NO_TELEMETRY='1';PIXI_NO_PROGRESS='true';PIXI_COLOR='never';TEMP="$root\tmp";TMP="$root\tmp"}
$managedPrefix = '^(PIXI_|RATTLER_)'
$prior = @{}
# Runtime overrides can outrank a pinned project manifest. Isolate every manager
# variable, including ones unknown to this wrapper, before applying our roots.
$inheritedNames = @(Get-ChildItem Env: | Where-Object { $_.Name -match $managedPrefix } | ForEach-Object Name)
foreach ($key in @($inheritedNames + @($overrides.Keys) | Select-Object -Unique)) {
 $prior[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
try {
 foreach ($key in $inheritedNames) { Remove-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue }
 foreach ($key in $overrides.Keys) {
  if ($null -eq $overrides[$key]) { Remove-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue }
  else { [Environment]::SetEnvironmentVariable($key, $overrides[$key], 'Process') }
 }
 foreach($dir in @('config','data','cache','tmp')){New-Item -ItemType Directory -Path (Join-Path $root $dir) -Force|Out-Null}; if(-not (Test-Path -LiteralPath "$root\config\empty-credentials.json")){'{}'|Set-Content -LiteralPath "$root\config\empty-credentials.json" -Encoding utf8}
 & "$root\v0.84.1\pixi.exe" @args
 $code = $LASTEXITCODE
} finally {
 foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -match $managedPrefix })) {
  Remove-Item -LiteralPath ("Env:" + $item.Name) -ErrorAction SilentlyContinue
 }
 foreach ($key in $prior.Keys) {
  if ($null -eq $prior[$key]) { Remove-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue }
  else { [Environment]::SetEnvironmentVariable($key, $prior[$key], 'Process') }
 }
}
exit $code