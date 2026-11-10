# Semgrep CE Windows 隔离安装与本地数据流验收

日期：2026-11-05。只使用自写 Python fixture 和 YAML 规则，无真实用户仓库扫描、Registry 规则、账户、Pro、MCP server 或全局配置修改。

## 决策与入口

- 默认入口：`{{CODEX_HOME}}\tools\semgrep\run-semgrep.ps1`。它调用 `candidate\semgrep-local.py` 与 `candidate\venv\Scripts\python.exe`。
- 候选发行标识：`1.183.0+local.security1`；Semgrep CLI/core 自报 `1.183.0`。仅 wheel 的 METADATA/RECORD 发生改变，CE 可执行代码未改。
- 保留官方原版在 `venv\`、`requirements.lock`、`dependency-audit.json`、`wheelhouse\`，作为对照；不要绕过受限入口将其用于默认工作流。
- PowerShell 示例：`& '{{CODEX_HOME}}\tools\semgrep\run-semgrep.ps1' -Config '<absolute-local-rule.yml>' -Target '<absolute-local-target>' -ErrorOnFindings`。

入口强制 CE `--oss-only --metrics=off --disable-version-check --no-autofix --strict --json`，仅接受指定本地 YAML 与本地目标，清除继承 SEMGREP_/OTEL_ 环境变量、隔离 settings/log；不转发任意 CLI 参数。拒绝原始 UNC/device 路径后才 resolve。此为受限调用约定，不是 OS 网络沙箱；没有抓包证明完全零网络。

## 来源、锁与兼容性修复

- 官方 repository：https://github.com/semgrep/semgrep 。当日 GitHub 元数据在 `repository-source.json`，星数只用于工具发现。
- 官方 PyPI：https://pypi.org/pypi/semgrep/1.183.0/json 。Windows wheel SHA256 `8e9d96b976d6cb8e1240d454e50245decd52d1329d84540df26c7f06787439f7`；许可证元数据为 LGPL-2.1-or-later；Python >=3.10。本机使用 Python 3.13。
- 原版固定 `mcp==1.29.0` 与 OpenTelemetry 1.37/0.58 系列。精确版本 PyPI advisory 查询发现 mcp 四条，opentelemetry-api 一条；bootstrap pip25.2 也有已知 advisory。原始结果保留 `dependency-audit.initial.json`；pip 已仅在隔离 env 升到26.3。
- 派生候选改为 mcp1.30.0、Otel API/SDK/HTTP exporter1.45.2、instrumentation0.66b2。候选完整依赖闭包为67包，加pip共68项，PyPI exact-version advisory检查零已报告条目、零查询错误；`pip check`通过。此结论只覆盖当日已知 advisory，不是安全或全功能兼容证明。
- 派生清单：`derived\derivation.json`；候选锁、下载来源/哈希、许可证和审计分别在 `candidate\requirements.lock`、`candidate\install-report.json`、`candidate\inventory.json`、`candidate\dependency-audit.json`。67个候选wheel全部经 `pip download --require-hashes` 校验并缓存。pip单独固定在 `bootstrap.lock`。

官方原版依赖 advisory IDs：GHSA-84m7-p3x7-pcfv、GHSA-5h93-6whr-6q8j、GHSA-w4fh-qvv9-3v23、GHSA-rwrf-2pqf-9j8j、GHSA-xcq7-p3pf-p88h。对应 MCP 服务/HTTP transport、tracestate header 路径不在本次启用范围；仍修复依赖，未依赖“不使用”代替修复。

## 同一任务的实际测试

`fixture.py` 的5行通过 raw→first→second 两次赋值到sink；30行是直接sink(source())。11行经自写规则声明的sanitize处理，16/17行是无关sink/固定字符串；21/26行为跨函数边界。

| 检查 | 官方原版 | 派生候选 |
|---|---|---|
| 自写 taint 规则，仅报告5/30行 | PASS | PASS |
| sanitizer、无关sink、固定字符串负例不报 | PASS | PASS |
| helper跨函数未报告（记录CE边界） | 观察到 | 观察到 |
| 默认有发现 exit0，`--error` exit1 | PASS | PASS |
| 无效Python规则 JSON errors + exit2 | PASS | PASS |
| source SHA256 前后不变 | PASS | PASS |
| 禁远程config、Pro、autofix | PASS | PASS |
| UNC在resolve与subprocess前拒绝 | PASS | PASS |
| pip check | PASS | PASS |

已有 ast-grep 的直接结构模式 `sink(source())` 在同一个fixture只报告30行。此对比证明当前自写taint规则能覆盖这个赋值传播样例，而直接结构模式不能；不代表ast-grep所有复杂规则都无法表达此情况，也不代表安全检出率基准。

初次 `pattern-sanitizers exact:true` 在这个样例仍报告11行；改为显式 `exact:false` 后负例通过。初次 `scan.json` 与 `sanitizer-nonexact.json` 保留。正式示例采用已测试配置，不把小型诊断推导为一般引擎缺陷。

机器结果：原版 `results.json`；派生候选 `candidate-results\results.json`。源文件SHA256：`ace5d2b67d92f72119db7e3b3c7799b967ceeea7436c74373cb080c81600ddd4`。

## 独立审查与工作流建议

独立 reviewer 找到“UNC resolve 早于拒绝”缺陷，已修复，并独立运行8个mock测试覆盖config/target的UNC、extended UNC、device path和forward slash；全部在resolve/subprocess前拒绝。独立比对181个wheel entries：除规范化dist-info目录后的METADATA/RECORD外无内容差异，全部RECORD hash/size和两个archive hash一致。候选本地scan结果已检查。

建议在已有 `rg / ast-grep定位 → 人工确认source/sink/sanitizer → 本地自写taint规则 → 候选CE扫描 → 源到汇证据复核 → focused安全审查` 里按需调用。source/sink规则必须由真实代码语义决定，不能把demo规则直接用作安全门。跨函数/文件流程应继续人工跟踪或用现有调用图工具；不计入Pro能力。无发现不能证明无漏洞。

验收范围已满足本地CE数据流补充工具用途。MCP、追踪、远程规则、真实repo和更广语言/功能兼容均未测试或未启用；派生依赖版本需显式维护，不冒充官方发行。

## Python 启动隔离补充

PowerShell 默认入口以 Python `-I` 启动本地 wrapper；wrapper 在启动 Semgrep 子进程前移除 `PYTHONPATH/PYTHONHOME/PYTHONSTARTUP/PYTHONUSERBASE`，并设 `PYTHONNOUSERSITE=1`。直接绕过 PowerShell 调用 wrapper 的使用者必须同样使用 `python -I`，因为 wrapper 尚未执行时无法阻止 Python 启动钩子。

受控 `sitecustomize.py` 哨兵在普通 Python 对照中确实写出标记；通过正式入口、同时注入该 PYTHONPATH 和无效 PYTHONHOME 时，扫描仍完成且未加载哨兵，结果保持5/30行、exit1、源码哈希不变。额外检查实际构造的子进程环境确认上述4变量全被清除。结果在 `python-isolation-results.json`，只重跑这项隔离检查和一次现成fixture扫描，未重复依赖审计或整套已通过测试。

参考官方语义：https://docs.semgrep.dev/writing-rules/data-flow/taint-mode/overview 。本机 `scan-help.txt` 和已安装 `commands/scan.py` 用于核对真实参数与默认值。
