---
name: nextjs-turbopack
description: Diagnose Next.js bundler selection, Turbopack compatibility, development caching or bundle-analysis issues. Use the installed Next.js version and official guidance; ordinary UI implementation does not need this workflow.
---

# Next.js Bundler Diagnosis

Inspect `next` in the manifest/lockfile, the actual dev/build scripts, Next configuration and CI before changing the bundler. If a current Vercel Next.js or Turbopack skill is already being used, consult it for the specific version-sensitive detail instead of loading duplicate general guidance.

Next.js 16 uses Turbopack by default for both development and production builds. Older releases differ; check the installed release's supported flags and features. Do not assume an unknown `--no-turbopack` flag works, or recommend a major upgrade solely to solve one build issue.

- Reproduce with the existing project command and preserve its exit code. Identify unsupported loaders/plugins, environment differences and application errors separately.
- Check version-specific configuration, cache behavior and filesystem inputs. Do not delete caches or change package managers without a reason tied to the failure.
- Compare Webpack only when an actual compatibility issue or measured tradeoff justifies it, using that release's supported option. Preserve required project plugins.
- For bundle size, use the official analyzer compatible with the installed release and verify the relevant runtime path. A generic speed claim is not a project measurement.
- After a change, rerun the affected dev/build and user-flow checks. Keep security and environment settings unchanged unless the task requires a reviewed change.

Primary reference: [Next.js Turbopack](https://nextjs.org/docs/app/api-reference/turbopack).
