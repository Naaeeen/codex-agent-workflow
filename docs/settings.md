# 我实际使用的 Codex 设置

完整复现现已提供独立安装入口、62 个用户 Skills、原工具控制器和固定依赖配方。先看[完整指南](full-environment.zh-CN.md)。本页仍解释保存的配置与历史记录，运行时路径、宿主连接及隐私替换以新清单为准。

这份说明对应 **2026-11-10 读取的本机文件**。完整配置、角色指令和可运行的本地工作流源码随包提供。个人目录、项目标识、环境变量值、应用生成的本机通信参数用占位符替换。这里只记录配置和已完成的本地检查；安装着某个工具、配置里写着 `enabled = true`，都不等于当前会话调用成功。

## 文件怎么用

| 文件 | 内容与使用方式 |
| --- | --- |
| [config.sanitized.toml](../config/config.sanitized.toml) | 实际全局配置的 24 个顶层键全部保留；用于对照，不能直接覆盖自己的配置 |
| [strict.config.toml](../config/strict.config.toml)、[yolo.config.toml](../config/yolo.config.toml) | 两个实际 profile 文件，内容与本机一致 |
| [agents](../config/agents/) | 四个实际角色 TOML，保留原指令和字段 |
| [agents-current-schema](../config/agents-current-schema/) | 适配当前官方角色 schema 的副本，添加 name/description，去掉不构成子代理权限隔离的 sandbox 声明 |
| [redaction-manifest.json](../config/redaction-manifest.json) | 字段级脱敏位置、配置层数量和类别 |
| [toolkit-inventory.json](../config/tooling/toolkit-inventory.json) | 本地 CLI 版本、来源、用途、启用/保留状态和 31 个原始入口 |
| [workflow-tool.ps1](../config/tooling/workflow-tool.ps1) | 随包提供实现的七个工作流入口；从包内直接运行 |
| [agent-tool.reference.ps1](../config/tooling/agent-tool.reference.ps1) | 实际使用的完整 31 路由 launcher，仅供理解本机目录与调用方式；其第三方依赖未随包打包 |
| [git-hooks](../config/git-hooks/) | 实际 pre-commit、pre-push 源码副本，没有自动安装 |
| [history-inventory.json](../config/rules/history-inventory.json) | 历史许可的排除与恢复说明；仅另附可审查的只读示例 |

先把本包当作一个可读、可试的工作台。通用源码可以在包内验证；账户、App 私有运行时、MCP 登录、项目信任等内容在自己的客户端里配置。

## 基础配置：模型、权限和上下文

| 实际字段和值 | 在这里的含义 | 复用时要判断什么 |
| --- | --- | --- |
| `model = "gpt-6.1-sol"` | 本机全局默认模型 | 必须在自己的账户和客户端中可用；这是快照，不是所有任务的最佳模型结论 |
| `model_reasoning_effort = "max"` | 全局 reasoning effort | 高 effort 不替代来源、测试和验收；任务或会话可能覆盖 |
| `model_context_window = 872000` | 手动声明的上下文窗口数值 | 不会给模型增加实际容量；不要把配置数字当成服务端能力证明 |
| `service_tier = "default"` | 本机保存的服务等级请求 | 未验证此值在各模型/客户端上的最终调度效果，不能称为 Ultra Fast 或保证的速度 |
| `personality = "pragmatic"` | 保存的表达风格偏好 | 不承担正确性或权限控制 |
| `approval_policy = "on-request"` | 配置允许代理在必要时提出审批 | 与沙盒共同决定执行边界 |
| `approvals_reviewer = "auto_review"` | 可适用的审批交由自动审查 | 不代表所有请求都会通过，也不能替代用户对发布等动作的授权 |
| `sandbox_mode = "workspace-write"` | 本机默认工作区写入模式 | 复制前确认自己的执行范围 |
| `sandbox_workspace_write.network_access = true` | 该沙盒模式允许网络访问 | 并不是外发文件或修改外部系统的授权 |
| `windows.sandbox = "elevated"` | Windows 沙盒实现选项 | 不能从名称推断每个命令都以管理员运行；受客户端实现和有效权限约束 |
| `web_search = "live"` | 默认实时搜索 | 仍应实际打开来源并检查日期 |

