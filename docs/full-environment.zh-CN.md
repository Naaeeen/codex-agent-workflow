# 完整环境复现指南

[English](full-environment.en.md)

这份包把可公开的设置、62 个用户 Skills、四类角色、工具控制器、harness 和依赖配方放到一个独立目录。参考依赖环境为 Windows x64。配置与源文件通过清单校验，第三方依赖从指定版本下载，安装过程保存各组的校验记录。

## 先准备

1. 完整备份项目和现有 Agent 配置，备份保存在仓库外，确认能恢复。
2. 准备 Git、PowerShell 7 和可运行 Python 的环境。完整依赖使用官方 Windows x64 [Python 3.13.7](https://www.python.org/downloads/release/python-3137/) 与 [Python 3.14.3](https://www.python.org/downloads/release/python-3143/)。
3. 两个本地补丁 wheel 要重现原始压缩字节。Serena 配方要求 Python 3.14.3、zlib `1.3.1.zlib-ng`，Semgrep 要求 Python 3.13.7、zlib `1.3.1`。预检不符时会停止，保留错误以便核对对应解释器。
4. 选择一个已有父目录下的新目录，放在 Git 仓库外。原配置继续保留。

查看解释器版本时可以运行以下命令。模型文件合计约 3 GB，完整程序和 Python/npm 依赖还需要额外空间。

若 `py -3.13` 或 `py -3.14` 选中了其他补丁版本，直接把所需版本的 `python.exe` 完整路径传给 `-Python313` 或 `-Python314`。预检会确认版本后才执行安装。

```powershell
py -3.13 -c "import sys,zlib; print(sys.version.split()[0], zlib.ZLIB_RUNTIME_VERSION)"
py -3.14 -c "import sys,zlib; print(sys.version.split()[0], zlib.ZLIB_RUNTIME_VERSION)"
```

## 分三步完成

首页命令通过 `setup.ps1` 执行以下步骤。

- **预览与写入。** `reproduce.py` 核对文件和路径，替换指定占位符，建立独立的 `codex-home`、初始项目和 `launch.py`。默认只预览，明确执行后才写入。
- **恢复依赖。** `install_dependencies.py` 按依赖顺序处理选定组。先验下载哈希，再解包；npm 禁用安装生命周期脚本；Python 包进入对应的独立 venv。经过检查的 GitNexus 原生模块复制、两个 wheel 的重建有单独规则。
- **接入自己的账号和宿主。** 使用独立入口登录，按下表完成自己的客户端、插件及项目参数。

要先安装一部分，可以选择组名，前置依赖会一并列入。

```powershell
$py313 = py -3.13 -c "import sys; print(sys.executable)"
$py314 = py -3.14 -c "import sys; print(sys.executable)"

# 预览 Codex、基础 CLI 与核心 Python 运行时
pwsh -NoProfile -File ./setup.ps1 -Destination ../my-codex-environment `
  -Group codex-cli,npm-agent-kit,python-harness-python

# 执行所选组，或者移除 -Group 以安装全部自动组
pwsh -NoProfile -File ./setup.ps1 -Destination ../my-codex-environment `
  -Python313 $py313 -Python314 $py314 `
  -Group codex-cli,npm-agent-kit,python-harness-python -Apply
```

`-SkipModelWeights` 仅暂缓 `qmd-models` 和 `docling-models`。需要这些能力时再选择对应组执行。所有组名和固定版本见[依赖清单](../environment/dependencies.json)。

## 哪些内容怎样恢复

| 内容 | 处理方式 |
| --- | --- |
| 模型、推理强度、搜索和权限默认值 | 从可迁移配置恢复。当前会话或宿主可以覆盖默认值，所选模型须在自己的账号可用 |
| 62 个用户 Skills | 安装在新 `CODEX_HOME/skills`，包括本地适配和许可。选定模板用路径占位符迁移 |
| 系统 Skills 与 17 项宿主插件记录 | 用自己的官方客户端及插件目录重新安装。参考[宿主配置](../environment/bundle/tooling/host-settings.reference.json)，由客户端生成其运行桥接和缓存 |
| 公共文档 MCP | 配置包含 Context7、OpenAI Docs、Microsoft Learn。启动后确认工具可见并做一次公开文档查询 |
| Serena MCP | 安装其固定依赖后使用目标目录的程序与配置，保留导航工具范围 |
| Supabase、Exa 和其他带账号服务 | 使用自己的项目参数和账号。未填写的服务保持禁用，按自己的用途再启用 |
| 浏览器 | 隔离自动化使用固定 Chromium。要操作自己的已登录标签页，通过自己的客户端浏览器连接 |
| 已记录但关闭的 STDIO MCP | 旧 Playwright、GitHub、memory、sequential-thinking 条目保持关闭。部分使用 `bunx`，仅在选择启用时另装 Bun 并核对对应服务。已复现的 Playwright CLI 与 Chromium 是另一条入口 |
| Git hooks | 提供脚本和许可。需要启用时，在具体仓库检查已有 hooks，再设置项目级 `core.hooksPath`，保留原配置以便恢复 |
| 历史批准命令、项目目录、聊天与记忆内容 | 由读者在自己的机器重新形成。私人原文和指纹不在复现包里 |
| 云端环境 | 使用自己的仓库、执行环境、权限和预算配置。交接工具负责打包与核对，实际派工需要可用的远端环境 |

原机 24 个顶层设置类别的去向记录在[覆盖清单](../environment/bundle/tooling/settings-coverage.json)。完整[脱敏快照](../config/config.sanitized.toml)供对照，运行用配置在安装后的 `codex-home/config.toml`。

## 在桌面客户端沿用这套环境

独立入口适合先验证和保留恢复点。希望自己的桌面客户端长期沿用时，可以把本指南交给桌面里的 Codex，让它按以下清单迁移。

1. 备份自己的配置文件、用户 Skills、角色和相关 hooks，记录各文件原先存在与否。备份留在仓库外。
2. 对照已生成的 `codex-home`，将选定 Skills、工作约定与角色合入自己的用户目录。已有同名文件先比较并保留副本。
3. 合并实际要使用的模型、搜索、权限和工具设置。工具程序可以继续位于独立安装目录，使用已经渲染的路径。桌面启动 MCP 时，将对应 venv Scripts 和固定 Node 目录加入该连接的子进程 PATH，并接上你自己的 PATH。保留自己账号的服务参数、项目授权和登录配置。
4. 从官方插件目录安装对应插件，按自己的账号连接。`node_repl`、浏览器信任值、通知程序和本机通信管道等使用自己客户端生成的版本。参考快照里的占位符只供对照。根据宿主设置参考逐项设置桌面偏好。
5. 重新加载客户端，在新会话确认 Skills、角色和 MCP，实际跑一项小任务。记录哪些字段成功应用，哪些因客户端版本不同需要调整，以及各自恢复方式。

安装器负责独立目录，桌面合并由读者在自己环境中明确执行。私有聊天、记忆、索引和许可历史继续使用自己的数据。

## 和原机相比的明确调整

- 个人路径改成安装目标或用户填写的项目位置。
- 四份角色使用兼容 schema，角色指令保留。权限仍由父会话和运行环境控制。
- 四个 Python 工具的 venv 放入独立子目录，Beads/Worktrunk 程序放到 `bin`，入口同步迁移。
- 旧版受限 `docx` 替换为固定提交的官方 Apache 版本。可选论文 PDF 改成上游链接。
- 私人登录、令牌、运行缓存、索引、数据和原机授权命令均由目标环境自行产生。

来源与逐文件改动见[移植记录](../environment/portability.json)和[第三方许可](../THIRD_PARTY_NOTICES.md)。

## 使用与验收

```powershell
$py313 = py -3.13 -c "import sys; print(sys.executable)"
& $py313 ../my-codex-environment/launch.py -- login
& $py313 ../my-codex-environment/launch.py -- --version
& $py313 ../my-codex-environment/launch.py --project C:/path/to/my-project
```

入口优先使用明确指定的 Codex 或已经安装并通过校验的固定 CLI。新环境单独保存登录，系统账户和操作系统权限仍属于当前读者。它是独立配置环境，运行文件权限由操作系统及 Codex 控制。

先做一个小任务，检查 Skill 是否被发现、所需工具能否运行、MCP 是否可用、产物是否符合要求。按任务需要选择测试和独立复核，留下结果与下一步。运行证据见[复现验证](reproduction-verification.md)。

已安装的固定 Node 会加入 Codex 子进程的 PATH，供工具调用。需要使用项目自己的 Node 时，在 `launch.py` 后加 `--inherit-node-path`，再按项目的运行时管理方式启动。

## 重试、个性化与恢复

中途失败时保留错误。已完成的依赖组通过记录校验后可复用，存在但不完整或被改过的目录会被拒绝覆盖。先查差异和是否有运行中的进程，再处理自己新建的失败目录。

建议先完成所需依赖，再修改个人配置。安装校验以发布版本为依据，后续有意编辑过的受管文件会被识别为差异。升级时可在另一个新目录复现，再合并自己的修改，保留当前可用版本。

恢复时切回原来的 Codex 入口和配置。手动接入过的插件或项目设置，按自己的备份恢复。原环境与备份不要一起删，也不要把包含密钥、账号或运行记录的目录提交到公开仓库。
