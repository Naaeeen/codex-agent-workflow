# Local document checks

Run on explicit task/project paths, not the whole home directory. These are
optional additions for relevant documentation changes, not replacements for
the project's build, lint or tests.

`agent-tool.ps1 typos --isolated --format json --sort PATH`

Typos reports candidates; exit 2 can mean findings. Inspect identifiers, names,
URLs and technical terms before accepting a correction. Use the project's own
allowlist where present. Avoid --write-changes unless the task authorizes the
reviewed edits; the default does not modify inputs.

`agent-tool.ps1 lychee --offline --include-fragments=anchor-only --format json --no-progress PATH`

Lychee validates selected local Markdown/HTML targets and heading fragments;
--offline blocks HTTP checks. It does not prove external URLs work or the page
looks correct. Use a selected config to avoid unintended settings; preserve
actual exit codes and distinguish skipped external links from checked links.
If online validation is needed, bound the chosen public URLs and request load.

Sources: https://github.com/crate-ci/typos ; https://github.com/lycheeverse/lychee
