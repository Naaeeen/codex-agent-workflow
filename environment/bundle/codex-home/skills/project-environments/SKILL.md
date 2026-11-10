---
name: project-environments
description: Reproduce or repair selected project runtimes and native dependency environments with existing manifests and installed mise or pixi. Use for environment setup or mismatches, not to replace a working project package manager.
---

# Reproducible local project environments

Start with the project's manifest and lockfile. Keep its existing npm/uv/conda/
other workflow when working. The pinned agent-tool.ps1 provides mise and pixi
as optional owners of different concerns; do not make them compete for the same
Python environment.

Use mise for language/tool versions and a declared local task DAG. Inspect
mise.toml and task commands before trusting them. The wrapper enforces paranoid
mode, so untrusted or changed configuration is rejected. Trust only a reviewed
task/project config within current authorization; do not set a blanket trusted
directory. Use the installed help to select explicit project cwd and locked
execution. No shell activation or global PATH replacement is needed.
When a native command needs the literal `--` separator, invoke the shared
launcher through `pwsh -NoProfile -File ...` rather than PowerShell's `&` form;
the outer PowerShell parser can consume that token before the script receives it.

Use pixi when Python plus native libraries or a cross-platform lock is useful.
Use the selected project's pixi.toml/pixi.lock and `pixi run --locked TASK`.
`--offline` requires cached packages and must fail rather than silently fetch.
A lock is not a copied environment: build it for each platform. Package licenses
are individual; the tool's BSD license does not apply to every resolved package.
For a new NumPy environment the tested OpenBLAS constraint avoids the larger
MKL dependency set, but does not establish a performance advantage.

Keep generated environments and caches out of source commits unless the project
specifically tracks them. Tasks/package code execute with current permissions;
these wrappers isolate configuration paths, not the OS or hostile code.

Sources: https://mise.jdx.dev/ ; https://pixi.prefix.dev/
