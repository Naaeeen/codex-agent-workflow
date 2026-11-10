$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
# This entry point uses the one isolated index, even when run inside a project
# containing .qmd/index.yml. An explicit different index needs its own launcher.
foreach ($argument in $args) {
  if ($argument -eq '--' -or $argument -eq '--index' -or $argument -like '--index=*') {
    throw 'This isolated QMD launcher reserves --index and the -- terminator.'
  }
}
$fixed = [ordered]@{
  INDEX_PATH = (Join-Path $root 'cache\qmd\workflow.sqlite')
  XDG_CACHE_HOME = (Join-Path $root 'cache')
  XDG_CONFIG_HOME = (Join-Path $root 'config')
  QMD_CONFIG_DIR = (Join-Path $root 'config\workflow')
  QMD_SKILLS_DIR = (Join-Path $root 'node_modules\@tobilu\qmd\skills')
  QMD_EMBED_MODEL = (Join-Path $root 'cache\qmd\models\Qwen3-Embedding-0.6B-Q8_0.gguf')
  QMD_RERANK_MODEL = (Join-Path $root 'cache\qmd\models\qwen3-reranker-0.6b-q8_0.gguf')
  QMD_GENERATE_MODEL = (Join-Path $root 'cache\qmd\models\qmd-query-expansion-1.7B-q4_k_m.gguf')
  QMD_FORCE_CPU = '1'
  HOME = (Join-Path $root 'home')
  USERPROFILE = (Join-Path $root 'home')
  TEMP = (Join-Path $root 'temp')
  TMP = (Join-Path $root 'temp')
  PWD = $ExecutionContext.SessionState.Path.CurrentFileSystemLocation.Path
}
# Remove inherited tool overrides, including trust switches and native-runtime
# repo/build paths. Restore every captured value in finally, including absent ones.
$inherited = @([Environment]::GetEnvironmentVariables('Process').Keys | Where-Object {
  $_ -like 'QMD_*' -or $_ -like 'NODE_LLAMA_CPP_*' -or $_ -like 'npm_config_node_llama_cpp*'
})
$keys = @($fixed.Keys) + $inherited + @('NODE_OPTIONS','NODE_PATH') | Select-Object -Unique
$old = @{}
foreach ($key in $keys) { $old[$key] = [Environment]::GetEnvironmentVariable($key,'Process') }
try {
  foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key,$null,'Process') }
  foreach ($key in $fixed.Keys) { [Environment]::SetEnvironmentVariable($key,$fixed[$key],'Process') }
  foreach ($directory in @($fixed.HOME,$fixed.TEMP)) {
    [void][IO.Directory]::CreateDirectory($directory)
  }
  & '{{CODEX_HOME}}\tools\agent-kit\runtime\node-v24.22.2-win-x64\node.exe' (Join-Path $root 'node_modules\@tobilu\qmd\bin\qmd') @args --index workflow
  $result = $LASTEXITCODE
} finally {
  foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key,$old[$key],'Process') }
}
exit $result
