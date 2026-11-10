# What is copied, adapted, and provided as a reference

| Content | Relationship to the working setup |
| --- | --- |
| `environment/bundle/` | Full reviewed user-environment export. Includes 62 user Skills, role settings, controllers and harness source with explicit privacy/path adaptations |
| `environment/manifest.json` | Integrity hashes for the public payload bytes and declared destination paths |
| `environment/dependencies.json` | Fixed upstream artifacts and package recipes. Large model assets download only during explicit installation |
| `environment/portability.json` | Per-Skill provenance, license classification and recorded export adaptations. A reference commit is a source/rights verification point, not a claim about the original installation commit |
| `setup.ps1`, `reproduce.py`, `install_dependencies.py` | New isolated staging, dependency restoration and verification entry points |
| `templates/global-AGENTS.md` | Complete standing agreements. Audited against the source file, byte-identical after privacy review |
| `config/config.sanitized.toml` and profiles | Actual saved configuration structure and safe values. Account identifiers, machine paths and trust roots use explicit replacements in the redaction manifest |
| `config/agents/` | Recorded role files |
| `config/agents-current-schema/` | Compatibility adaptation for current documented role fields. Original and adapted forms remain separately inspectable |
| `skills/` | Six portable rewrites retained for the smaller project starter |
| Skill catalog | Inventory and provenance of installed skill files. Full third-party skill libraries are acquired from their respective sources and licenses |
| `config/tooling/harness/` | Seven-route core source, tests and synthetic fixtures. Additional full-environment controllers are in `environment/bundle/codex-home/` |
| `config/tooling/workflow-tool.ps1` | Runnable entry to the seven bundled core routes |
| `config/tooling/agent-tool.reference.ps1` | Broader launcher reference, including third-party tools with separate installation requirements |
| Tool manifests and locks | Versions and dependency declarations for separately installed software |
| Diagrams and writing | New explanations authored for this publication using inspected configuration and workflow evidence |

No repository history, account state or live credentials are required to try the project-level workflow. Use your own paths, account connections and project scope when applying the setup.

中文解释见 [设置说明](docs/settings.md) 和 [工作方法](docs/workflows.md)。文件名称中的 snapshot、sanitized、reference 和 current-schema 表示各自的来源与使用方式，迁移时按说明选择。
