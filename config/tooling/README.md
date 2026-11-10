# 可运行源码与本机工具清单

本页保留便携七入口的独立用法。完整环境的 31 路由、原控制器与固定依赖现已在[完整导出](../../environment/bundle/codex-home/tools/)提供，安装说明见[完整复现指南](../../docs/full-environment.zh-CN.md)。

先从 `workflow-tool.ps1 --help` 开始。这个入口只路由随包提供实现的七项：task、improvement-verify、eval、observe、eval-native、handoff、execution-plan。Python 3.11+ 必需；eval 中的 JS/PowerShell 检查还需相应运行时。源码与合成测试在 `harness/`，不读取原用户的聊天历史或账户状态。

`observe` 与显式执行的 `eval-native` 会运行调用者指定的 CLI，可能消耗额度；`--help`、本包的单元测试及合成 grader 检查不需要模型服务。本次 observer 测试使用 fake CLI，没有新开真实模型会话。

Windows 上请用普通物理目录。源码的安全文件读取会拒绝 symlink/junction；如果从目录快捷入口进入，先转到该目录实际指向的文件夹运行。不要删除这些检查来让测试变绿。

## 在包内验证

从本目录运行：

```powershell
pwsh -NoProfile -File ./workflow-tool.ps1 --help
python -B -m unittest discover -s ./harness -p 'test_*.py'
python -B -m unittest discover -s ./harness/evals -p 'test_*.py'
python -B -m unittest discover -s ./harness/native-observer -p 'test_*.py'
python -B -m unittest discover -s ./harness/native-eval-bridge -p 'test_*.py'
python -B -m unittest discover -s ./harness/portable-handoff -p 'test_*.py'
python -B ./harness/evals/verify.py
```

这五套单元测试合计 134 项。发布制作时 134 项结束、2 项跳过；跳过项不能算验证通过的能力。完整性、负例与预期拒绝行为应一起看；这些测试不证明模型输出质量。

## 原工具目录如何对应

`agent-tool.reference.ps1` 是原始中央入口。它从自身目录计算 `.codex/tools` 与 `.codex/harness`，并依赖固定 Node/Python、多个本机 venv、第三方 binary、模型文件和专用 wrapper。它保留作来源，不是即装即用脚本。

| 原入口 | 本包中的复现材料 / 尚需依赖 |
| --- | --- |
| task / improvement-verify / eval / observe / eval-native / handoff / execution-plan | 已提供源码；用新的 workflow-tool.ps1 |
| rea / repomix / ast-grep | `npm/agent-kit` 的 package.json、package-lock.json；需要兼容的 Node；ast-grep 是 Windows x64 包 |
| browser | 完整导出包含控制器；浏览器和 npm 包由固定依赖组恢复 |
| pi-lab | 完整导出包含离线试验控制器及输出检查；npm 包单独安装 |
| gitnexus / qmd / mcp-inspector | 对应 npm 锁文件、已有可公开 wrappers；QMD 的本地模型和索引不随包提供 |
| serena | Python 锁、context/mode、固定上游与补丁重建配方；输出哈希经过核对 |
| docling / marimo / inspect | `manifests/*requirements-lock.txt`；隔离 Python 环境、模型和可选系统依赖自行准备 |
| pdf-layout | 完整导出提供 layout_extract.py 和固定 Python 依赖 |
| beads / worktrunk / mise / pixi | 清单给上游来源与版本；部分原 wrappers 已提供；需按自己的系统安装对应发行版 |
| duckdb / hyperfine / typos / lychee / trafilatura | 清单给固定版本；需单独安装；不要从原 launcher 的个人目录寻找可执行文件 |
| semgrep | 完整导出提供包装器、锁与补丁重建配方，保留精确输出哈希检查 |
| audit | 完整导出提供 env_audit.py 与测试；生成的本机报告按私有文件处理 |

六套 npm 项目都保存了**实际依赖与锁文件**，不是只给一个 latest 安装命令。要试某套依赖，先复制对应 `npm/<tool>/` 到单独目录，再检查其用途、平台、来源与许可后安装。例：

```powershell
# 在单独的 agent-kit 目录里，先阅读 package.json 与 package-lock.json。
npm ci --ignore-scripts --no-fund
```

命令只是复建依赖的起点，不会创建所有原 launcher 所需目录。`--ignore-scripts` 会跳过依赖生命周期脚本；某些平台或原生依赖因此需要进一步、明确的安装步骤。这里没有为了让安装成功而自动放开脚本执行。安装后用自己的版本和功能检查确认结果；本次没有重新联网安装这些依赖。

`harness-source-map.json` 列出原文件别名、公开文件的 SHA-256 与移植修改。私有原件的指纹已省略。保存源码不意味着附带原作者的运行记录、测量结果或账户可用性。第三方工具遵循各自上游许可；尤其 GitNexus 的清单记录非商业许可，不能被本工作流包的说明覆盖。
