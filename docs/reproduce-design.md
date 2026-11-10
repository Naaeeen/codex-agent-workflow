# Portable environment installer

## Full Windows x64 setup

Run `setup.ps1` from the checkout. Use a destination outside that checkout,
under an existing local directory. Preview needs a Python 3.11+ runner. Apply
uses the exact Python executables required by the selected groups.

```powershell
.\setup.ps1 -Destination $destination
.\setup.ps1 -Destination $destination -Python313 $python313 -Python314 $python314 -Apply
```

The full plan includes every automatic group. Add `-SkipModelWeights` to omit
the QMD and Docling weight downloads. Add `-Group npm-agent-kit,python-pdf-layout`
to select a smaller plan. The driver includes prerequisites in installation
order, verifies the selected x64 Python versions and wheel zlib versions before
writing the destination, and prints the launch command on success. On retry it
checks the existing configuration and installed groups against the source
manifest and receipts. Use the dependency preview below to see the manual
account and platform steps.

## Stage or verify configuration separately

Run these commands from the directory containing `reproduce.py`. Python 3.11+
is sufficient for these steps.

```text
python reproduce.py ../my-codex-workflow
python reproduce.py ../my-codex-workflow --apply
python reproduce.py ../my-codex-workflow --verify
```

The first command checks the package and previews the managed file paths. Apply
writes the environment into a sibling staging directory and publishes it in
one no-replace rename. An existing destination stays untouched. Verify compares
the managed files and their modes where supported against the current package.
It verifies the generated launcher and receipt as well. All three operations
are offline and require no Codex login or model request. The installer does
not inspect unmanaged files in the destination, including account state that
a reader creates later.

## Launch the installed environment

```text
python ../my-codex-workflow/launch.py -- --version
python ../my-codex-workflow/launch.py -- login
python ../my-codex-workflow/launch.py --project /path/to/your/project
python ../my-codex-workflow/launch.py --project /path/to/your/project -- exec "Inspect the repo"
```

