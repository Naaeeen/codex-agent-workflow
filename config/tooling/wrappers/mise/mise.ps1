# Isolated mise entrypoint. Use pwsh -NoProfile -File <this file> <mise args>.
$root=$PSScriptRoot
$overrides=@{MISE_CONFIG_DIR="$root\config";MISE_DATA_DIR="$root\data";MISE_INSTALLS_DIR="$root\data\installs";MISE_INSTALL_STORE_DIR="$root\data\store";MISE_PLUGINS_DIR="$root\data\plugins";MISE_DOWNLOADS_DIR="$root\data\downloads";MISE_CACHE_DIR="$root\cache";MISE_STATE_DIR="$root\state";MISE_TMP_DIR="$root\tmp";MISE_SYSTEM_CONFIG_DIR="$root\system-config";MISE_SYSTEM_CONFIG_FILE="$root\system-config\config.toml";MISE_SYSTEM_DATA_DIR="$root\system-data";MISE_GLOBAL_CONFIG_FILE="$root\config\config.toml";MISE_GLOBAL_CONFIG_ROOT="$root\config";MISE_LOG_FILE=$null;MISE_HIDE_UPDATE_WARNING='1';MISE_COLOR='0';MISE_TRUSTED_CONFIG_PATHS='';MISE_YES='0';MISE_PARANOID='1';TEMP="$root\tmp";TMP="$root\tmp"}
$managedPrefix = '^MISE_'
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
 foreach($dir in @('config','data','cache','state','tmp','system-config','system-data')){New-Item -ItemType Directory -Path (Join-Path $root $dir) -Force|Out-Null}
 & "$root\v2026.11.1\mise\bin\mise.exe" @args
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