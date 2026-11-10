---
name: marimo-notebooks
description: Create or maintain a reactive Python notebook or local analytical app in marimo when the user requests that format or reactive parameter exploration.
---

# Reactive Python notebooks

Preserve an existing Jupyter/CSV/Excel workflow unless the request benefits from
a reactive Python notebook. This skill is not required for ordinary charts.

The pinned CLI is {{CODEX_HOME}}\tools\marimo\venv\Scripts\marimo.exe
and its Python is in the same Scripts directory. Use the installed help and
https://docs.marimo.io/ for version-sensitive APIs.

Keep notebook source in a task/project-owned .py file. Cells should have clear
inputs and outputs and avoid duplicate global definitions and dependency cycles.
Validate with marimo check --strict and a cold script run, not only a previously
executed interactive session. Check calculations against an independent oracle.

Use marimo run/edit only for an explicitly selected local notebook; bind local
servers to loopback and stop task-owned processes afterwards. If a real UI check
is needed, delegate it to a UI-capable subagent chosen under the current relative
cost/capability policy: a capable lower-cost model or the same model at lower
reasoning effort when suitable.

marimo export html produces a static snapshot; the qualified default export
references CDN assets, so it is not a verified fully offline single-file artifact.
Do not promise reactive controls in a static export. Retain the .py source and
make format/dependency limits clear. AI completions and external integrations
are optional and must not be enabled just to use notebooks.
