# Verification / 验证记录

Checked on 2026-11-10 with Windows, Python 3.14 and the locally installed Codex CLI 0.157.1. The documented Python source minimum is 3.11.

| Check | Observed result |
| --- | --- |
| Core harness unit tests | 134 tests, 132 passed and 2 skipped symlink cases. Details in [tooling summary](config/tooling/verification.json) |
| Synthetic grader calibration | Eight tasks with good, bad, alternative, and scope-violating outputs |
| Project bootstrap | Five regression tests passed |
| Fresh-profile discovery | Installed 11 files in an isolated temporary project. All six portable Skill names appeared in CLI debug input. Model generation was not invoked |
| Preservation | Dry run left the target absent. A second apply rejected an existing directory. Installed AGENTS bytes matched the full source template |
| Command routing | Seven help entries and multiple-argument forwarding checked; the single-argument forwarding defect was fixed |
| Format and navigation | TOML/JSON parsing and local Markdown target checks passed |
| Independent review | Reviewed portability, privacy, command routing, documentation and representative diagrams; confirmed reported fixes |

The native-eval bridge rejects linked/reparse-point paths. Its test run used a resolved ordinary directory. The package contains a full configuration inventory and a runnable seven-tool core. Third-party binaries, model access, account connectors, custom local wheels and several experimental controllers require their own setup. See the configuration guide for each boundary.

运行测试时产生的 coverage、verification、运行日志和 bytecode 只留在本地。仓库忽略生成的评测目录，发布包按文件清单筛选。真实模型调用、带账号的 MCP、云端执行和实际小红书预览都需要在对应环境验证。

The synthetic tests establish utility and checker behavior. They do not measure whether these instructions improve model quality across tasks. The [comparison protocol](templates/comparison-protocol.md) and [evolution guide](docs/evolution.en.md) describe how to investigate that question.
