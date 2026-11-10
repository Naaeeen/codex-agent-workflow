---
name: dmux-workflows
description: "Operate or configure an existing dmux/tmux workflow, or help a user who specifically chooses dmux for terminal agent orchestration. Generic parallel work in Codex should use available native multi-agent tools without installing another harness."
---

# dmux Workflows

Orchestrate parallel AI agent sessions using dmux, a tmux pane manager for agent harnesses.

## When to Activate

- The user asks to use, configure, or troubleshoot dmux.
- The current project already uses dmux and the task concerns its workflow.

For ordinary parallel work in Codex, use the available native multi-agent tools. A request to split work does not itself require tmux, a second harness, new credentials, or global packages. Before operating dmux, inspect the installed version, project state, and supported controls. On Windows, use the selected WSL distribution only if that is the intended environment.

## What is dmux

dmux is a tmux-based orchestration tool that manages AI agent panes:
- Press `n` to create a new pane with a prompt
- Press `m` to open the pane menu; Merge is a distinct operation that can commit and alter branches.
- Supports: Claude Code, Codex, OpenCode, Cline, Gemini, Qwen

**Installation is optional:** Reuse an existing installation. If the user chooses dmux and it is missing, review the current [upstream setup instructions](https://github.com/standardagents/dmux) and compatible version, then install only within the authorized scope. Do not install a global tool merely to parallelize a Codex task.

## Quick Start

```bash
# Start dmux session
dmux

# Create agent panes (press 'n' in dmux, then type prompt)
# Pane 1: "Implement the auth middleware in src/auth/"
# Pane 2: "Write tests for the user service"
# Pane 3: "Update API documentation"

# Each pane runs its own agent session
# Press 'm' for the pane menu; inspect the diff before choosing Merge
```

## Workflow Patterns

### Pattern 1: Research + Implement

Parallelize research and independent preparation; implementation decisions that depend on research wait for its findings:

```
Pane 1 (Research): "Research best practices for rate limiting in Node.js.
  Check current libraries, compare approaches, and write findings to
  /tmp/rate-limit-research.md"

Pane 2 (Preparation): "Inspect existing middleware and tests. Report the
  integration points without editing behavior until research is reconciled."

# After Pane 1 completes, merge findings into Pane 2's context
```

### Pattern 2: Multi-File Feature

Agree interfaces and ownership first, then parallelize independent work across files:

```
Pane 1: "Create the database schema and migrations for the billing feature"
Pane 2: "Build the billing API endpoints in src/api/billing/"
Pane 3: "Create the billing dashboard UI components"

# Merge all, then do integration in main pane
```

### Pattern 3: Test + Fix Loop

Run tests in one pane, fix in another:

```
Pane 1 (Watcher): "Run the test suite in watch mode. When tests fail,
  summarize the failures."

Pane 2 (Fixer): "Fix failing tests based on the error output from pane 1"
```

### Pattern 4: Cross-Harness

Use different AI tools for different tasks:

```
Pane 1 (Claude Code): "Review the security of the auth module"
Pane 2 (Codex): "Refactor the utility functions for performance"
Pane 3 (Claude Code): "Write E2E tests for the checkout flow"
```

### Pattern 5: Code Review Pipeline

Parallel review perspectives:

```
Pane 1: "Review src/api/ for security vulnerabilities"
Pane 2: "Review src/api/ for performance issues"
Pane 3: "Review src/api/ for test coverage gaps"

# Merge all reviews into a single report
```

## Best Practices

1. **Independent tasks only.** Don't parallelize tasks that depend on each other's output.
2. **Clear boundaries.** Each pane should work on distinct files or concerns.
3. **Merge strategically.** Review pane output before merging to avoid conflicts.
4. **Use git worktrees.** For file-conflict-prone work, use separate worktrees per pane.
5. **Resource awareness.** Each pane consumes model capacity and may incur charges. Bound concurrency by actual quotas, independent work, and coordination cost; more panes are not inherently better.
6. **Side effects.** A pane may use another provider or account. Preserve scoped authorization for remote dispatch, commits, merges, pushing, credentials, and lifecycle hooks; a prompt example grants none of these.

## Git Worktree Integration

Inspect/reuse a suitable checkout first. In Codex desktop use the supported managed-worktree tools when available. The following shell example is for an explicitly selected standalone dmux/Git workflow; verify refs, paths, clean state, and ownership before adapting it:

```bash
# Create worktrees for isolation
git worktree add ../feature-auth feat/auth
git worktree add ../feature-billing feat/billing

# Run agents in separate worktrees
# Pane 1: cd ../feature-auth && claude
# Pane 2: cd ../feature-billing && claude

# Merge branches when done
git merge feat/auth
git merge feat/billing
```

## Complementary Tools

| Tool | What It Does | When to Use |
|------|-------------|-------------|
| **dmux** | tmux pane management for agents | Parallel agent sessions |
| **Superset** | Terminal IDE for 10+ parallel agents | Large-scale orchestration |
| **Claude Code Task tool** | In-process subagent spawning | Programmatic parallelism within a session |
| **Codex multi-agent** | Built-in agent roles | Codex-specific parallel work |

## Troubleshooting

- **Pane not responding:** Check if the session awaits input. Use the installed version's pane navigation (currently `j`/Enter); `m` opens the menu, not a read-only output fetch.
- **Merge conflicts:** Use git worktrees to isolate file changes per pane.
- **High token usage:** Reduce number of parallel panes. Each pane is a full agent session.
- **tmux not found:** Verify the intended environment. Use native Codex agents if tmux is unnecessary; install system dependencies only when the chosen dmux setup requires and authorizes it.