With no `--project` flag, the launcher uses the bundled `project/` directory.
An external project keeps its own repository instructions and project Skills.
Bundled shared Skills under `codex-home/skills/` are available from both
locations. The launcher sets `CODEX_HOME` for its child process, disables the
shared daemon, and selects file-based CLI authentication in the installed home.
The reader signs in with their own account. The default child environment drops
`OPENAI_API_KEY`, `CODEX_API_KEY`, `CHATGPT_API_KEY`, and `CODEX_ACCESS_TOKEN`.
`--allow-env-auth` opts back into those inherited variables. On Windows, the
launcher verifies the installed Node 24.22.2 executable and its dependency
receipt, then puts its directory first on the child process PATH. This lets the
bundled evaluation grader resolve `node` on a machine with no global Node.
Pass `--inherit-node-path` before the forwarded Codex arguments to use the
project's existing Node selection. Other PATH entries and the OS home are
inherited. [Pinned Node checksums](https://nodejs.org/dist/v24.22.2/SHASUMS256.txt)

Use `--codex /path/to/codex` to select a binary explicitly. On Windows the
default is the pinned Codex CLI 0.157.1 from the applied dependency group,
when installed. The launcher checks its executable against the group receipt.
It also checks the executable's pinned release SHA-256.
If that group is absent, it looks for `codex.exe` on PATH, which may be another
version. To select an npm-installed client through `--codex`, pass the native
executable in its architecture package. [Pinned Codex CLI release](https://github.com/openai/codex/releases/tag/rust-v0.157.1)

Install pinned CLIs and other runtime dependencies separately according to the
environment's tool documentation. Local package staging, dependency
installation, account authorization, enabling a connector and running an
agent are separate actions.

## Manifest contract

`environment/manifest.json` has `schema_version: 1` and a nonempty `files`
array. Each entry specifies these fields.

| Field | Meaning |
| --- | --- |
| `source` | Slash-delimited path under `environment/bundle/`, relative to `environment/` |
| `target` | Slash-delimited path under `codex-home/`, `project/` or `tooling/` |
| `sha256` | Lowercase SHA-256 of the exact source bytes |
| `executable` | JSON boolean for the installed owner execute bit on POSIX |
| `render` | Optional `"paths"` for UTF-8 text with quoted path placeholders |

Quoted TOML or PowerShell path strings can use `{{ENV_ROOT}}`,
`{{CODEX_HOME}}`, and `{{TOOLS_ROOT}}`. They expand to slash-delimited
absolute paths for the installation, Codex home and
`codex-home/tools/` respectively. The installer accepts path characters common
to these quoted strings, including spaces, parentheses and Unicode letters,
and refuses shell interpolation characters such as `$` or a backtick. It checks
the source digest before rendering and stores the rendered digest in
`reproduction-receipt.json`. Use the same package when verifying an existing
installation. If a curated file contains a rendered path, use a new install
when relocating the environment.

The installer rejects traversal, target collisions, symlinks, junctions,
other reparse points and hard-linked inputs. Run it from a trusted checkout
with a destination parent you control. The package manifest checks file
integrity. Provenance and redistribution review happen separately. The receipt
does not attest to any file created later by Codex or another program.

## Evidence

- Windows and Codex CLI `0.157.1` were exercised with a temporary installation.
  The generated launcher started the CLI app server using the isolated home.
  `skills/list` returned the enabled user Skill for both the bundled project
  and an unrelated project. It returned the bundled project Skill only for
  the bundled project. The two discovery results had zero errors. This probe
  disabled plugins and used a non-listening loopback proxy to prevent outbound
  requests. No model turn was started.
- A second native probe used the staged release bundle under `--strict-config`.
  All 62 exported Skill files were discovered and enabled in both the bundled
  project and an unrelated project, with zero Skill discovery errors.
- Atomic no-replace publication, tamper checks and link rejection were tested
  with Windows and Ubuntu WSL Python. macOS uses `renamex_np` with `RENAME_EXCL`
  and has yet to be exercised. Apply stops if the platform lacks a supported
  no-replace operation.
- OpenAI documents the current repository Skill roots and the app-server
  `skills/list` method. The CLI probe separately established compatibility
  with the isolated `CODEX_HOME/skills` path for the installed version.
  [Skill discovery](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills) ·
  [App-server methods](https://learn.chatgpt.com/docs/app-server#api-overview)

## Install runtime groups

The Windows x64 dependency manifest is separate from the configuration bundle.
Run the preview after applying the configuration.

```text
python install_dependencies.py ../my-codex-workflow
python install_dependencies.py ../my-codex-workflow --group GROUP_ID
python install_dependencies.py ../my-codex-workflow --group GROUP_ID --apply
```

The preview lists dependency groups and any manual steps. Each `--apply` needs
an explicit group id. Repeat `--group` to process groups in order, with
prerequisites first. The installer verifies the applied configuration receipt
before staging any dependencies. It also verifies the installed group's files
and recipe inputs on retry, reuses a verified group and refuses to replace a
directory with drift or an absent completion receipt.

Public native artifacts use HTTPS with a pinned SHA-256. Archive entries are
validated as regular files or directories before writing files, and only the
selected archive paths are copied. npm uses the manifest's pinned Node and npm,
registry-backed lockfile integrity and `npm ci --ignore-scripts`. A
`layout: "node_modules"` group publishes only the dependency directory so
the existing package files and controllers stay in their original layout.
`verified_copies` can activate a specified native Node binding inside staging
when its source SHA-256 matches. Lifecycle scripts stay disabled.
Python groups use the selected base Python version and a new venv, install
only wheels, and use hashes where the lock contains them. A group listed with
`integrity: "pins"` has exact package versions. Its upstream wheel bytes are
not pinned.

The Semgrep venv first installs its hash-locked pip 26.3 wheel through the
managed bootstrap recipe. The dependency receipt records the bootstrap and
main lock inputs separately. The main lock resolves the rebuilt wheel from
the temporary wheelhouse and checks its SHA-256.

Local patch-wheel groups download a SHA-256-pinned public upstream wheel,
apply exact metadata substitutions, regenerate its wheel RECORD and check
the entire rebuilt wheel against the recorded output digest. The recipe
specifies the Python and zlib versions used for the original compression.
Install a consuming pip group with the exact base Python listed for that group
after its wheel prerequisite is ready.

Package-manager subprocesses use temporary homes and caches inside the
installation, with no inherited account environment variables. Dependency
downloads use public registries or the explicit HTTPS sources in the
manifest. Connector authorizations, native extension activation, and any
other group printed as manual require separate action.

Native and npm groups are published by no-replace rename. A Windows venv
contains absolute paths, so the installer claims its final directory before
building it and publishes the completion receipt last. If the installer is
abruptly terminated during venv creation, inspect the incomplete group and
use a fresh destination for a clean retry.

Smoke-tested in temporary Windows installations using the actual pinned
artifacts. Node reported 24.22.2 and npm reported 11.19.1. The agent-kit npm
recipe installed 282 packages with lifecycle scripts disabled and repomix
reported 1.18.1 from the original `node_modules` layout. The hash-locked PDF
venv installed eight wheels and imported pdfplumber 0.11.9. The Serena and
Semgrep wheel groups both reproduced the original patched wheel SHA-256.
The GitNexus npm group installed 254 packages and the hash-checked LadybugDB
binding loaded successfully in Node. Retry verified the completed receipts.
The staged `agent-tool.ps1` reported Beads 1.3.4, Worktrunk 0.81.0 and Marimo
0.25.2 through their relocated paths. The browser controller generated its
config with the pinned Chromium path. A selective `setup.ps1 -Apply` installed
both patched wheel groups and the Semgrep and PDF venvs with the two exact
Python versions. A second run verified all four receipts. Semgrep's venv
reported pip 26.3 and Semgrep 1.183.0+local.security1. These checks cover the
tested groups, reconstruction and version output, with live browsing,
account-dependent workflows and GitNexus FTS outside the smoke-test scope.
