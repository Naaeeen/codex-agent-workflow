---
name: webapp-testing
description: Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs.
license: Complete terms in LICENSE.txt
---

# Web Application Testing

Use the project's existing browser tests or an available supported browser capability. Python Playwright is one option when installed; do not install another browser integration solely to follow this skill.

**Helper Scripts Available**:
- `scripts/with_server.py` - Manages server lifecycle (supports multiple servers)

Verify that a helper exists and fits the task before executing it. For a trusted installed helper, `--help` can establish usage; inspect source when needed to assess side effects or customize behavior. Resolve helper paths from this skill's actual installation, not the project working directory.

## Decision Tree: Choosing Your Approach

```
User task → Is it static HTML?
    ├─ Yes → Read HTML file directly to identify selectors
    │         ├─ Success → Write Playwright script using selectors
    │         └─ Fails/Incomplete → Treat as dynamic (below)
    │
    └─ No (dynamic webapp) → Is the server already running?
        ├─ No → Run: python scripts/with_server.py --help
        │        Then use the helper + write simplified Playwright script
        │
        └─ Yes → Reconnaissance-then-action:
            1. Navigate and wait for the relevant UI condition
            2. Take screenshot or inspect DOM
            3. Identify selectors from rendered state
            4. Execute actions with discovered selectors
```

## Example: Using with_server.py

To start a server, run `--help` first, then use the helper. Supply foreground commands that keep running; do not use daemon mode, detached sessions, or background shell operators. The helper rejects already-listening loopback ports, discards server output, and cleans up only the process groups it starts, including the automation command and its descendants. Use non-interactive automation; its output remains visible, but its stdin is closed. `--timeout` bounds server startup, not the automation runtime. Run a failing server directly when its logs are needed. Keep secrets out of command arguments.

Readiness here means a local TCP listener, not an HTTP response or a usable UI. Assert the actual page state in the automation. Port prechecks cannot prove ownership if another process claims the port concurrently. POSIX children that deliberately detach, or a helper killed with SIGKILL, cannot be reliably cleaned up by this helper; Windows requires Job Object assignment and fails before launching the server if that is unavailable.

**Single server:**
```bash
python scripts/with_server.py --server "npm run dev" --port 5173 -- python your_automation.py
```

**Multiple servers (e.g., backend + frontend):**
```bash
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_automation.py
```

To create an automation script, include only Playwright logic (servers are managed automatically):
```python
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True) # Prefer headless for unattended local checks
    page = browser.new_page()
    page.goto('http://localhost:5173') # Server already running and ready
    # Replace with the task's actual readiness condition, not a generic load guess.
    expect(page.get_by_role('button', name='Save')).to_be_enabled()
    # ... your automation logic
    browser.close()
```

## Reconnaissance-Then-Action Pattern

1. **Inspect rendered DOM**:
   ```python
   page.screenshot(path='/tmp/inspect.png', full_page=True)
   content = page.content()
   page.locator('button').all()
   ```

2. **Identify selectors** from inspection results

3. **Execute actions** using discovered selectors

## Common Pitfall

Network silence is not proof that the relevant UI is ready, and polling can prevent it entirely. Use locator assertions for the required visible, enabled, or completed state. When the task depends on a specific request, await that response and still check the resulting UI. Keep waits bounded and report timeouts as failed or incomplete checks.

## Best Practices

- Prefer the existing helper when its lifecycle and readiness checks fit the task; inspect or adapt it when they do not.
- Use `sync_playwright()` for synchronous scripts
- Always close the browser when done
- Use descriptive selectors: `text=`, `role=`, CSS selectors, or IDs
- Prefer auto-waiting locators and retrying assertions over fixed sleeps. Check the observed outcome after each important action; a click alone does not establish success.

## Reference Files

- **examples/** - Examples showing common patterns:
  - `element_discovery.py` - Discovering buttons, links, and inputs on a page
  - `static_html_automation.py` - Using file:// URLs for local HTML
  - `console_logging.py` - Capturing console logs during automation
