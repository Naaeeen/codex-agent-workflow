---
name: deploy-to-vercel
description: Deploy applications and websites to Vercel when the user requests deployment, a live link, or a preview deployment, using their authorized project and environment.
metadata:
  author: vercel
  version: "3.0.0"
---

# Deploy to Vercel

Deploy the requested project to the user's intended Vercel account and environment. Prefer a preview unless production is explicitly authorized. Retain an existing useful Git integration without making Git pushes or new integrations a prerequisite for deployment.

## Step 1: Gather Project State

Inspect the requested directory, working-tree changes, relevant instructions, package manager, build settings, existing ignore files, and deployment configuration. Use installed tools and read-only checks first:

```text
git status --short
git remote get-url origin
git branch --show-current
vercel --version
vercel whoami
```

Read `.vercel/project.json` or `.vercel/repo.json` if present, plus non-secret project/team environment identifiers. On Windows use `Get-Content -LiteralPath`; in Bash use `cat` on exact paths. Do not print authentication files, environment dumps, or secret values. Do not suppress failures and infer a state from missing output.

Resolve the team, project, repository directory, and environment from existing linkage and the user's request. Verify a monorepo's specific directory mapping; `.vercel/repo.json` does not mean every folder maps to the same project. If multiple targets remain plausible, ask only for the missing target. Existing scoped authorization still counts.

Use the installed CLI's help and [current Vercel documentation](https://vercel.com/docs/cli) to confirm options. Do not assume `--format json`, repo-linking flags, or authentication methods exist in an old version. Check local linking before commands that might initiate setup; do not use bare `vercel link` or `vercel list --yes` as a read-only state probe.

## Step 2: Confirm Upload Scope and Environment

Check the exact files/build outputs that will be uploaded using the project's existing ignore/configuration rules. Exclude credentials, local configuration, private data, unrelated work, and scratch artifacts. A Git-clean tree alone does not prove the upload contains no secrets.

