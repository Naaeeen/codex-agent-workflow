---
name: vercel-cli-with-tokens
description: Deploy and manage projects on Vercel using token-based authentication. Use when working with Vercel CLI access tokens for deployment, project setup, or environment management.
metadata:
  author: vercel
  version: "1.0.0"
---

# Vercel CLI with Tokens

Deploy and manage projects using Vercel CLI with token authentication. Preserve the user's selected account, project, and deployment environment.

## Step 1: Locate the Vercel Token Safely

Check only whether the configured variable is nonempty. Never print the token, dump the environment, grep matching secret lines, enable shell tracing, or ask the user to paste credentials into chat.

Bash:

```bash
if [ -n "${VERCEL_TOKEN:-}" ]; then
  printf 'VERCEL_TOKEN: present\n'
else
  printf 'VERCEL_TOKEN: missing\n'
fi
```

PowerShell:

```powershell
if ([string]::IsNullOrWhiteSpace($env:VERCEL_TOKEN)) {
    'VERCEL_TOKEN: missing'
} else {
    'VERCEL_TOKEN: present'
}
```

If a project documents a local dotenv file, check only for the expected key without exposing its value. Do not search unrelated credential stores. For example, in PowerShell:

```powershell
$tokenFile = '.env'
if (Test-Path -LiteralPath $tokenFile -PathType Leaf) {
    $hasTokenKey = [bool]([System.IO.File]::ReadLines((Resolve-Path -LiteralPath $tokenFile).Path) | Where-Object { $_ -match '^\s*(export\s+)?VERCEL_TOKEN\s*=' } | Select-Object -First 1)
    if ($hasTokenKey) { 'VERCEL_TOKEN key: present in local file' }
    else { 'VERCEL_TOKEN key: missing from local file' }
} else {
    'Token file: missing'
}
```

This detects a key, not a valid or nonempty credential. For a different documented variable name, check that exact name rather than guessing by token prefix. Use the project's existing dotenv/secret loader to inject the value into the CLI process without logging it. Do not execute an untrusted `.env` as shell code or parse it with `grep | cut`; quoting, comments, and embedded equals signs matter.

