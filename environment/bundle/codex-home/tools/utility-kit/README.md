# Isolated local utilities — verified 2026-11-05

This is a new version-pinned installation. It does not modify PATH, existing tools, Codex configuration, skills, model settings, or launcher code. Native executable archives were independently matched to the official release asset SHA-256. Archives were inspected and only the expected executable was extracted into each versioned bin directory. Project licenses and source metadata are in `provenance/` and per-tool `licenses/` directories.

| Utility | Version | Relative entrypoint | Intended bounded use |
|---|---|---|---|
| DuckDB | 2.0.0 | `duckdb/2.0.0/bin/duckdb.exe` | Local CSV/SQL analysis |
| Hyperfine | 2.0.0 | `hyperfine/2.0.0/bin/hyperfine.exe` | Repeat known local commands and export measurements |
| Typos | 1.52.0 | `typos/1.52.0/bin/typos.exe` | Report source/docs spelling candidates |
| Lychee | 0.24.2 | `lychee/0.24.2/bin/lychee.exe` | Offline local Markdown file/heading checks |
| Trafilatura | 2.3.1 | `trafilatura/2.3.1/venv/Scripts/trafilatura.exe` | Extract local HTML supplied on stdin |

## Integration contract and observed limits

- DuckDB: pass `-no-agent -json`. In this Codex environment `CODEX_CI` enables agent output automatically unless explicitly disabled. SUM of integers can yield HUGEINT whose CLI JSON representation is a string; accept that schema or explicitly CAST to a suitable numeric type. The acceptance fixture uses BIGINT and checks nulls, Unicode, a left join, aggregation, row_number, and invalid SQL.
- Hyperfine 2.0 defaults to `--shell=none`. Do not pass shell pipelines without explicitly selecting a shell. The measured command, plus setup/prepare/cleanup hooks if selected, is executable code and needs appropriate task authorization. Schema version 2 has `results[].measurements` and `results[].summary[metric]` with explicit units/count. A failing command produces a nonzero Hyperfine exit unless the caller deliberately enables ignore-failure. Four runs were validated in seconds; these are functional checks, not comparative performance claims.
- Typos reports changes unless `--write-changes` is explicitly supplied. Prefer explicit input paths and `--isolated`; add `--config` only for a chosen local allowlist. Typo findings return exit 2. The fixture preserves an intentional identifier using `[default.extend-identifiers]`; Unicode inputs remain byte-identical.
- Lychee: use `--offline --include-fragments=anchor-only --format json --no-progress` and explicit local file paths. Use an explicit chosen config to avoid implicit project settings. Correct links return 0; missing local files/headings return 2. `--offline` plus zero hits to a temporary loopback HTTP sentinel was tested. This is not OS packet-capture proof. The check never wrote its Markdown inputs.
- Trafilatura: use the executable above, or its venv Python for `trafilatura.extract`. `python -m trafilatura` is unsupported. Supply raw local HTML on stdin; CLI `-i` means a URL input list and is not the raw-HTML file option. The tested local CLI flags are `--fast --precision --no-comments --with-metadata --json`. `fast=True, favor_precision=True, include_comments=False` is the equivalent Python configuration. Default fallback returned navigation text for a navigation-only fixture; fast mode returned no result for that fixture while retaining the test article. Empty output is an abstention and must not be called successful extraction. This small synthetic test is not an extraction-accuracy benchmark.

## Python dependency provenance

The Trafilatura venv uses the existing Python 3.14 runtime and contains 17 installed application distributions. `pip check` passed. Every installed application wheel was independently matched to its official PyPI release JSON and saved in `downloads/wheels/`. `trafilatura/2.3.1/requirements-lock.txt` pins every distribution and SHA-256; an offline `pip --isolated install --dry-run --ignore-installed --no-index --find-links downloads/wheels --require-hashes -r ...` resolved successfully. Exact license files/METADATA were preserved. No PyPI known-vulnerability records were reported on verification; this does not establish absence of vulnerabilities.

## Evidence and rollback

`manifest.json` records absolute entrypoints and source URLs; `integrity.json` records binary and archive hashes. `provenance/acceptance-results.json` has case results. Full executable test scripts, synthetic fixtures, raw outputs, the observed default-fallback failure, and unsupported module invocation are retained in the evidence directory named by the manifest. No source repository, user document, external account, service, or global configuration was changed. Rollback is deletion of this newly created directory only, after resolving and checking its exact path and confirming no unexpected files have been added.
