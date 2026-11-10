# Execution providers and handoff

Codex Cloud: a published, accessible environment and matching repository are
prerequisites. Current setup found zero such environments. The installed CLI
exposes cloud exec/status/list/diff/apply, but it remains experimental. Verify
current help and the exact ID type before dispatch. CLI environment IDs and
saved environmentConfigId values are not assumed interchangeable. Cloud does
not automatically receive personal local skills, Windows tools or browser state.
Copy only relevant portable instructions into approved project artifacts.

Vercel Sandbox: the account connection exists, but this setup did not create a
project/session or validate plan/quota. User chose preparation without charges.
For a future authorized test use one short nonpersistent session, no open ports,
deny-all network where compatible, no inherited secrets, explicit cwd and argv,
and stop in finally. Nonzero command exits must be checked; they do not necessarily
throw. Do not call a local mock/WSL replay a cloud result.

Local/WSL: WSL remains this computer, not cloud. Use its own interpreter and
dependencies. The handoff fixture was actually extracted, executed and returned
on existing Ubuntu, then verified from Windows. This checks portability for that
small fixture only, not arbitrary software or cloud isolation.

Before promotion verify the actual output, not only its hash schema. The helper
detects declared byte changes and path mistakes, but cannot authenticate the
author or find every secret hidden in ordinary text. It is not an OS sandbox.

Sources:
- https://learn.chatgpt.com/docs/environments/cloud-environments
- https://learn.chatgpt.com/docs/remote-connections
- https://vercel.com/docs/sandbox
