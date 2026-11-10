# Skills 实装目录与公开复用集

完整环境现在提供 [62 个用户 Skills](../environment/bundle/codex-home/skills/)，来源、许可和隐私适配见[逐项记录](../environment/portability.json)与[许可说明](../THIRD_PARTY_NOTICES.md)。下面的原目录盘点保留了源环境的分类，六项便携改写属于轻量项目入口。系统 Skills 由目标客户端提供。

盘点日期：2026-11-10。依据是两个用户 Skill 根目录的实际 `SKILL.md` 与客户端 `.system` 子目录；只读取元数据和本次相关正文，不读取认证、会话数据库、私人聊天或 memory。插件缓存不在这个文件系统统计内，本次会话另外提供的插件 Skills 也不等于这里安装的用户 Skills。

A = 用户 `.agents/skills`；C = 用户 `.codex/skills`；S = 后者的 `.system`。路径已替换为相对别名。
本次实际存在：A **46** 项，C **16** 项，S **5** 项，共 **67** 项。

“正文已读”仅指这次公开包审计读过该说明；“元数据盘点”仅确认文件存在与路由描述。二者都不证明历史任务调用或执行成功。当前宿主是否暴露某项能力，还须查会话 catalog；例如系统目录里存在 `review-agent`，不能据此声称当前会话可调用一个同名角色。

## 公开包里的六个可复用 Skills

这些是轻量项目入口的原创便携说明，保留工作方法的语义。全局快照里的 `evidence-driven-work` 名称在此保留以避免断链，其他名称区分重写版与实装原件。完整环境另有经过脱敏、来源与许可核对的用户 Skill 导出。本页不以文件存在或安装数量推断效果提升。

| 便携 Skill | 用途 | 对照的实装方法 |
| --- | --- | --- |
| [evidence-driven-work](../skills/evidence-driven-work/SKILL.md) | 阶段证据循环、重要比较与复核 | 同名个人 Skill、全局约定 |
| [source-led-research](../skills/source-led-research/SKILL.md) | 来源、版本、冲突与推断分离 | deep-research、documentation-lookup 的路由边界 |
| [bounded-delivery](../skills/bounded-delivery/SKILL.md) | 文件归属、委派、独立评审、交接 | 全局约定、strategic-compact |
| [behavioral-verification](../skills/behavioral-verification/SKILL.md) | 复现、red/green、原生与真实流程验证 | systematic-debugging、tdd-workflow、verification-loop、coding-standards |
| [matched-agent-comparison](../skills/matched-agent-comparison/SKILL.md) | 隔离 A/B、grader 校准、负对照 | evidence-driven-work、eval-harness |
| [evidence-to-public-content](../skills/evidence-to-public-content/SKILL.md) | 可公开材料到有证据的内容 | content-engine、项目公开边界 |

每项 Skill 自包含。模板留在公开包 `templates/`，可按需复制进任务笔记，无需把整套模板放进常驻上下文。先在目标客户端确认技能发现路径和安装范围；复制包不会自动安装 MCP、脚本、hook 或服务。

## 实际存在的用户与系统 Skills

来源列说明：**安装记录**是本机 lockfile 记录的 GitHub source 与当前目录名的匹配，确认的是来源映射；**本地 provenance**是已读的历史溯源记录。没有重新联网确认上游最新内容、精确 commit 或所有许可证，链接是原项目入口，不是已审计供应链声明。本地正文可能已经修改。无明确依据的来源写未核实，不能靠名称猜仓库。

### 通用流程、研究与评审

