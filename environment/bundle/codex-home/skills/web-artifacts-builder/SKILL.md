---
name: web-artifacts-builder
description: Build a standalone interactive HTML deliverable when the user needs a shareable file with bundled assets. Use for multi-component artifacts that justify bundling; use the existing project workflow for app development and direct HTML/CSS/JS for simple standalone pages.
license: Complete terms in LICENSE.txt
---

# Web Artifacts Builder

Build the requested standalone web artifact with the simplest appropriate stack. Preserve an existing project's framework, package manager, and build system. A React/TypeScript application may benefit from bundling; a small interactive page often needs no dependencies.

## Workflow

1. Confirm the deliverable from the request: a standalone HTML file, existing project change, or hosted application. Do not introduce a hosted service or a different framework merely to use this skill.
2. Inspect available project tools. Work in a task-owned directory; reuse installed dependencies and pin compatible additions through the existing package manager when needed.
3. Build the necessary interface and interactions. Reuse the existing component library; include only components the artifact needs.
4. For a standalone deliverable, use the project's supported bundling path or a reviewed task-local build. Direct outputs to a new task-owned destination. Inspect for remote asset dependencies, secret values, and unsupported file-origin behavior before calling the result self-contained.
5. Test the final file with an available browser before delivery: inspect relevant viewport sizes, exercise the main interaction, and check console/load errors. If a check is unavailable, state that limitation rather than calling the artifact verified.
6. Share the resulting local file using the host's supported file link or preview. HTML delivery does not imply a Claude artifact viewer or public hosting.

## Tooling

Use the current project's reviewed build scripts or a small task-owned build.
The historical init-artifact.sh and bundle-artifact.sh helpers are removed from
this skill's active scripts directory: they installed floating/global packages
and deleted relative output paths. Their provenance is retained in the upgrade
archive; they are not supported execution entrypoints.

## Design

Match the brief and existing visual identity. Use the available frontend design skill when a new visual direction is needed; typography, colors, and layout are choices rather than universal bans. Preserve accessibility, keyboard interaction, and reduced-motion behavior.

## Reference

- shadcn/ui component documentation: https://ui.shadcn.com/docs/components
