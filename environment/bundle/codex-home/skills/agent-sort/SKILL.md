---
name: agent-sort
description: Build an evidence-backed ECC install plan for a specific repo by sorting skills, commands, rules, hooks, and extras into DAILY vs LIBRARY buckets using parallel repo-aware review passes. Use when ECC should be trimmed to what a project actually needs instead of loading the full bundle.
---

# Agent Sort

Use this skill when a repo needs a project-specific ECC surface instead of the default full install.

The goal is not to guess what "feels useful." The goal is to classify ECC components with evidence from the actual codebase.

## When to Use

- A project only needs a subset of ECC and full installs are too noisy
- The repo stack is clear, but nobody wants to hand-curate skills one by one
- A team wants a repeatable install decision backed by grep evidence instead of opinion
- You need to separate always-loaded daily workflow surfaces from searchable library/reference surfaces
- A repo has drifted into the wrong language, rule, or hook set and needs cleanup

## Non-Negotiable Rules

- Use the current repository as the source of truth, not generic preferences
- Every DAILY decision must cite concrete repo evidence
- LIBRARY does not mean "delete"; it means "keep accessible without loading by default"
- Do not install hooks, rules, or scripts that the current repo cannot use
- Respect the actual host and existing install system; ECC content is a candidate library, not proof that its Claude-specific runtime is available
- Planning is read-only. Apply only scoped, authorized changes; do not install hooks, MCP servers, plugins, or permission bypasses just because a bundle includes them

## Outputs

Produce these artifacts in order:

1. DAILY inventory
2. LIBRARY inventory
3. install plan
4. verification report
5. optional `skill-library` router if the project wants one

## Classification Model

Use two buckets only:

- `DAILY`
  - should be readily discoverable for relevant daily tasks in this repo; this does not require loading every skill body into every session
  - strongly matched to the repo's language, framework, workflow, or operator surface
- `LIBRARY`
  - useful to retain, but not worth loading by default
  - should remain reachable through search, router skill, or selective manual use

## Evidence Sources

Use repo-local evidence before making any classification:

- file extensions
- package managers and lockfiles
- framework configs
- CI and hook configs
- build/test scripts
- imports and dependency manifests
- repo docs that explicitly describe the stack

Useful commands include:

```bash
rg --files
rg -n "typescript|react|next|supabase|django|spring|flutter|swift"
cat package.json
cat pyproject.toml
cat Cargo.toml
cat pubspec.yaml
cat go.mod
```

## Parallel Review Passes

If parallel subagents are available, split the review into these passes:

1. Agents
   - classify `agents/*`
2. Skills
   - classify `skills/*`
3. Commands
   - classify `commands/*`
4. Rules
   - classify `rules/*`
5. Hooks and scripts
   - classify hook surfaces, MCP health checks, helper scripts, and OS compatibility
6. Extras
   - classify contexts, examples, MCP configs, templates, and guidance docs

If subagents are not available, run the same passes sequentially.

## Core Workflow

### 1. Read the repo

Establish the real stack before classifying anything:

- languages in use
- frameworks in use
- primary package manager
- test stack
- lint/format stack
- deployment/runtime surface
- operator integrations already present
- running host/client, supported roles and tool schemas, OS, and actual skill-discovery paths
- existing project instructions and install records, including overlapping skills

### 2. Build the evidence table

For every candidate surface, record:

- component path
- component type
- proposed bucket
- repo evidence
- short justification

Use this format:

```text
skills/frontend-patterns | skill | DAILY | 84 .tsx files, next.config.ts present | core frontend stack
skills/django-patterns   | skill | LIBRARY | no .py files, no pyproject.toml       | not active in this repo
rules/typescript/*       | rules | DAILY | package.json + tsconfig.json            | active TS repo
rules/python/*           | rules | LIBRARY | zero Python source files             | keep accessible only
```

### 3. Decide DAILY vs LIBRARY

Promote to `DAILY` when:

- the repo clearly uses the matching stack
- the component is general enough to help every session
- the repo already depends on the corresponding runtime or workflow

Demote to `LIBRARY` when:

- the component is off-stack
- the repo might need it later, but not every day
- it adds context overhead without immediate relevance

### 4. Build the install plan

Translate the classification into action:

- DAILY skills -> keep existing discoverable skills; for Codex use the verified project `.agents/skills/` or user skill location supported by that client. Use `.claude/skills/` only for an actual Claude Code target.
- DAILY commands -> keep explicit compatibility shims only when the host supports and needs them; Codex does not gain Claude slash commands by copying their files.
- DAILY rules -> place necessary concise guidance in the host's existing instruction surface; do not assume Claude rule directories are automatically loaded by Codex.
- DAILY hooks/scripts -> retain only verified host/OS-compatible integrations with a concrete need and authorization. Do not translate hook schemas by guesswork.
- LIBRARY surfaces -> preserve their existing files and make them discoverable through current search/catalog mechanisms. Do not delete or globally disable them merely for being off-stack.

If the repo already uses selective installs, update that plan instead of creating another system.

### 5. Create the optional library router

First check whether the existing skill catalog or search already provides the needed discovery. Only if the project requests a router and it adds useful routing, create it under the verified host-specific skill directory, for example `.agents/skills/skill-library/SKILL.md` for a Codex project. Do not default to a Claude-only path.

That router should contain:

- a short explanation of DAILY vs LIBRARY
- grouped trigger keywords
- where the library references live

Do not duplicate every skill body inside the router.

### 6. Verify the result

After the plan is applied, verify:

- every DAILY file exists where expected and is actually discoverable by the running host
- stale language rules were not left active
- incompatible hooks were not installed
- the resulting install actually matches the repo stack

Return a compact report with:

- DAILY count
- LIBRARY count
- removed stale surfaces
- open questions

## Handoffs

Use these follow-ups only if the named skill is installed and applicable; otherwise provide the plan or perform the authorized equivalent with available tools. Do not install a missing skill merely to satisfy this list.

If the next step is interactive installation or repair, consider:

- `configure-ecc`

If the next step is overlap cleanup or catalog review, hand off to:

- `skill-stocktake`

If the next step is broader context trimming, hand off to:

- `strategic-compact`

## Output Format

Return the result in this order:

```text
STACK
- language/framework/runtime summary

DAILY
- frequently relevant, discoverable items with evidence

LIBRARY
- searchable/reference items with evidence

INSTALL PLAN
- what should be installed, removed, or routed

VERIFICATION
- checks run and remaining gaps
```
