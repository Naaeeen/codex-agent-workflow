# Isolated local browser CLI lab

Installed 2026-11-06 (Australia/Sydney). Default: Playwright CLI 0.1.23. Optional compact interaction route: agent-browser 0.41.2, with the limitations below. No global PATH, Codex configuration, skill or user Chrome profile was changed.

## Invoke

```powershell
& '{{CODEX_HOME}}\tools\browser-lab\browser-lab.ps1' pw 'C:\path\to\project\browser-work' task1 open 'http://127.0.0.1:3000'
& '{{CODEX_HOME}}\tools\browser-lab\browser-lab.ps1' pw 'C:\path\to\project\browser-work' task1 snapshot
& '{{CODEX_HOME}}\tools\browser-lab\browser-lab.ps1' pw 'C:\path\to\project\browser-work' task1 close
```

Replace `pw` with `ab` for agent-browser. Keep the same workspace and session on every command; use distinct session names for unrelated work. Use fresh snapshot refs. Close the session in a finally block. The wrapper pins executable paths, starts headless, removes inherited browser-provider environment settings, and scopes temporary files, daemon metadata and home/config discovery to `<workspace>/<session>`. It reuses only the Chromium executable from the existing Playwright cache, never its user profile. Config/profile/CDP/session overrides are rejected by the wrapper; reviewed local CDP testing uses the separate test harness. These are accidental-misconfiguration guards, not a security sandbox: eval/run-code and browser navigation remain powerful. Do not use them on untrusted instructions.

A wrapper command is capped at 30 seconds; on watchdog expiry it attempts a scoped close and returns 124. A failed scoped close requires inspecting that owned session; do not use machine-wide kill-all. CLI/native action timeouts return nonzero separately. Idle shutdown is 60 seconds.

## Runtime and reproducibility

Node: existing `{{CODEX_HOME}}\tools\agent-kit\runtime\node-v24.22.2-win-x64\node.exe`.
Chromium executable: existing `{{TOOLS_ROOT}}/browser-lab/runtime/chrome-win64/chrome.exe`.

`package.json` pins direct versions; `package-lock.json` pins transitive tarball URLs/SRI. `provenance.json` records current registry metadata, license, source and engines. `hashes.json` records SHA256 of lock, CLIs, Node and Chromium. Both top-level packages use Apache-2.0. CLI metadata says Node >=18 but its pinned Playwright dependencies require >=20; this installation uses Node 24.22.2. Agent-browser declares Node >=24 and pnpm >=11 in metadata; npm installed its published package successfully without needing pnpm.

Install used `npm install --ignore-scripts --no-fund`. Agent-browser's inspected postinstall can download a binary and patch global npm shims; it was NOT executed. The native Windows x64 executable is already included in the SRI-covered npm tarball. No native build/download step or browser download was needed. `audit.json`: 0 known npm vulnerabilities at the recorded audit; not a source-code security audit.

Reinstall with the pinned Node's npm: `npm ci --ignore-scripts --no-fund --prefix <this-directory>` after checking lock/provenance. Never silently update via npx. Recheck the cached browser path/hash on another machine.

## Actual comparison


Both tools actually passed snapshot/ref input, checkbox, precise selection of the second of two Save buttons, explicit wait for a delayed button, iframe, confirm dialog, PNG screenshot, trace generation, missing-element nonzero exit, 500ms timeout nonzero exit, and scoped close. Both PNGs were opened and visually inspected. Playwright downloaded the expected file and recovered its exact contents; it also reported the expected thrown JS error. Agent-browser repeatedly canceled downloads (both dedicated download and click + wait-download, slash-path variant included), and `errors` exited zero while outputting only a blank error marker. These are retained failures, with cause not established. Agent-browser's click on a not-yet-rendered element returned immediately as not found; explicitly wait before clicking dynamic elements.

Final local command totals, including close: PW 22 commands / 4,740 stdout+stderr bytes / 14,265ms; AB 27 commands / 1,237 bytes / 4,695ms. These are a single local fixture run with different assertion interfaces, not a controlled agent benchmark or a general speed/quality claim. They support keeping AB as an optional compact, low-overhead DOM interaction route, not replacing the more complete default. PW writes snapshots and Playwright traces; AB writes Chrome tracing events, a different format. AB trace was ~9.9MB, so compact console output does not imply smaller artifacts.

## Controlled CDP adapter

`node cdp-test.mjs <new-output-directory>` creates its own new headless Chromium profile and loopback CDP endpoint. PW connects and writes localStorage, the owner reads that mutation, AB connects in a different session and reads the same storage. Both CLI closes preserve the owner, which is then explicitly closed. Actual evidence: `...\browser\cdp-reviewed\cdp-results.json`, four capability checks plus three cleanup checks passed. This qualifies local CDP attachment/cross-session state only. It does not validate a cloud provider, remote network, billing, Vercel Sandbox, browser provisioner, authentication or users' real Chrome profiles.

## Integration recommendation

Root launcher should route local terminal browser automation to this `pw` wrapper, retain host CUA for the user's logged-in GUI state, and expose `ab` only as an explicit alternative with the documented download/error gaps. Keep cloud work preparation-only until a separate authorized provider job. Do not present local CDP success as cloud acceptance. Preserve native browser/runtime assertions as evidence separate from model judgment or human review.

Cleanup evidence `...\browser\cleanup.json`: no scoped Chrome/Node/agent-browser process remained after the final fixture/CDP tests, and no temporary profile directory remained in final-run. Empty isolated home/temp/daemon directories and the deliberately retained CDP test profile directory/artifacts remain as test evidence. No daily Chrome profile was touched.

## Primary sources

- https://github.com/microsoft/playwright-cli/releases/tag/v0.1.23
- https://github.com/vercel-labs/agent-browser/tree/v0.41.2
- https://registry.npmjs.org/@playwright/cli/0.1.23
- https://registry.npmjs.org/agent-browser/0.41.2

Independent fresh-context review completed after fixes; see the task evidence review.md. Watchdog-expiry and forced cleanup-failure paths were inspected statically, not runtime fault-injected.

