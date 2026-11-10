# Six layers of the workflow

The entry point is a natural-language task. Completing it requires reasoning plus access to the project, tools, permissions, and evidence. This kit uses “harness” for the operating environment around the model.

## How a task runs

1. The main agent reads the task, applicable AGENTS.md files, current repository state, and relevant sources. It defines an observable outcome. An export task needs conditions for ordinary data, an empty result, and behavior existing callers rely on.
2. It chooses a method for the uncertainty. Official documentation can settle an API contract, source navigation can trace impact, and the actual browser can show interaction behavior. A relevant Skill supplies the procedure, boundaries, and expected evidence.
3. It chooses an execution interface and location. CLIs are useful for repeatable local commands, MCP exposes service or structured tool interfaces, and browser tools operate the real UI. Local files and signed-in sessions often require local work. Cloud execution needs a usable environment, a bounded input package, and authorization.
4. Independent work can be delegated with scope, file ownership, sources, and acceptance conditions. The main agent reconciles the returned evidence. Shared directories require ownership or isolated worktrees.
5. Checks answer the acceptance conditions. Static analysis, unit tests, integration checks, browser behavior, and human feedback establish different things. Preserve failures, infrastructure errors, and checks not run. After a fix, rerun the affected checks.
6. Deliver the artifact and evidence, and leave the decisions needed to continue. Recurring failures can motivate a candidate workflow change, followed by a comparison and independent review.

## What each layer owns

| Layer | Representation | Effect |
| --- | --- | --- |
| Runtime settings | Config, profile, host policy, invocation overrides | Model, reasoning, search, and execution boundaries. A saved default can be overridden |
| Persistent agreements | User and project AGENTS.md | What to inspect, how to collaborate, acceptance and authorization |
| Task procedures | Skill metadata, instructions, references | Discover relevant guidance, then load the needed procedure |
| Workers | Main agent and subagent roles | Independent contexts with bounded responsibilities and host-controlled capabilities |
| Capabilities | CLI, MCP, browser, connectors | Read, execute, interact, and return observable results |
| Feedback and state | Checks, reviews, ledgers, handoff notes | Evidence for completion and continuity after interruption |

## Reading the evidence correctly

A field in a file establishes a saved setting. Client version, trust, host support, and actual session loading determine its effect. A reviewer role describes responsibility, while the runtime enforces permissions. The kit keeps recorded roles and a current-schema counterpart for inspection.

Installing a tool establishes availability. A Skill describes when and how to use it. A successful run checks one task. Promoting a workflow change requires a baseline, candidate, matched task, and a grader the candidate cannot alter.

Start with the [full working agreements](../templates/global-AGENTS.md), [workflow procedures](workflows.md), [Skill catalog](skills-catalog.md), and [configuration guide](settings.md). The project bootstrap stages rules, Skills, and roles into a fresh directory. The full machine snapshot contains explicit placeholders that must be adapted to the receiving environment.
