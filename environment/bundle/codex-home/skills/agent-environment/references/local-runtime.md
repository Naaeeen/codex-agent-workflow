# Local runtime compatibility notes

Verified 2026-11-05; re-check against the installed client before using these as
current facts. These notes do not replace official product documentation.

- PATH CLI was 0.157.1; the desktop binary used for tests was
  <USER_HOME>\AppData\Local\OpenAI\Codex\bin\<APP_BUILD>\codex.exe,
  version 0.166.0-alpha.6. Do not assume different clients expose identical flags.
- The shared desktop config contains the app-owned
  computer_use.windows.always_allowed_app_ids setting. Strict native exec rejects
  that field, while ordinary execution succeeds with deprecation diagnostics.
  Do not delete UI authorization preferences just to make a CLI strict check pass.
- Explicit Windows sandbox settings remain supported. The two generic warning
  messages do not justify changing sandbox or approval defaults.
- In this tested CLI, completion usage copies cumulative thread totals. Preserve
  raw numeric snapshots, classify scope by source/version, and never sum resumed
  snapshots as if they were independent turns.
- The local-analysis experiment profile was removed: its small ABBA trial showed
  no stable benefit and more nonfatal errors. It is not an installed preset.
- Worker roles' read-only wording is a behavioral constraint; effective parent
  permissions and runtime controls determine actual filesystem access.