配置数值与官方字段语义是两种证据。以上数值来自本机文件；字段定义以 [Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference) 和 [Advanced Configuration](https://learn.chatgpt.com/docs/config-file/config-advanced) 为准。

**当前制作会话的有效权限与这份文件不同**：宿主为本会话提供了 full access / `danger-full-access` 与 `approval_policy = never`。这是运行时观察，不能倒推文件已经被改成这样。本次没有修改全局文件，也没有试图把文件权限强加到宿主会话。

## 两个 profile：只覆盖明确写出的字段

`strict.config.toml` 的完整内容是：

```toml
approval_policy = "on-request"
sandbox_mode = "read-only"
web_search = "cached"
```

`yolo.config.toml` 的完整内容是：

```toml
approval_policy = "never"
sandbox_mode = "workspace-write"
web_search = "live"
```

第二个文件虽然叫 yolo，实际仍写着 `workspace-write`，不能描述成无沙盒配置。它没有重新声明 `sandbox_workspace_write.network_access`，与全局层合并时还要检查继承值。两个 profile 都没有指定另一种模型。

在自己的 `CODEX_HOME` 中保存这两个独立文件后，可选择：

```powershell
codex --profile strict
codex --profile yolo
```

这两条命令会启动会话；本次只检查了文件，没有启动新的模型任务。当前官方文档规定先加载全局 `config.toml`，再叠加 `<profile>.config.toml`；Codex 0.134.0 起不再从 `[profiles.name]` 读取 profile，也不再使用顶层 `profile` 选择器。本机 PATH 中实际检查到的是 **codex-cli 0.157.1**，桌面客户端的内嵌执行器可能不同。[Profiles 文档](https://learn.chatgpt.com/docs/config-file/config-advanced#profiles)

## 子代理：完整指令可读，模型选择不会自动省钱

原配置保留 `features.multi_agent = true`、`agents.max_threads = 6`、`agents.max_depth = 1`，以及四个带 `description` 与 `config_file` 的注册项。当前文档将 `agents.max_threads` 视作并发字段的旧别名；宿主可提供不同额度。本次会话公开的并发额度是运行时信息，不能用磁盘的 6 推算当前可用数量。

| 角色 | 原指令要求的主要行为 | 原文件中的其他字段 |
| --- | --- | --- |
| explorer | 按父代理限定的问题探索；不改文件；追踪真实执行路径；给文件、符号、行号和不确定性；禁止远端派工或外部修改 | `sandbox_mode = "read-only"` |
| reviewer | 独立核对需求、最终 diff 和执行路径；优先正确性、安全、回归和缺失测试；每项给触发条件、影响、位置和严重性；没有发现也报告验证缺口 | `sandbox_mode = "read-only"` |
| docs_researcher | 按指定版本查当前一手文档；不安装、不编辑、不改外部状态；区分文档事实、本地观察、推断与未知 | `sandbox_mode = "read-only"` |
| computer_operator | 只处理限定 UI 任务；先读技能与实际 API；保护用户已打开的工作；遵守外部动作授权；完成工具要求的收尾交接 | 只有 `developer_instructions` |

这不是截短后的“角色提示词模板”。四份 [实际文件](../config/agents/) 保留完整英文 `developer_instructions`；表格只是入口。

四份文件都没有 `model` 或 `model_reasoning_effort`。指令写的是“父代理按任务选择当前可用、足够胜任的低成本模型或较低 effort”；这句话本身不会切换模型。父代理是否能指定参数、是否使用全历史 fork、角色文件是否另有覆盖，都要看实际工具。不能把“建立了四个角色”写成“自动把便宜的活分给便宜模型”。

**原文件中的 read-only 声明不等于独立的强制只读沙盒。** 当前官方说明明确：角色文件里的 `sandbox_mode`、`approval_policy`、`model_provider`、`mcp_servers` 不覆盖父代理设置；服务等级跟随根会话。原指令里的“不编辑”是行为要求。需要强制隔离时，应使用实际受控的父会话权限、工作区和工具限制。[Custom agent schema](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agent-file-schema)

当前独立角色文件 schema 要求 `name`、`description`、`developer_instructions`。本机原文件仍采用全局注册项提供描述的结构，不能声称它们在所有新版加载器中都能原样发现。因此同时给出 [current-schema 副本](../config/agents-current-schema/)：保留行为指令，补名字和描述，去掉无效的沙盒暗示；没有擅自固定另一种模型。实际装入哪一套应以本机客户端列出的角色为准。本次没有改用户原角色文件。

## MCP：11 个条目，区分 HTTP、STDIO、禁用与 App 运行时

| 名称 | 传输及磁盘状态 | 配置用途与具体限制 |
| --- | --- | --- |
| supabase | HTTP；未显式写 enabled | URL 带项目范围，项目标识已替换；`execute_sql.approval_mode = "approve"` 原样保留。该字段不是 SQL 只读限制，不能据此承诺只查不改 |
| context7 | HTTP；true | 库文档；启动超时 30 秒；resolve-library-id 输出上限 4000，query-docs 12000 |
| openaiDeveloperDocs | HTTP；true | OpenAI 一手文档；启动 30 秒；search/list/fetch/list-api 输出上限依次 8000/6000/16000/8000 |
| microsoftLearn | HTTP；true | Microsoft 文档和代码示例；启动 30 秒；两个 search 上限 8000、fetch 16000 |
| exa | HTTP；false | 保留但禁用；私人 URL 不公开，也不在复现包中启用 |
| playwright | STDIO：`bunx @playwright/mcp@latest`；false | 启动 30 秒；该原始配置未锁版本，不能称为可重复安装的固定版本 |
| github | STDIO：`npx -y @modelcontextprotocol/server-github`；false | 启动 30 秒；与连接器里的 GitHub 插件是两条接入路径 |
| memory | STDIO：`bunx @modelcontextprotocol/server-memory`；false | 启动 30 秒；与 Codex 自身 memories 开关不同 |
| sequential-thinking | STDIO：`bunx @modelcontextprotocol/server-sequential-thinking`；false | 启动 30 秒；保留配置不代表本任务使用 |
| node_repl | 本机可执行程序 STDIO；未显式写 enabled | App 管理的 Node/浏览器/计算机桥接，启动 120 秒；可执行路径和全部 env 值必须由自己的 App 生成 |
| serena | 本机可执行程序 STDIO；true | 代码符号导航，启动 45 秒、单工具 90 秒；只开放下面列出的 5 个工具 |

Serena 的参数保留了 `--agent-interface tools`、关闭 web dashboard/open dashboard/GUI log window，使用自定义 context 和 mode。开放五个导航工具，对应 [context 与 mode](../config/tooling/serena/) 已提供。角色及工具范围仍受父环境权限控制。完整复现使用固定上游 wheel 和[重建配方](../environment/bundle/tooling/wheels/serena.json)，生成 `serena-agent 2.1.0+codex.1` 并检查原始输出哈希。

公开配置仅保留已在官方来源核对的公共端点：

- Context7：`https://mcp.context7.com/mcp`，[官方仓库](https://github.com/upstash/context7)。
- OpenAI Docs：`https://developers.openai.com/mcp`，[官方配置示例](https://learn.chatgpt.com/docs/agent-configuration/subagents)。
- Microsoft Learn：`https://learn.microsoft.com/api/mcp`，[官方说明](https://learn.microsoft.com/en-us/training/support/mcp)。
- Supabase：`https://mcp.supabase.com/mcp` 加自己的项目参数，[官方配置](https://supabase.com/docs/guides/ai-tools/mcp)。

`enabled` 是配置状态，工具列表是宿主暴露状态，成功调用才是运行证据。本次用 OpenAI Docs 查了配置文档；没有为了“证明齐全”连接全部服务、登录账户或执行数据库查询。

`node_repl.env_vars` 仅保留四个传入变量名：`BROWSER_USE_ACCESS_EXECUTOR_ID`、`BROWSER_USE_ACCESS_PIPE_PATH`、`BROWSER_USE_ACCESS_VERIFYING_IDENTITY`、`CODEX_WINDOWS_REGISTERED_CORE`。其 env 表中 17 个变量名全部保留，值全部占位，覆盖 Node 路径、模块目录、可信代码路径、App 版本、浏览器后端、管道和工具说明开关。`serena.env` 的 `SERENA_HOME` 与 `PATH` 同样保留名称、替换值。不要把别人机器的管道、路径或信任摘要当作可共享配置。

## 插件、记忆、通知和桌面偏好也在快照里

**插件。** `marketplaces` 保留 openai-bundled、openai-primary-runtime 两个本地源条目，路径已占位。`plugins` 中的 17 个 enabled 条目全部保留：documents、spreadsheets、presentations、github、linear、teams、computer-use、google-drive、openai-developers、hugging-face、chrome、pdf、template-creator、visualize、browser、unified-computer-use、codex-app-tools。它们不等于当前会话可用插件全集；当前宿主也可能从其他服务暴露插件。配置存在不证明服务已登录或工具获授权。

**记忆。** `features.memories = true`；`memories.generate_memories = true`、`use_memories = true`、`disable_on_external_context = false`。第三项意味着没有配置“因为使用外部上下文就停止生成记忆”这个过滤条件。这里只公开开关，没有读取或复制记忆内容。记忆帮助接续上下文，不替代核查当前文件和服务状态。[Memories 配置字段](https://learn.chatgpt.com/docs/config-file/config-reference)

**通知。** 原 `notify` 调用 App 内的 `codex-computer-use.exe`，参数为 `turn-ended`、`--previous-notify`、`[]`；仅可执行路径被替换。它是 App 安装关联的通知桥接，不是本文新写的 hook，也不是独立可安装插件。官方 `notify` 是外部通知程序机制；不能用本文占位路径运行。[notify 说明](https://learn.chatgpt.com/docs/config-file/config-advanced#notifications)

**桌面。** 原样保留环境建议、步骤/命令详情、上下文用量显示、插电时远端控制保活、后续输入 `steer`、全局快捷窗口、confetti、外部 agent 导入同步、空 Git branch prefix，以及可显示的 reasoning effort 选项。`selected-avatar-id = stacky`、默认打开工具 `pycharm` 也保留；单个项目的编辑器路径改为占位。它们主要属于 App 界面和交互偏好；本文没有用未公开字段推断稳定的跨版本 API。

**项目和界面状态。** 私有项目清单与分项目编辑器偏好已移除，对应字段保留空结构。读者在自己的客户端逐个信任所需项目。`notice.fast_default_opt_out`、`tui.screen_reader_detection_done`、`tui.model_availability_nux` 也保留，用于说明原配置完整性；这些状态不是开展工作流所必需的指令。

**浏览器/计算机权限。** `computer_use.windows.always_allowed_app_ids` 原样记录 Edge、PowerPoint、Codex、Word、Explorer 五个 App 标识的 true 值。`shell_environment_policy.set.NODE_REPL_TRUSTED_BROWSER_CLIENT_SHA256S` 的值已替换。前者是本机 App 设置，后者是信任摘要；不能代替用户对具体操作的授权。包内不安装这些允许项、不关闭自己的保护。

## CLI 工具层：版本和用途都交代清楚

工具集中在自己的隔离 tools 目录，通过一个 PowerShell launcher 选择固定入口；没有把“安装了很多 CLI”当成每个任务都要用一遍。原 launcher 源码展示了如何传参数、暂存/恢复进程环境、给 Docling 设模型目录及关闭隐式 token/telemetry、给 Serena 设置专用状态目录、用固定 Python/Node 调用实现。

| 工作 | 实际工具与记录版本 | 使用边界 |
| --- | --- | --- |
| 文本/结构检索 | ast-grep 0.51.1、Repomix 1.18.1、Serena 2.1.0+codex.1 | 普通搜索先用 rg；结构导航或限定上下文包确有帮助时再调用 |
| 已发布包检查 | REA 6.8.0 | 面向发布包、二进制、Electron 等；不替代普通源码阅读 |
| 项目依赖与隔离 | Beads 1.3.4、Worktrunk 0.81.0 | 前者任务依赖、后者 worktree；采用项目已有 tracker 时不另建一套 |
| 代码图 | GitNexus 1.6.12 | 本地 graph-only；安装记录注明非商业许可范围；不能把索引当成真实调用的最终证据 |
| 本地知识检索 | QMD 2.8.3 | 只索引明确选定资料；不自动扫描 home、记忆或私人目录 |
| 项目运行环境 | mise 2026.11.1、pixi 0.84.1 | 优先项目已有清单；不是强制替换 npm、uv 等 |
| MCP 诊断 | MCP Inspector 2.14.0 | 受控 CLI 调试；不因为有诊断工具就上传状态或凭证 |
| 静态规则检查 | Semgrep 1.183.0+local.security1 | 本地 CE 规则；这是本地修订版，没有声称等价于官方未修订发行版或完整安全审计 |
| 文档解析 | Docling 2.147.0；pdf-layout 的 pdfplumber 0.11.9 | 复杂结构提取；普通文本/PDF 工具够用时不用增加模型依赖 |
| Notebook / eval | marimo 0.25.2、Inspect AI 0.3.287 | 分别用于明确需要的交互 notebook 与评测；不是普通任务的默认入口 |
| SQL/时间/文本检查 | DuckDB 2.0.0、Hyperfine 2.0.0、Typos 1.52.0、Lychee 0.24.2 | 针对已选数据、可重复计时、拼写和链接；结果仍需按任务解释 |
| 网页正文提取 | Trafilatura 2.3.1 | 获取并解析已选页面，不代替来源核对 |
| 隔离浏览器 CLI | Playwright CLI 0.1.23；agent-browser 0.41.2 | 独立浏览器实验；已有登录态优先宿主 CUA，两个方式不混称一种验证 |
| agent 实验 | pi-coding-agent 1.5.0 | 本地离线/faux-provider 实验，不宣称替换当前聊天模型 |
| 明确保留但排除 | CodeGraphContext 0.6.13 | 原清单记载 alias edge 与 repo 边界问题；不在中央 launcher/MCP 默认路径里 |

版本证据来自安装清单、package.json 或 requirements lock，**没有在本次重新下载、安装、调用全部工具或做新的依赖漏洞扫描**。`toolkit-inventory.json` 保留上游来源和本地排除原因；`tooling/manifests` 给出 npm 精确依赖/overrides 与五份 Python 锁文件。agent-kit 的 overrides 包括 zod 4.6.7、minimatch 11.0.4、glob 14.0.3；QMD 也有自己的 MCP、Git 和 Zod overrides。复建时不能丢掉 overrides 再声称同一个依赖树。

这些 manifest 是安装输入和观察记录；六套 npm 项目还在 [tooling/npm](../config/tooling/npm/) 提供配对的实际 package.json 与 package-lock.json。包里没有二进制、模型权重、第三方 node_modules 或虚拟环境。Serena 本地 wheel 和 Semgrep 本地修改需要另行审核重建；相关路径明确占位。历史工具清单的云环境说明仅是旧安装记录，不是今天的远端 readiness 检查。

## 随包可运行的七个工作流入口

这一层提供实际源码和测试，不要求读者复制个人 tools 目录。需要 Python 3.11+；本次测试用 Python 3.14.3。eval 的部分合成检查还需要 Node 和 PowerShell。先在真正的普通目录解压；文件完整性检查会拒绝某些 junction/symlink 路径。

从 `workflow-kit` 目录运行：

```powershell
pwsh -NoProfile -File config/tooling/workflow-tool.ps1 --help
pwsh -NoProfile -File config/tooling/workflow-tool.ps1 task --help
pwsh -NoProfile -File config/tooling/workflow-tool.ps1 eval selftest
python -B config/tooling/harness/evals/verify.py
```

| 入口 | 随包实现与作用 | 明确的限制 |
| --- | --- | --- |
| task | objective、workspace、checks、证据文件 hash、revision、checkpoint 与 complete gate | 记录 pass 不证明报告诚实或 review 独立；complete 会重新检查证据 |
| improvement-verify | 检查改进包的比较条件、主张、证据和限制结构 | 结构通过不等于改进有效 |
| eval | 8 个固定合成任务；prepare、grade-existing、selftest | 控制器不调用模型；PASS 只对应具体确定性检查 |
| observe | 有界观察显式给定的原生 CLI，保存筛选后的执行元数据 | 真正执行会消耗该 CLI 的资源；不能默认当作离线自测 |
| eval-native | 连接合成任务、observer 与 artifact grader；默认需要明确执行选项 | 不把 CLI、desktop、native-agent 样本混成一个效果数字 |
| handoff | 为明确选定文件生成受限、可校验的交接包 | 不做远端执行，不保证识别所有秘密 |
| execution-plan | 根据任务和能力 JSON 建议 local/cloud/hybrid | 建议不是授权，也不实际派发任务 |

八个合成任务是 Python interval repair、JavaScript API migration、Windows manifest copying、offline HTML briefing、source-backed document revision、chain-rule teaching feedback、bounded research synthesis、minimal-edit negative control。每个任务都附原始 fixture、prompt、grader 和 golden。先运行自测，再准备某个 case，才能比较两个设置。不能把一次合成 PASS 写成整套 setup 提高所有真实任务质量。

核心实现见 [harness](../config/tooling/harness/)。`native_eval.py` 的本地绝对安装依赖被改成包内相邻 `evals`；脱敏测试用的 UUID 仍保留大小写拒绝测试。所有移植位置在 [source map](../config/tooling/harness-source-map.json) 中列明。新 `workflow-tool.ps1` 只列出随包可用入口；原 31 个入口的 reference launcher 需要恢复它所指向的第三方安装和脚本，不能单独复制运行。

## Git hooks 和 Codex 命令规则是两层机制

本机 Git 全局 `core.hooksPath` 指向一个目录，其中存在 `pre-commit` 和 `pre-push`。包内保留两份实际脚本；没有修改读者或作者的 hooksPath。

`pre-commit` 用 NUL 分隔的 staged 文件列表，只扫描新增文本行，识别若干高信号 token、private key block 和 credential assignment。它不打印命中内容；读取 diff、rg/PCRE2 执行异常会失败。它跳过图片、压缩文件、PDF 和锁文件等类型，所以绝不能声称“所有秘密都扫过”。源码也保留了原来的跳过变量/标记，这意味着它不是不可绕过的组织策略。

`pre-push` 识别 packageManager 或 lockfile，依次运行实际存在的 lint、typecheck、test、build；test 设 CI=true。依赖 audit 只有 `ECC_PREPUSH_AUDIT=1` 时才执行。Go 项目在 go 可用时跑 go test；Python 项目在 pytest 可用时跑 pytest，否则显示跳过。纯分支删除会跳过。没有找到检查时不会凭空制造成功测试。

历史命令许可属于原机私有状态。公开包只说明恢复方式，并提供单独标明的只读规则示例；实际许可由读者根据自己的项目重新建立。

本次在选定位置没有发现全局 `hooks.json` 或 inline `[hooks]`。`notify`、Git hooks、Codex rules、插件可能提供的 lifecycle hooks 互不等同；这个结论不覆盖未审计的插件内部 hook。官方当前有独立的 [Hooks 机制](https://learn.chatgpt.com/docs/hooks)，本文没有把旧 Git hooks 重新命名成这个功能。

## 复建与验证顺序

1. 在自己的普通工作目录解压包，先跑随包 help 与 synthetic tests，确认 Python、Node、PowerShell 可用。
2. 对照全局配置，选择要保留的模型、网络、审批和沙盒设置。备份自己的原文件后逐段合并；不要整份覆盖，也不要把占位路径当变量展开语法。
3. 根据自己的客户端版本选择角色格式；用客户端实际列出的角色检查加载。验证真实行为和权限，不以 description 里的 read-only 判断隔离。
4. 按任务需要安装固定版本工具；保留来源、lock、override 和安装后的检查。需要本地补丁版本的工具，在拿到补丁前保持未复现状态。
5. MCP 使用自己的官方配置、项目范围和登录。App 私有运行时让自己的 App 建立。先检查工具列表，再用有明确范围的只读任务验证。
6. 选择一个真实任务跑完：输入、产物、检查、独立 review、剩余缺口。想比较设置时固定任务和验收，只改一个重要因素；不要把这份安装说明当作性能评测。

完整配置已做 TOML 结构解析和字段覆盖核对。随包核心源码完成 134 项单元测试：132 项通过，2 项因当前 Windows 无法创建符号链接而跳过，另有 junction 检查实际运行。8 个合成 case、每个 4 个校准变体的验证完成；runner/grader 可执行行覆盖率分别为 91.4%/92.3%，不是分支覆盖率。新 PowerShell 入口验证了 help、带空格参数的 task 初始化及未知命令拒绝。[验证记录](../config/tooling/verification.json)

首次从目录 junction 别名运行时，bridge 正确拒绝了 reparse 路径；改从真实物理目录运行后通过，没有放宽 guard。脱敏测试 UUID 的首次替换曾消除大小写负例，修正为含小写字母的合成 UUID 后，25 项 observer 测试通过。模型效果、所有 MCP 的连接状态、每个第三方 CLI 的功能、云端执行、真实人类 A/B 结果均不属于这次配置快照已经证明的内容。