| 名称 / 位置 | 本次证据 | 能力描述（实装元数据） | 已知上游 |
| --- | --- | --- | --- |
| `agent-introspection-debugging` / A | 元数据盘点 | Structured self-debugging workflow for AI agent failures using capture, diagnosis, contained recovery, and introspection reports. | 未核实 / 本地工作方法 |
| `agent-sort` / A | 正文已读 | Build an evidence-backed ECC install plan for a specific repo by sorting skills, commands, rules, hooks, and extras into DAILY vs LIBRARY buckets using parallel repo-aware review passes. Use when ECC should be trimmed to what a project actually needs instead of loading the full bundle. | 未核实 / 本地工作方法 |
| `coding-standards` / A | 正文已读 | Apply cross-project naming, readability, type-safety and maintainability conventions during implementation or code-quality review. Framework architecture and security reviews use their focused skills. | [本地 provenance：Everything Claude Code](https://github.com/affaan-m/everything-claude-code) |
| `deep-research` / A | 正文已读 | Research a question in depth using available search and source-reading tools, then synthesize a cited report with source quality, uncertainty, and decision-relevant findings. | 未核实 / 本地工作方法 |
| `documentation-lookup` / A | 元数据盘点 | Verify library and framework behavior against current primary documentation and the installed version, using Context7 when available or official documentation search when it is not. Use for API, setup, or version-sensitive implementation questions. | 未核实 / 本地工作方法 |
| `eval-harness` / A | 正文已读 | Design and run evidence-based evaluations of agent, prompt, skill, or harness changes, with isolated trials and outcome-based grading. Use for reliability comparisons and regression evaluation, not as a replacement for ordinary project tests. | 未核实 / 本地工作方法 |
| `everything-claude-code` / A | 元数据盘点 | Work on the ECC source repository itself, such as its skill catalog, installer, compatibility mappings or tests. Do not use this as general Codex coding guidance or a reason to install the ECC bundle. | 未核实 / 本地工作方法 |
| `evidence-driven-work` / A | 正文已读 | Apply recurring source-backed comparison, fresh review, calibrated verification and refinement to substantial research, planning, design, implementation or agent-method work, including individual sections and phases. Use existing focused skills for their specialist tasks; simple self-contained answers do not need this workflow. | 未核实 / 本地工作方法 |
| `exa-search` / A | 元数据盘点 | Use an available Exa integration for web, code, or company research when the user asks for Exa or the task calls for its specific capabilities. General research can use other available search tools. | 未核实 / 本地工作方法 |
| `security-review` / A | 元数据盘点 | Review the security boundaries affected by an implementation change, such as authentication, authorization, untrusted input, uploads, secrets or sensitive data. Use codex-security for repository/diff vulnerability scans and dedicated provider skills for setup. | [本地 provenance：Everything Claude Code](https://github.com/affaan-m/everything-claude-code) |
| `strategic-compact` / A | 正文已读 | Preserve a concise task handoff at logical phase boundaries during long work, and use manual context compaction only when the running client supports it and it benefits the task. | 未核实 / 本地工作方法 |
| `tdd-workflow` / A | 正文已读 | Use red-green-refactor for new production behavior and bug fixes, and protect substantive refactors with meaningful regression tests using the project's existing test tools. | 未核实 / 本地工作方法 |
| `verification-loop` / A | 正文已读 | Verify substantive code changes with the project's build, type, lint, test, security, and diff checks, preserving real failures and reporting validation gaps. | 未核实 / 本地工作方法 |
| `systematic-debugging` / C | 正文已读 | Investigate application bugs, failing tests, build failures, and integration regressions using reproduction, discriminating experiments, and root-cause evidence. Use for software faults; agent execution failures belong to agent-introspection-debugging, and comparative agent evaluations belong to eval-harness. | [安装记录：obra/superpowers](https://github.com/obra/superpowers)；正文已本地改写 |

### 前后端、接口与开发工具

| 名称 / 位置 | 本次证据 | 能力描述（实装元数据） | 已知上游 |
| --- | --- | --- | --- |
| `api-design` / A | 元数据盘点 | Design or review HTTP API contracts, including resources, methods, statuses, response schemas, pagination, filtering, rate-limit responses and compatibility. Server layering and security scans use focused skills. | [本地 provenance：Everything Claude Code](https://github.com/affaan-m/everything-claude-code) |
| `backend-patterns` / A | 元数据盘点 | Structure server application layers, data access, caching, jobs, middleware and operational error handling in an existing backend. API contracts, provider-specific setup and security scans use focused skills. | [本地 provenance：Everything Claude Code](https://github.com/affaan-m/everything-claude-code) |
| `bun-runtime` / A | 元数据盘点 | Bun as runtime, package manager, bundler, and test runner. When to choose Bun vs Node, migration notes, and Vercel support. | 未核实 / 本地工作方法 |
| `frontend-patterns` / A | 元数据盘点 | Implement React or Next.js component composition, state, effects, forms and rendering behavior using the existing stack. Use frontend-design for visual direction and the installed React review skill for post-edit review. | [本地 provenance：Everything Claude Code](https://github.com/affaan-m/everything-claude-code) |
| `mcp-server-patterns` / A | 元数据盘点 | Build MCP servers with Node/TypeScript SDK — tools, resources, prompts, Zod validation, stdio vs Streamable HTTP. Use Context7 or official MCP docs for latest API. | 未核实 / 本地工作方法 |
| `nextjs-turbopack` / A | 元数据盘点 | Diagnose Next.js bundler selection, Turbopack compatibility, development caching or bundle-analysis issues. Use the installed Next.js version and official guidance; ordinary UI implementation does not need this workflow. | 未核实 / 本地工作方法 |
| `product-capability` / A | 元数据盘点 | Translate PRD intent, roadmap asks, or product discussions into an implementation-ready capability plan that exposes constraints, invariants, interfaces, and unresolved decisions before multi-service work starts. Use when the user needs an ECC-native PRD-to-SRS lane instead of vague planning prose. | 未核实 / 本地工作方法 |
| `vercel-composition-patterns` / A | 元数据盘点 | React composition patterns that scale. Use when refactoring components with boolean prop proliferation, building flexible component libraries, or designing reusable APIs. Triggers on tasks involving compound components, render props, context providers, or component architecture. Includes React 19 API changes. | [安装记录：vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) |
| `vercel-react-best-practices` / A | 元数据盘点 | React and Next.js performance optimization guidelines from Vercel Engineering. This skill should be used when writing, reviewing, or refactoring React/Next.js code to ensure optimal performance patterns. Triggers on tasks involving React components, Next.js pages, data fetching, bundle optimization, or performance improvements. | [安装记录：vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) |
| `vercel-react-native-skills` / A | 元数据盘点 | React Native and Expo best practices for building performant mobile apps. Use when building React Native components, optimizing list performance, implementing animations, or working with native modules. Triggers on tasks involving React Native, Expo, mobile performance, or native platform APIs. | [安装记录：vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) |
| `vercel-react-view-transitions` / A | 元数据盘点 | Guide for implementing smooth, native-feeling animations using React's View Transition API (`ViewTransition` component, `addTransitionType`, and CSS view transition pseudo-elements). Use this skill whenever the user wants to add page transitions, animate route changes, create shared element animations, animate enter/exit of components, animate list reorder, implement directional (forward/back) navigation animations, or integrate view transitions in Next.js. Also use when the user mentions view transitions, `startViewTransition`, `ViewTransition`, transition types, or asks about animating between UI states in React without third-party animation libraries. | [安装记录：vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) |
| `e2e-testing` / A | 元数据盘点 | Create or repair a Playwright end-to-end test suite, including page objects, fixtures, CI, artifacts, and flaky-test diagnosis. Use for maintained test coverage; use browser-control skills for ad hoc browsing. | 未核实 / 本地工作方法 |
| `webapp-testing` / A | 元数据盘点 | Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs. | [安装记录：anthropics/skills](https://github.com/anthropics/skills) |

### 写作、传播、研究产物

| 名称 / 位置 | 本次证据 | 能力描述（实装元数据） | 已知上游 |
| --- | --- | --- | --- |
| `article-writing` / A | 元数据盘点 | Draft or substantially revise articles, essays, tutorials, guides, and newsletter issues with clear structure, evidence, and an appropriate voice. Use for authored long-form content, not routine answers, code review explanations, or minor copy edits. | 未核实 / 本地工作方法 |
| `brand-voice` / A | 元数据盘点 | Create or update a reusable writing voice profile from representative source material when the user requests voice analysis, brand voice guidance, or consistency across multiple outputs. Reuse an existing confirmed profile; ordinary drafting and minor edits do not require a separate profiling workflow. | 未核实 / 本地工作方法 |
| `content-engine` / A | 正文已读 | Create platform-native content systems for X, LinkedIn, TikTok, YouTube, newsletters, and repurposed multi-platform campaigns. Use when the user wants social posts, threads, scripts, content calendars, or one source asset adapted cleanly across platforms. | 未核实 / 本地工作方法 |
| `crosspost` / A | 元数据盘点 | Multi-platform content distribution across X, LinkedIn, Threads, and Bluesky. Adapts content per platform using content-engine patterns. Preserve identical wording when explicitly requested. Use when the user wants to distribute content across social platforms. | 未核实 / 本地工作方法 |
| `investor-materials` / A | 元数据盘点 | Create and update pitch decks, one-pagers, investor memos, accelerator applications, financial models, and fundraising materials. Use when the user needs investor-facing documents, projections, use-of-funds tables, milestone plans, or materials that must stay internally consistent across multiple fundraising assets. | 未核实 / 本地工作方法 |
| `investor-outreach` / A | 元数据盘点 | Draft cold emails, warm intro blurbs, follow-ups, update emails, and investor communications for fundraising. Use when the user wants outreach to angels, VCs, strategic investors, or accelerators and needs concise, personalized, investor-facing messaging. | 未核实 / 本地工作方法 |
| `market-research` / A | 元数据盘点 | Conduct market research, competitive analysis, investor due diligence, and industry intelligence with source attribution and decision-oriented summaries. Use when the user wants market sizing, competitor comparisons, fund research, technology scans, or research that informs business decisions. | 未核实 / 本地工作方法 |
| `research-paper-writer` / A | 元数据盘点 | Structure or substantially revise a research paper or survey from supplied results and verified literature; follow the actual venue and evidence limits. | [安装记录：ailabs-393/ai-labs-claude-skills](https://github.com/ailabs-393/ai-labs-claude-skills) |
| `video-editing` / A | 元数据盘点 | AI-assisted video editing workflows for cutting, structuring, and augmenting real footage. Covers the full pipeline from raw capture through FFmpeg, Remotion, ElevenLabs, fal.ai, and final polish in Descript or CapCut. Use when the user wants to edit video, cut footage, create vlogs, or build video content. | 未核实 / 本地工作方法 |
| `x-api` / A | 元数据盘点 | X/Twitter API integration for posting tweets, threads, reading timelines, search, and analytics. Covers OAuth auth patterns, rate limits, and platform-native content posting. Use when the user wants to interact with X programmatically. | 未核实 / 本地工作方法 |

### 视觉、网页与文档

| 名称 / 位置 | 本次证据 | 能力描述（实装元数据） | 已知上游 |
| --- | --- | --- | --- |
| `design-taste-frontend` / A | 元数据盘点 | Explore art-directed frontend layouts and interaction design when a creative visual direction or substantial UI redesign is requested. Use its design dials and inspiration selectively; preserve the existing stack, brand, accessibility, and performance requirements for product work. | [安装记录：leonxlnx/taste-skill](https://github.com/leonxlnx/taste-skill) |
| `docx` / A | 元数据盘点 | Inspect or repair DOCX OOXML, tracked changes, comments, and docx-js layouts using the bundled low-level helpers. Use for these specific document internals or as a fallback when the available document-authoring skill cannot handle the operation; ordinary Word authoring should use the host document workflow when available. | [安装记录：anthropics/skills](https://github.com/anthropics/skills) |
| `fal-ai-media` / A | 元数据盘点 | Use fal.ai when the user requests or selects that provider for image, video, or audio generation. Check live models, schema, upload scope and cost before an authorized job; ordinary image requests can use native image generation. | 未核实 / 本地工作方法 |
| `frontend-design` / A | 元数据盘点 | Design and implement a distinctive web interface when the user requests a new visual direction, polished page, landing page, or substantial UI styling. Respect the existing design system for product changes; do not trigger for non-visual maintenance or unrelated document/poster work. | [安装记录：anthropics/skills](https://github.com/anthropics/skills) |
| `frontend-slides` / A | 元数据盘点 | Create or improve browser-based HTML slide decks, or convert a supplied PPT/PPTX to HTML. Use when HTML is the chosen deliverable; ordinary PowerPoint or Google Slides work belongs to the available presentation workflow. | 未核实 / 本地工作方法 |
| `web-artifacts-builder` / A | 元数据盘点 | Build a standalone interactive HTML deliverable when the user needs a shareable file with bundled assets. Use for multi-component artifacts that justify bundling; use the existing project workflow for app development and direct HTML/CSS/JS for simple standalone pages. | [安装记录：anthropics/skills](https://github.com/anthropics/skills) |
| `web-design-guidelines` / A | 元数据盘点 | Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices". | [安装记录：vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) |
| `theme-factory` / C | 元数据盘点 | Apply or adapt a reusable color and typography palette to an artifact when a theme is needed; preserve the user's existing design system. | 未核实 / 本地工作方法 |
| `structured-document-extraction` / C | 元数据盘点 | Extract tables, headings and structured text from complex local PDF or DOCX files with installed Docling when ordinary extraction is insufficient. | 未核实 / 本地工作方法 |

### 运行环境与本地专业工具

| 名称 / 位置 | 本次证据 | 能力描述（实装元数据） | 已知上游 |
| --- | --- | --- | --- |
| `agent-environment` / C | 正文已读 | Audit, upgrade, or repair this user's local Codex skills, MCP configuration, agent roles, and pinned tool installation. | 未核实 / 本地工作方法 |
| `connected-workflows` / C | 元数据盘点 | Coordinate an authorized task across connected documents, email, calendars and project services. Use for cross-service work; route single-service actions to that provider's focused skill and do not create accounts or send messages by default. | 未核实 / 本地工作方法 |
| `dmux-workflows` / A | 元数据盘点 | Operate or configure an existing dmux/tmux workflow, or help a user who specifically chooses dmux for terminal agent orchestration. Generic parallel work in Codex should use available native multi-agent tools without installing another harness. | 未核实 / 本地工作方法 |
| `execution-routing` / C | 正文已读 | Choose local, WSL, cloud or hybrid execution for a substantial task and prepare verified handoffs. Use when remote execution or parallel local/cloud work would help; do not treat installed cloud tools as a ready environment. | 未核实 / 本地工作方法 |
| `good-learning` / C | 元数据盘点 | Teach user-supplied slides, course PDFs and problem sets for exam preparation, with selectable teaching flows, source-linked explanations, actual-answer mistake tracking and cross-chat progress. Use for learning a course, revising, studying lecture notes or preparing for an exam, not unrelated research or ordinary software debugging. | 未核实 / 本地工作方法 |
| `local-data-sql` / C | 元数据盘点 | Query selected local CSV, JSON or Parquet files with the installed DuckDB CLI for joins, grouped checks and repeatable SQL analysis. Use when local SQL fits the task; preserve an existing spreadsheet or project workflow. | 未核实 / 本地工作方法 |
| `local-knowledge-search` / C | 元数据盘点 | Search an explicitly selected local Markdown collection with installed QMD for natural-language retrieval and source lookup. Do not automatically index personal memory, the home directory, or unrelated documents; web research uses web tools. | 未核实 / 本地工作方法 |
| `marimo-notebooks` / C | 元数据盘点 | Create or maintain a reactive Python notebook or local analytical app in marimo when the user requests that format or reactive parameter exploration. | 未核实 / 本地工作方法 |
| `playwright` / C | 元数据盘点 | Automate a browser with an existing Playwright CLI or a deliberately selected task-scoped CLI setup. Use for terminal browser workflows; prefer the host browser tools, configured MCP, or existing test framework when they already provide the required capability. | 未核实 / 本地工作方法 |
| `project-environments` / C | 元数据盘点 | Reproduce or repair selected project runtimes and native dependency environments with existing manifests and installed mise or pixi. Use for environment setup or mismatches, not to replace a working project package manager. | 未核实 / 本地工作方法 |
| `project-workflow` / C | 元数据盘点 | Coordinate dependent repository tasks and isolated Git worktrees with installed Beads and Worktrunk for multi-part implementation. Preserve an existing project tracker; skip for small self-contained edits. | 未核实 / 本地工作方法 |
| `repository-intelligence` / C | 元数据盘点 | Use local structural search, bounded repository bundles and qualified repository graph queries when ordinary text search or targeted source reads are insufficient. | 未核实 / 本地工作方法 |
| `reverse-engineer-anything` / C | 元数据盘点 | Inspect shipped binaries, archives, Electron/JavaScript packages, or recorded runtime evidence with the locally installed REA toolkit; skip ordinary source-repository analysis. | 未核实 / 本地工作方法 |
| `wsl-coding` / C | 正文已读 | Read, edit, build, and test a project in an existing WSL Linux distribution from Windows Codex. Use for WSL or Ubuntu project paths and Linux toolchain issues; do not apply to ordinary Windows projects or remote Linux servers. | 未核实 / 本地工作方法 |
| `deploy-to-vercel` / A | 元数据盘点 | Deploy applications and websites to Vercel when the user requests deployment, a live link, or a preview deployment, using their authorized project and environment. | [安装记录：vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) |
| `vercel-cli-with-tokens` / A | 元数据盘点 | Deploy and manage projects on Vercel using token-based authentication. Use when working with Vercel CLI access tokens for deployment, project setup, or environment management. | [安装记录：vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) |

### 客户端系统目录

| 名称 / 位置 | 本次证据 | 能力描述（实装元数据） | 已知上游 |
| --- | --- | --- | --- |
| `imagegen` / S | 元数据盘点 | Generate or edit raster images when the task benefits from AI-created bitmap visuals such as photos, illustrations, textures, sprites, mockups, or transparent-background cutouts. Use when Codex should create a brand-new image, transform an existing image, or derive visual variants from references, and the output should be a bitmap asset rather than repo-native code or vector. Do not use when the task is better handled by editing existing SVG/vector/code-native assets, extending an established icon or logo system, or building the visual directly in HTML/CSS/canvas. | 未核实 / 本地工作方法 |
| `openai-docs` / S | 元数据盘点 | Use for Codex models/pricing, scheduled tasks, skills, settings, setup, troubleshooting, customization, automations, and self-knowledge—including 'you,' 'your,' 'this app,' or 'this coding agent' when they refer to Codex—and for OpenAI APIs/products and ChatGPT Work. Also use for model choice/migration, prompting, SDKs, Responses, Realtime, agents, evals, and Chat/Work/Codex comparisons. Do not use for generic app/software tasks that merely mention Codex. | 未核实 / 本地工作方法 |
| `review-agent` / S | 元数据盘点 | Perform a read-only, defect-first review of a specified code change and return every actionable finding. Use when another agent delegates review of uncommitted changes, a base-branch diff, a commit, or custom review instructions. | 未核实 / 本地工作方法 |
| `skill-creator` / S | 正文已读 | Create or update a Codex skill with appropriately scoped instructions and any needed supporting resources. | 未核实 / 本地工作方法 |
| `skill-installer` / S | 元数据盘点 | Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). | 未核实 / 本地工作方法 |

## 安装记录中的历史项

下列名称仍出现在安装记录，却没有在本次两个顶层根目录或系统子目录找到对应 `SKILL.md`。它们可能已迁移、移除或由别的插件提供；不能据此称已安装，也不建议自动补装：

`academic-researcher`、`academic-writing`、`agent-browser`、`ai-image-generation`、`better-auth-best-practices`、`brainstorming`、`citation-management`、`copywriting`、`dispatching-parallel-agents`、`executing-plans`、`find-skills`、`finishing-a-development-branch`、`knowledge-synthesis`、`literature-review`、`pdf`、`receiving-code-review`、`remotion-best-practices`、`requesting-code-review`、`research-synthesis`、`subagent-driven-development`、`supabase-postgres-best-practices`、`test-driven-development`、`using-git-worktrees`、`using-superpowers`、`verification-before-completion`、`writing-plans`、`writing-skills`。

## DAILY / LIBRARY 怎样落地

`agent-sort` 的方法是按实际项目证据选择。DAILY 表示该项目日常相关且容易发现，不要求每次加载正文；LIBRARY 表示保留可检索入口，不是删除。React 项目可用依赖、TSX 文件与 CI 支持前端 Skills 的 DAILY 判断；纯文档项目无需默认加载数据库和端到端测试说明。先复用现有 catalog，只有确实需要时增加 router。复制 Claude 目录、slash command 或 hook 名称不会使 Codex 获得对应运行能力。

这个目录提供透明度与选用依据，不是建议全部安装。可执行工具、账号授权和服务状态必须分别验证。
