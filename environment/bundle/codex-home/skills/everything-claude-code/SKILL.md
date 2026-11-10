---
name: everything-claude-code
description: Work on the ECC source repository itself, such as its skill catalog, installer, compatibility mappings or tests. Do not use this as general Codex coding guidance or a reason to install the ECC bundle.
---

# Maintaining ECC Source

First verify that the current checkout is the ECC repository or an explicitly selected fork. This is a repository-specific workflow, not a global set of architecture or language rules.

- Read that revision's AGENTS.md, CONTRIBUTING, package manifest, lockfile and CI. Use their current commands and commit conventions; an old generated summary is not evidence of today's test runner, layout or coverage.
- For a skill or command change, locate the canonical source and actual Codex/Claude compatibility copies before editing. Update only the entrypoints maintained by that checkout; avoid an independent mirror that will drift.
- For catalog changes, compare manifest entries with actual directories and run the repository's native catalog/packaging checks.
- For installer or hook changes, verify supported host/OS behavior and the affected regression tests. Do not run an installer against personal settings merely to test source changes.
- Preserve local modifications and selected model/permissions. Upstream examples are candidates to review, not authority to overwrite this user's adaptations.

Source: [ECC](https://github.com/affaan-m/ECC). Inspect the actual revision's compatibility documentation rather than assuming feature parity across agents.