If no usable token exists, ask the user to configure it locally through their secret manager or environment. The user can create a token at [Vercel account tokens](https://vercel.com/account/tokens). A missing or rejected token does not authorize uploading source to a different deployment service.

Current [Vercel global options](https://vercel.com/docs/cli/global-options#token) document `VERCEL_TOKEN` as an authentication input. Prefer process environment injection over `--token` arguments. Verify the installed CLI's behavior with `vercel --version`, help, and a read-only `vercel whoami`; do not claim a token is valid merely because it exists. If an older CLI lacks the documented behavior, resolve compatibility instead of exposing the credential in command arguments.

## Step 2: Identify Project and Team

Read known non-secret `VERCEL_PROJECT_ID` / `VERCEL_ORG_ID` values and the existing `.vercel/project.json` or `.vercel/repo.json`. Do not dump `.env` to discover them. Resolve conflicts among environment variables, local linking, and the user's intended target before mutation.

`VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` together can target a project without interactive linking. A project dashboard URL can supply a team slug, but does not prove account authorization. For a monorepo, verify the mapping for the exact directory; the mere presence of `.vercel/repo.json` does not establish that every package is linked.

## CLI Setup

Use the existing CLI and package manager. Check `vercel --version` and the relevant command's `--help`. Do not automatically install globally or upgrade it during deployment. If the user requests setup and the CLI is missing, install in the agreed scope, then verify it. Do not add dependencies only to perform a read-only check.

## Deploying a Project

Default to preview. Before uploading, verify account/team, project, directory, upload scope, and environment. A deployment request authorizes deployment to that target; it does not implicitly authorize a Git push, account change, production release, or fallback intermediary.

**New project caveat:** The [deploy documentation](https://vercel.com/docs/cli/deploy#prod) says a project's first deployment is production even without `--prod`. For preview-only requests, check that an established project can accept preview deployments. If a new project's first deployment would be production, explain this and obtain production authorization or use an existing authorized project. Do not assume `--target=preview` overrides that documented caveat.

For a verified existing target, a supported CLI can deploy without waiting for the build:

```text
vercel deploy --cwd <project-directory> --target=preview --scope <team-slug> --no-wait
```

Capture the returned deployment URL and command exit status. Use `--yes` only after the target is resolved; it accepts setup defaults and must not silently select/create an unintended project. Production requires explicit scoped authorization:

```text
vercel deploy --cwd <project-directory> --prod --scope <team-slug> --no-wait
```

Check the exact returned URL or ID, not the latest deployment for the account:

```text
vercel inspect <deployment-url-or-id> --scope <team-slug>
```

A URL from `--no-wait` means submission, not build success. Inspect until a terminal result using bounded waits; stop on build failure and report it. A safe read-only visit to the actual deployment can verify reachability; a browser is needed to verify changed interactive behavior.

### Linking an Existing Project

Inspect local state before linking. With the intended team and project known:

```text
vercel link --project <project-name> --scope <team-slug>
```

Use `vercel link --repo` only when the installed CLI supports it and repository mapping is appropriate. Verify resulting IDs and directory mappings. Linking must not create an unspecified project or replace an unrelated link. Read [Vercel link](https://vercel.com/docs/cli/link) as needed; do not edit `.vercel/` metadata by hand.

### Git Push Deployments

Use this route only when the user has authorized the push and the Git integration and branch environment are confirmed. Otherwise an authorized CLI preview is available even when a Git remote exists.

1. Check `git status --short`, current branch, staged changes, and the task diff. Verify the production branch in the actual Vercel project; do not assume it is `main`.
2. Stage only explicit task paths, such as `git add -- path/to/task-file`. Preserve unrelated staged work; stop and isolate the task commit if the index contains other work. Review `git diff --cached` safely before a scoped commit.
3. Push the intended commit and branch only under the user's authorization. If that branch triggers production, obtain production authorization first or use the preview CLI route.
4. Record the pushed commit SHA. Find deployments for the exact project and commit, e.g. for GitHub:

```text
vercel list <project-name> --scope <team-slug> --meta githubCommitSha=<pushed-sha> --environment=preview
```

Validate returned team/project, SHA, environment, and deployment ID; inspect that ID. For other Git providers use verified provider metadata or the commit's deployment check. Never use the latest entry alone, and never guess a URL if association cannot be established. [Vercel list](https://vercel.com/docs/cli/list) documents metadata filtering.

### Remote Repository

Clone only the requested repository into a suitable local checkout, inspect its build and upload content, then use the same target/authentication flow. Cloning does not authorize a push or deployment of unrelated files.

## Managing Environment Variables

Operate only on the authorized variable, project, and environment. Inspect the installed CLI's help before use. Provide secret values through supported protected input; do not echo literal secrets, put them into arguments, or display pulled files.

```text
vercel env ls --scope <team-slug>
vercel env add VAR_NAME preview --scope <team-slug>
vercel env pull <ignored-local-file> --scope <team-slug>
vercel env rm VAR_NAME preview --scope <team-slug>
```

`add`, `pull`, and `rm` examples are distinct requested operations, not a sequence to run automatically. `pull` writes secrets locally: choose an ignored destination that does not overwrite an existing file, and verify ignore status. Removal needs explicit authorization for that variable/environment. Omit confirmation-skipping flags unless the exact action is authorized and reviewed.

## Inspecting Deployments

```text
vercel list <project-name> --scope <team-slug>
vercel inspect <deployment-url-or-id> --scope <team-slug>
vercel inspect <deployment-url-or-id> --logs --scope <team-slug>
```

Logs can contain application secrets or personal data. Retrieve only what is needed and redact diagnostic excerpts. For runtime logs, consult `vercel logs --help` to select bounded output rather than assuming version-specific follow behavior.

## Managing Domains and Plans

Read-only domain listing is distinct from changing traffic:

```text
vercel domains ls --scope <team-slug>
```

Add or reassign a domain only to the explicitly authorized project after checking current ownership and routing. Plan changes can bill money or remove capabilities; only perform a specifically authorized change through an existing supported integration. Verify current [plan details](https://vercel.com/docs/plans/pro-plan) rather than relying on static prices or feature lists in this skill. Do not install or invoke Stripe Projects solely because it appeared in an example.

## Troubleshooting

- **Token missing:** Repeat the presence-only check and have the user configure it locally. Never request the value in chat.
- **Authentication failure:** Use a bounded read-only identity check, then report whether authentication is unavailable. Do not retry deployment repeatedly or send the source to an unauthenticated fallback.
- **Wrong team/project:** Inspect the conflicting scope and linkage; repair only the authorized target, not global account defaults.
- **Build failure:** Inspect that deployment's redacted logs. Check existing dependencies, environment names, and framework configuration; make a focused fix before retrying the authorized deployment.
- **CLI missing/incompatible:** Report the gap or perform scoped setup if authorized. Do not use a global latest install as an automatic recovery step.

## Working Agreement

Keep authentication secret, targets explicit, and preview/production status accurate. Honor existing scoped authorization without asking repeatedly. Only report successful deployment after checking the specific deployment; distinguish build readiness, reachability, and tested user flows.
