---
name: wsl-coding
description: Read, edit, build, and test a project in an existing WSL Linux distribution from Windows Codex. Use for WSL or Ubuntu project paths and Linux toolchain issues; do not apply to ordinary Windows projects or remote Linux servers.
---

# Coding in WSL

Keep the repository and its toolchain in the environment the user selected.
Determine whether this agent is already running in Linux or is a Windows agent
accessing WSL. Use Linux tools directly in the former case.

## Identify the target

- Check the installed distribution with `wsl.exe --list --verbose`; use its exact
  name and verify the Linux user with `id -un`. Resolve the Linux project path and read its applicable AGENTS.md, manifests,
  tool versions, Git status, and existing changes before editing.
- Use the distribution and project selected by the reader. Confirm the directory is the intended existing repository before changing files.
- Windows can address Linux files through `\\wsl.localhost\Ubuntu\home\<WSL_USER>\...`
  or `\\wsl$\Ubuntu\home\<WSL_USER>\...`. Seeing a folder through UNC does not mean
  Windows Node, Python, or Git is the right runtime for it.

## Read, edit, and run in Linux

From Windows, use an explicit distribution and Linux working directory:

```powershell
wsl.exe --distribution Ubuntu --user <WSL_USER> --cd /home/<WSL_USER>/<PROJECT_ROOT> --exec git status --short
wsl.exe --distribution Ubuntu --user <WSL_USER> --cd /home/<WSL_USER>/<PROJECT_ROOT> --exec python3 -m unittest
```

Substitute the actual task path and project test command. Use the existing Linux
virtual environment, package manager, dependencies, and CI commands. Do not install
packages globally or reuse Windows `node_modules`/virtual environments for a Linux
project. Do not move a working repository to `/mnt/c` to make it accessible.

For Git operations that invoke hooks, also verify the Linux scanner/tool PATH.
Use a fixed login-shell command or an explicit reviewed environment when needed;
an unavailable scanner is a failed check, not a reason to bypass the hook.

Use `--exec` argument lists for simple commands. For multiline code or file edits,
pass a reviewed script through stdin or a task-owned file instead of interpolating
user text through PowerShell and a Linux shell. If a shell is required, keep its
script fixed and pass variable data separately. Verify the Linux resolved path and
diff after edits. Scope every write to the authorized project or isolated fixture.

`--exec` does not load login profiles. Resolve binaries within Linux and use an
explicit Linux executable when needed. The verified user-local Codex entrypoint is:

```powershell
wsl.exe --distribution Ubuntu --user <WSL_USER> --cd /home/<WSL_USER>/<PROJECT_ROOT> --exec /home/<WSL_USER>/<PROJECT_ROOT>
```

If `codex` resolves under `/mnt/c/.../npm`, it is a Windows shim; do not try to fix
Linux by installing Linux optional dependencies into the Windows package. Check the
existing Linux entrypoint first. Windows and Linux keep separate Codex config and
credentials; do not copy auth files or share a CODEX_HOME with platform-specific paths.

## Permission and completion boundaries

- A Windows sandbox may deny access to the WSL service. Request narrowly scoped
  execution for the intended Linux command when the host supports it. Do not treat
  `Wsl/Service/E_ACCESSDENIED` as proof that WSL is absent, and do not disable security.
- Native Linux agent execution is separate from using a WSL terminal. Changing the
  desktop agent backend requires the supported app setting and a restart; do not
  change all projects' backend or restart the user's app merely to run one command.
- Before claiming WSL coding works, verify read, a scoped edit, and the relevant
  Linux test/build command. Record actual exits and inspect the final Git diff.
  Use an isolated fixture for environment setup checks, not an unrelated user repo.
- Report whether verification used the Windows-to-WSL bridge or a Linux-native
  Codex session; one does not establish the other's full tool behavior.

References: [OpenAI WSL guidance](https://learn.chatgpt.com/docs/windows/wsl)
and [Windows app WSL settings](https://learn.chatgpt.com/docs/windows/windows-app#windows-subsystem-for-linux-wsl).