The [deploy documentation](https://vercel.com/docs/cli/deploy#prod) notes that a new project's first deployment is production even without `--prod`. Before fulfilling a preview-only request, verify that the selected existing project supports the intended preview. If a new project's first release would be production, obtain authorization for that consequence or select an existing authorized project. Do not claim that omitting `--prod`, or adding `--target=preview`, overrides the first-deployment caveat.

A deployment request authorizes deployment to its stated target. It does not authorize pushing Git history, changing production traffic, creating unrelated projects, or uploading through a different intermediary.

## Step 3: Choose a Deploy Method

### Existing linked project: CLI preview

An existing Git remote does not require a Git push. For a verified target and a compatible CLI:

```text
vercel deploy --cwd <project-directory> --target=preview --scope <team-slug> --no-wait
```

Capture the URL from this command's standard output and its actual exit status. `--no-wait` submits a build; it does not establish that the build succeeded. `--yes` accepts setup defaults, so use it only after verifying the intended target and any project-creation consequences.

For explicitly authorized production deployment:

```text
vercel deploy --cwd <project-directory> --prod --scope <team-slug> --no-wait
```

### Unlinked project: link the intended target

If authenticated, choose the target from existing evidence or the user's explicit choice. Linking an existing project:

```text
vercel link --project <project-name> --scope <team-slug>
```

Use repo-based linking only when the installed CLI supports it and the chosen directory/repository mapping is understood. Check the resulting IDs and directory before deployment. Do not let inferred folder defaults create an unspecified project or replace an unrelated link. Creating a project must be within the user's requested setup, with the first-deployment environment understood. See [Vercel link](https://vercel.com/docs/cli/link).

### Authorized Git push deployment

Use Git deployment when the user has authorized the push and the integration is verified:

1. Inspect the index, task diff, branch, and remote. Check which branch Vercel actually treats as production; do not assume `main` or assume a non-main branch is always preview.
2. Stage only explicit task paths with `git add -- <task-paths>`. Review the staged diff safely. Do not use blanket staging; unrelated existing staged files must not enter the task commit. Isolate the task or stop before committing if they cannot be separated safely.
3. Commit using the project's convention and push the exact authorized branch. A push that triggers production also needs production authorization. For preview-only work, use an existing authorized preview branch or the CLI route instead of changing production settings.
4. Record the pushed SHA. Query the exact project and commit or read that commit's deployment check. For a verified GitHub integration:

```text
vercel list <project-name> --scope <team-slug> --meta githubCommitSha=<pushed-sha> --environment=preview
```

Use the actual provider's verified metadata for other integrations. Check project/team, SHA, environment, and deployment ID before returning the URL. Concurrent deployments make the latest entry unreliable. If metadata association is missing or ambiguous, report the missing association rather than choosing the newest URL. See [deployment list filters](https://vercel.com/docs/cli/list).

### CLI missing or unauthenticated

Check availability using `Get-Command vercel -ErrorAction SilentlyContinue` in PowerShell or `command -v vercel` in Bash. Use the existing CLI or an already supported deployment integration. If setup is requested, install in the agreed scope with the existing package manager; do not automatically upgrade globally.

For interactive login, the user completes `vercel login` themselves. For an existing access token, use the token skill if available, injecting credentials privately. Never ask for a token in chat. If authentication fails, diagnose or report it; do not automatically upload through a no-auth service.

## Optional Claimable-Deployment Fallback

The bundled Bash helpers remain available for an explicitly authorized claimable deployment:

- `resources/deploy-codex.sh` uploads to `https://codex-deploy-skills.vercel.sh/api/deploy`.
- `resources/deploy.sh` uploads to `https://claude-skills-deploy.vercel.com/api/deploy`.

These are separate upload destinations, not evidence of authentication to the user's existing Vercel project. A CLI auth failure or a sandbox does not authorize them.

Before use:

1. Read the actual local helper and identify the current upload endpoint, packaging behavior, and claimed ownership/transfer mechanism. If they differ from these notes, stop and reassess.
2. Obtain explicit authorization for that intermediary destination and the claimable project model unless already given. Explain what source/build files will leave the machine and where. Prepare the concrete local package and manifest before asking for the final approval.
3. Create an isolated staging directory containing only approved deployable files, or use a reviewed archive. Inspect the full manifest, hidden files, symlinks, and nested directories. Excluding only `.env`, `.env.*`, `.git`, and `node_modules` is not a complete secret/private-data check. For an archive, inspect contents before upload; reject unsafe paths and links. Do not pass an unchecked tarball directly.
4. Use the helper from its verified installed location in an available Bash environment; do not assume `/mnt/skills/`, `~/.claude/`, or a Windows path works in WSL. Pass only the reviewed staging directory/archive. Do not install a shell solely for the fallback.
5. After authorized execution, validate the response and exact deployment ID. The existing helpers can label HTTP 4xx responses ready; that message alone is not build or application success. A claim URL is access-bearing: provide it only to the requester and do not place it in commits or public logs.

Do not switch between fallback endpoints after an error without target authorization. No live fallback is needed for a configuration review or skill test.

## Verify and Report the Exact Deployment

Inspect the returned ID or URL within the chosen team:

```text
vercel inspect <deployment-id-or-url> --scope <team-slug>
```

Use a bounded `--wait --timeout=45s` only if supported, or spaced status checks tied to that same deployment. Stop after a terminal failure and inspect a relevant redacted log excerpt. Check the actual environment and assigned domains; do not infer preview status from a URL's shape. [Vercel inspect](https://vercel.com/docs/cli/inspect) documents ID/URL inspection and bounded waiting.

Read-only reachability checks and browser visits are permitted within the requested deployment. Do not submit forms, trigger purchases, or modify data just to verify deployment. Respect deployment protection; do not disable authentication to get a passing check. Distinguish submitted, build-ready, reachable, and interaction-tested states. HTTP 401/403 may indicate deployment protection, not a broken build or successful app flow.

Return the verified deployment URL with the status and any unverified behavior. If no URL was returned, report the actual failure. For an authorized claimable deployment, provide its claim link privately and explain that ownership transfer remains for the user; do not claim it is already in their account.

## Troubleshooting

- **Network/sandbox failure:** Identify whether the cause is DNS, connectivity, permissions, or authentication before retrying. Use a narrow allowed escalation only for the same authorized action if required; do not disable the sandbox, change egress settings, or pick a new destination automatically.
- **Authentication failure:** Use a read-only identity check, then request local login/secret setup if necessary. Preserve the requested provider and account.
- **Build failure:** Inspect the exact deployment's logs with redaction, fix the relevant project issue, and retry only the authorized deployment. Avoid repeated blind uploads.
- **Uncertain deployment ownership:** Use commit/project metadata or the captured deployment ID. Report uncertainty if association cannot be established.
