---
name: e2e-testing
description: Create or repair a Playwright end-to-end test suite, including page objects, fixtures, CI, artifacts, and flaky-test diagnosis. Use for maintained test coverage; use browser-control skills for ad hoc browsing.
---

# E2E Testing Patterns

Use the repository's installed Playwright version, package manager, existing fixtures, and CI. The examples below assume TypeScript and npm; adapt selectors, API contracts, and commands to the actual application. A template is not evidence that a workflow passed.

## Test File Organization

```
tests/
├── e2e/
│   ├── auth/
│   │   ├── login.spec.ts
│   │   ├── logout.spec.ts
│   │   └── register.spec.ts
│   ├── features/
│   │   ├── browse.spec.ts
│   │   ├── search.spec.ts
│   │   └── create.spec.ts
│   └── api/
│       └── endpoints.spec.ts
├── fixtures/
│   ├── auth.ts
│   └── data.ts
└── playwright.config.ts
```

## Page Object Model (POM)

```typescript
import { expect, type Page, type Locator } from '@playwright/test'

export class ItemsPage {
  readonly page: Page
  readonly searchInput: Locator
  readonly itemCards: Locator
  readonly createButton: Locator

  constructor(page: Page) {
    this.page = page
    this.searchInput = page.locator('[data-testid="search-input"]')
    this.itemCards = page.locator('[data-testid="item-card"]')
    this.createButton = page.locator('[data-testid="create-btn"]')
  }

  async goto() {
    await this.page.goto('/items')
    await expect(this.searchInput).toBeVisible()
  }

  async search(query: string) {
    const origin = new URL(this.page.url()).origin
    // This example assumes GET /api/search?q=... is triggered by filling the input.
    const responsePromise = this.page.waitForResponse(response => {
      const url = new URL(response.url())
      return url.origin === origin && url.pathname === '/api/search' &&
        url.searchParams.get('q') === query && response.request().method() === 'GET'
    })
    await this.searchInput.fill(query)
    const response = await responsePromise
    expect(response.status()).toBe(200)
    // The caller asserts the rendered result; a response alone is not UI readiness.
  }
}
```

## Test Structure

```typescript
import { test, expect } from '@playwright/test'
import { ItemsPage } from '../../pages/ItemsPage'

test.describe('Item Search', () => {
  let itemsPage: ItemsPage

  test.beforeEach(async ({ page }) => {
    itemsPage = new ItemsPage(page)
    await itemsPage.goto()
  })

  test('should search by keyword', async ({ page }, testInfo) => {
    await itemsPage.search('test')

    await expect(itemsPage.itemCards.first()).toContainText(/test/i)
    await page.screenshot({ path: testInfo.outputPath('search-results.png') })
  })

  test('should handle no results', async ({ page }) => {
    await itemsPage.search('xyznonexistent123')

    await expect(page.locator('[data-testid="no-results"]')).toBeVisible()
    await expect(itemsPage.itemCards).toHaveCount(0)
  })
})
```

## Playwright Configuration

```typescript
import { defineConfig, devices } from '@playwright/test'

// Set BASE_URL only for the intended, authorized test deployment.
const targetURL = process.env.BASE_URL

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: './test-results',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'playwright-results.xml' }],
    ['json', { outputFile: 'playwright-results.json' }]
  ],
  use: {
    baseURL: targetURL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
  ],
  webServer: targetURL ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
```

## Flaky Test Patterns

### Quarantine

Quarantine only an identified failure with an issue and an owner; report skipped coverage. A retry that passes is still a flaky result, not a repaired test.

```typescript
test('flaky: complex search', async ({ page }) => {
  test.fixme(true, 'Flaky - Issue #123')
  // test code...
})

test('conditional skip', async ({ page }) => {
  test.skip(!!process.env.CI, 'Flaky in CI - Issue #123')
  // test code...
})
```

### Identify Flakiness

Use the already-installed local runner (examples assume npm with Playwright installed); do not let a missing runner trigger an implicit package download.

```bash
npx playwright test tests/search.spec.ts --repeat-each=10
npx playwright test tests/search.spec.ts --retries=3
```

### Common Causes & Fixes

**Actionability:** prefer locators; clicks already wait for a visible, stable, enabled target that receives events. Neither `page.click()` nor `locator.click()` waits for application-specific business readiness after the click.

```typescript
await page.getByTestId('button').click()
await expect(page.getByTestId('result')).toHaveText('Complete')
```

**Network timing:**
```typescript
// Bad: arbitrary timeout
await page.waitForTimeout(5000)

// Good: assert the user-visible outcome with automatic retries
await expect(page.getByTestId('data-result')).toHaveText('Expected result')
// When a response is part of the contract, register its wait before the trigger,
// as in ItemsPage.search; then still assert the rendered outcome.
```

**Animation timing:** `locator.click()` includes stability checks. Assert the resulting state instead of using `networkidle` or a fixed delay as readiness. For a custom animation that matters to the test, assert its actual completion condition.

