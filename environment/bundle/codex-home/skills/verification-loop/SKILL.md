---
name: verification-loop
description: Verify substantive code changes with the project's build, type, lint, test, security, and diff checks, preserving real failures and reporting validation gaps.
---

# Verification Loop Skill

Verify a feature, refactor, bug fix, or proposed PR using the checks the repository actually supports.

## Choose the Checks

Read applicable project instructions, manifests, lockfiles, CI, and the changed files. Identify the required checks and the affected behavior before running commands. Use the existing package manager and installed tools; do not install a compiler, linter, scanner, or test runner just to satisfy this checklist.

For documentation and configuration changes, use their native validators and focused review. Do not invent application tests or claim test coverage for prose.

## Preserve the Command Result

Run checks directly when output is bounded and safe. Do not pipe the live command into `head`, `tail`, or another formatter and then use the formatter's exit status as proof of success. If output needs capturing, save it to an ignored, task-specific log and capture the command's status immediately. Inspect only relevant, redacted excerpts; raw logs can contain secrets.

These examples assume the project already defines `npm run build`. Substitute the actual check and an existing ignored scratch location; run the snippet in a child shell because it exits with the check's status.

PowerShell (Windows native command):

```powershell
$checkLog = Join-Path $env:TEMP ('codex-check-' + [guid]::NewGuid().ToString('N') + '.log')
try {
    $LASTEXITCODE = 0
    & npm.cmd run build *> $checkLog
    $checkExit = $LASTEXITCODE
} catch {
    $checkExit = if ($LASTEXITCODE -ne 0) { $LASTEXITCODE } else { 1 }
}
Write-Output "Check exit code: $checkExit"
Write-Output "Local log: $checkLog"
exit $checkExit
```

Bash (Linux, macOS, or WSL; not PowerShell):

```bash
check_log=$(mktemp "${TMPDIR:-/tmp}/codex-check.XXXXXX") || exit 1
if npm run build >"$check_log" 2>&1; then
  check_exit=0
else
  check_exit=$?
fi
printf 'Check exit code: %s\nLocal log: %s\n' "$check_exit" "$check_log"
exit "$check_exit"
```

A timeout, unavailable command, or truncated result is not a pass. Preserve the log until diagnosis is complete; do not commit or upload it. Prefer test commands that use dummy credentials; when sensitive runtime data is unavoidable, use the project's existing redaction and restricted log storage.

## Verification Phases

### 1. Build

Run the project's required build if applicable. Fix a failing build before reporting readiness. Independent diagnostics may continue if they help resolve the failure.

### 2. Types and Lint

Run the configured type and lint commands for the affected scope, such as repository scripts or an already installed Python checker. Do not use an unpinned `npx` invocation that might download a new tool. Separate new errors from pre-existing failures, with evidence.

### 3. Tests and Coverage

Run affected behavioral tests and required integration checks. For changed interactive flows, use a real browser when available. A build or mocked test does not establish end-to-end success.

Use the project's coverage command and threshold where configured; target at least 80% for new production behavior where supported. Report actual measured coverage and its scope, or explain why it was not measured. Do not reinterpret skipped tests as passes.

### 4. Security

Inspect changed boundaries and use the project's existing secret/dependency checks as applicable. Configure scanners to redact findings. For an initial heuristic search, list filenames only:

```text
rg -l --hidden -g '!.git/**' -g '!node_modules/**' -g '!vendor/**' -e 'sk-' -e 'api_key' <reviewed-task-paths>
```

Replace the placeholder with explicit task paths, excluding private credential files. Matches require review and do not prove a leak; no matches do not prove absence. Report filename and redacted diagnosis, never a matching secret line. `rg` exit 1 means no matches; exit 2 means an error. Logging calls need contextual review, not a blanket ban.

### 5. Diff and Scope

Start with the working tree, including staged and untracked work:

```text
git status --short
git diff --stat
git diff --name-only
git diff --cached --name-only
git ls-files --others --exclude-standard
```

Review the relevant unstaged and staged diffs after checking for secret exposure; inspect untracked task files separately. For a branch/PR review, also compare against the verified base using `git diff <base>...HEAD`. `HEAD~1` alone misses other commits, staged/unstaged work, and untracked files. Preserve unrelated changes.

Check for unintended files, regressions, missing error handling, and untested edge cases. Obtain independent review for substantive code changes, resolve actionable findings, and rerun only affected checks.

## Report

Report each applicable check as PASS, FAIL, or NOT RUN, with its command/scope and relevant exit status. Mark irrelevant checks NOT APPLICABLE with a reason. Include test counts and measured coverage only when available, outstanding failures, and behavior not verified. Claim readiness only within that stated scope.

## When to Repeat

Verify after meaningful changes, before completion, and after fixing failures. Repeat passing checks only after a relevant change or unresolved concern; elapsed time alone is not a reason. Use available tools directly, without requiring a Claude `/verify` command or installing hooks.

For substantial documentation changes, optional pinned Typos and offline Lychee
checks are available. Use [local document checks](references/local-document-checks.md)
when spelling or local links are relevant; preserve the project's own check stack.
