# Local browser routing

Use existing host browser/CUA tools for the user's already authenticated browser
when that state is required. Do not open the normal Chrome profile through a new
remote-debugging port or export its cookies to cloud.

For isolated local automation, use the shared `browser` route with backend pw,
absolute task artifact directory, and a unique session name. It selects the pinned
Playwright CLI and a fresh headless profile. Snapshot, use current refs or stable
role/label/test-id selectors, assert the result, and close that session. A CLI
interaction is not a maintained Playwright Test suite; retain project tests when
repeatable regression coverage is requested.

Backend ab is optional for compact snapshot-driven exploration. Tests retained
download cancellation and incomplete JS-error messages; use pw for those flows.
Both backends need explicit waits for the tested delayed element. Different trace
formats and command counts do not establish general speed/quality superiority.

A separate owned-browser CDP experiment passed. That qualifies the local transport,
not a remote provider, credentials, billing or the user's real browser. Cloud
browser operation requires a ready, separately authorized provider and new state.
Current Codex Cloud does not offer browser/computer use; keep that part local or
use an explicitly provisioned browser service. See execution-routing for hybrid
work and verified return artifacts.

Sources: https://playwright.dev/docs/getting-started-cli ;
https://github.com/vercel-labs/agent-browser ;
https://developer.chrome.com/blog/remote-debugging-port
