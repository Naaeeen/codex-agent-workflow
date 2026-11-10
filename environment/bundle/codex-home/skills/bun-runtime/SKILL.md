---
name: bun-runtime
description: Bun as runtime, package manager, bundler, and test runner. When to choose Bun vs Node, migration notes, and Vercel support.
---

# Bun Runtime

Bun is a fast all-in-one JavaScript runtime and toolkit: runtime, package manager, bundler, and test runner.

## When to Use

- Consider Bun when it is the project toolchain or the user requests an adoption comparison. For new projects, compare actual dependencies, hosting support and measured workflow needs; do not migrate an existing lockfile or runtime just because this skill is selected.
- **Prefer Node** for: maximum ecosystem compatibility, legacy tooling that assumes Node, or when a dependency has known Bun issues.

Use when: adopting Bun, migrating from Node, writing or debugging Bun scripts/tests, or configuring Bun on Vercel or other platforms.

## How It Works

- **Runtime**: JavaScriptCore-based runtime with substantial Node.js compatibility. Check the installed version and required APIs; compatibility is not universal.
- **Package manager**: Current releases use text `bun.lock`; older releases used binary `bun.lockb`. Respect the repository version and lockfile. Measure installation performance on the actual project before claiming a gain.
- **Bundler**: Built-in bundler and transpiler for apps and libraries.
- **Test runner**: Built-in `bun test` with Jest-like API.

**Migration from Node**: First inspect `packageManager`, lockfiles, CI and deployment runtime. In an authorized isolated migration, run the existing build/test and critical integration checks with the chosen Bun version. Keep the original toolchain until compatibility is demonstrated; do not replace APIs or package managers based on a speed claim alone.

**Hosting**: Verify current Bun support and the required deployment configuration for the selected platform. Reuse project scripts and a frozen lockfile where supported. CLI examples below are for an already-selected Bun project, not automatic installation steps.

Reference: [Bun Node.js compatibility](https://bun.sh/docs/runtime/nodejs-compat).

## Examples

### Run and install

```bash
# Install dependencies (creates/updates bun.lock or bun.lockb)
bun install

# Run a script or file
bun run dev
bun run src/index.ts
bun src/index.ts
```

### Scripts and env

```bash
bun run --env-file=.env dev
FOO=bar bun run script.ts
```

### Testing

```bash
bun test
bun test --watch
```

```typescript
// test/example.test.ts
import { expect, test } from "bun:test";

test("add", () => {
  expect(1 + 2).toBe(3);
});
```

### Runtime API

```typescript
const file = Bun.file("package.json");
const json = await file.json();

Bun.serve({
  port: 3000,
  fetch(req) {
    return new Response("Hello");
  },
});
```

## Best Practices

- Commit the lockfile (`bun.lock` or `bun.lockb`) for reproducible installs.
- Prefer `bun run` for scripts. For TypeScript, Bun runs `.ts` natively.
- Keep dependencies up to date; Bun and the ecosystem evolve quickly.