## Artifact Management

### Screenshots

```typescript
// Inside a test callback receiving testInfo: unique per test, project, and retry.
await page.screenshot({ path: testInfo.outputPath('after-login.png') })
await page.screenshot({ path: testInfo.outputPath('full-page.png'), fullPage: true })
await page.getByTestId('chart').screenshot({ path: testInfo.outputPath('chart.png') })
```

### Traces

In Playwright Test, prefer `use.trace` in the configuration; it also records test assertions. For a standalone Playwright Library script, use context tracing (not Chromium's separate performance-tracing API):

```typescript
const context = await browser.newContext()
await context.tracing.start({ screenshots: true, snapshots: true })
try {
  const page = await context.newPage()
  // ... script actions ...
} finally {
  await context.tracing.stop({ path: 'artifacts/trace.zip' })
  await context.close()
}
```

Choose a task-specific output path for standalone scripts. Do not manually start tracing on a context whose tracing is already managed by Playwright Test.

### Video

```typescript
// Fields in defineConfig({ ... }); video files go under the test output directory.
outputDir: './test-results',
use: {
  video: 'retain-on-failure',
}
```

## CI/CD Integration

The npm example below starts the local application through `webServer`. For an existing deployment, set `BASE_URL` and verify that target separately. Use the project's declared supported Node version in place of `lts/*` when available; preserve its package-manager lockfile and reviewed action pins.

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: 'lts/*'
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: playwright-report
          path: |
            playwright-report/
            test-results/
          retention-days: 30
```

## Test Report Template

```markdown
# E2E Test Report

**Date:** YYYY-MM-DD HH:MM
**Duration:** Xm Ys
**Status:** PASSING / FAILING / PARTIAL / NOT RUN

## Summary
- Tested revision, environment, and command: [...]
- Total: X | Passed: Y (Z%) | Failed: A | Flaky: B | Skipped: C
- Mocked boundaries and unverified backend/provider behavior: [...]

## Failed Tests

### test-name
**File:** `tests/e2e/feature.spec.ts:45`
**Error:** Expected element to be visible
**Screenshot:** test-results/<test-output>/failed.png
**Recommended Fix:** [description]

## Artifacts
- HTML Report: playwright-report/index.html
- Screenshots: test-results/<test-output>/*.png
- Videos: test-results/<test-output>/*.webm
- Traces: test-results/<test-output>/*.zip
```

## Wallet / Web3 Testing

This is a UI contract mock, not wallet, signature, or blockchain integration coverage. Match the application's test chain and supported provider methods; reject unexpected signing or transaction requests.

```typescript
test('wallet connection', async ({ page, context }) => {
  // Mock wallet provider
  await context.addInitScript(() => {
    Object.defineProperty(window, 'ethereum', { value: {
      isMetaMask: true,
      request: async ({ method }: { method: string }) => {
        if (method === 'eth_requestAccounts')
          return ['0x1234567890123456789012345678901234567890']
        if (method === 'eth_chainId') return '0x539' // Example local test chain.
        throw new Error(`Unexpected mocked wallet request: ${method}`)
      }
    } })
  })

  await page.goto('/')
  await page.locator('[data-testid="connect-wallet"]').click()
  await expect(page.locator('[data-testid="wallet-address"]')).toContainText('0x1234')
})
```

## Financial / Critical Flow Testing

`NODE_ENV` describes the runner, not the destination or payment mode. Before a mutating flow, verify the actual app/backend/provider targets, test-mode credentials, and isolated test account or test chain. Use the project's verified sandbox fixture; a URL containing "test" or a local frontend alone is not sufficient. If isolation is unverified, stop before submission and report the untested boundary.

For an authorized preview-only check of a UI known not to submit during input:

```typescript
test('trade preview only', async ({ page }) => {
  await page.goto('/markets/test-market')
  await page.getByTestId('position-yes').click()
  await page.getByTestId('trade-amount').fill('1.0')
  await expect(page.getByTestId('trade-preview')).toContainText('1.0')
  // No confirm/submit/sign action: this does not verify execution or settlement.
})
```

For an explicitly authorized, verified sandbox execution test, register the precise response wait before submitting, then verify the persisted transaction outcome. Cover rejection and duplicate/idempotent submission where applicable; use disposable state and the project's cleanup. A mocked success response proves the UI branch only.

## Current API References

- [Readiness and waiting for responses](https://playwright.dev/docs/api/class-page#page-wait-for-response)
- [Locator actionability](https://playwright.dev/docs/actionability)
- [Tracing](https://playwright.dev/docs/api/class-tracing)
- [Recording configuration](https://playwright.dev/docs/test-use-options#recording-options)
- [Per-test output paths](https://playwright.dev/docs/api/class-testinfo#test-info-output-path)
- [CI setup](https://playwright.dev/docs/ci-intro)
