---
name: strategic-compact
description: Preserve a concise task handoff at logical phase boundaries during long work, and use manual context compaction only when the running client supports it and it benefits the task.
---

# Strategic Compact Skill

Keep long-running work coherent across context compaction. Preserve the active objective, user decisions, evidence, and next step before a useful phase boundary; continue work without restarting completed steps.

## When to Use

- A lengthy task has accumulated bulky research or debugging output.
- Work moves from exploration to implementation, or a milestone has completed.
- Context pressure is evident in the running client and a compact handoff would help.

Do not infer a fixed context limit from a model name, tool-call count, or elapsed time. Do not assume slower responses prove context pressure. A phase transition is a chance to assess, not an instruction to compact automatically.

## Save the Handoff First

Use the task's existing notes or scratch area. Keep project architecture and team runbooks in their existing documentation rather than global memory. Change personal memory only when the user explicitly asks and the host permits it.

A useful handoff contains:

- Objective and acceptance criteria, including the latest user constraints.
- Decisions and important rejected approaches, with brief reasons.
- Changed files and relevant working-tree state; preserve unrelated work.
- Checks run, exact failures or gaps, and where supporting artifacts are saved.
- Running processes or agent tasks still needed, blockers, and one concrete next action.

Write enough to resume reliably, not a copy of the conversation or raw logs. Do not store credentials or sensitive diagnostic output. An available task/plan tool can complement the note; no particular tool such as `TodoWrite` is required.

## Compaction Decision Guide

| Phase transition | Decision | Context to retain |
|---|---|---|
| Research to planning | Consider once evidence is distilled | Sources, uncertainties, decision criteria |
| Planning to implementation | Consider after the accepted plan is saved | Scope, dependencies, acceptance checks |
| Implementation to testing | Keep recent details when needed | Edited paths, behavior, test commands |
| Debugging to next feature | Consider at a completed boundary | Root cause, rejected attempts, verification |
| Mid-implementation | Usually continue | Partial edits, failures, dependencies |
| Failed approach | Preserve what failed before changing direction | Reproduction and reasons not to repeat it |

A failure alone is not a reason to discard context. Do not compact away unresolved evidence merely to make the next attempt feel fresh.

## Use the Running Client's Capabilities

Check which context-management action the actual client exposes. If manual compaction is available and useful, use that supported action with a task-focused summary. Otherwise rely on normal client compaction and the saved handoff; continue authorized work.

Do not issue a Claude `/compact` command in Codex unless that exact client confirms support. Do not install Claude `PreToolUse` hooks, reference a nonexistent `suggest-compact.js`, or modify global settings to use this skill. Tool-call reminders and automatic hooks are optional product-specific features, not prerequisites.

## After Compaction

Check the current user request and read the handoff. Reinspect relevant files and any unfinished process results where needed; do not repeat passing work solely because the context changed. Disk files and Git state are durable, but conversation summarization details depend on the host. Never promise that particular tool history, a task list, or nuanced user preferences survive unless verified in the current client.

## Local task evidence ledger

For a genuinely long, multi-stage task, the installed standard-library ledger at
{{CODEX_HOME}}\harness\task_ledger.py can preserve its fixed workspace,
acceptance checks, evidence hashes, failure history and next action. Use its init,
record, checkpoint and resume commands; inspect --help before invocation. Keep
state in the task's scratch area. Do not create a ledger for a small self-contained
edit, and do not replace native Codex goals/resume or project documentation with it.

The complete command requires all required evidence (including review) to pass
and still match its hash. A status command returning zero does not mean the task
is complete: inspect ready_to_complete and completion_currently_valid. Evidence
records do not authenticate reviewer independence or prove a test actually ran.
Do not mark a native goal complete just because the ledger is readable.
