# 我的 Codex 工作流

ChatGPT / Codex 重度用户，500 刀 Pro 在用。分享一下我怎么让它接下一整件事，也想听听大伙的建议。

我给目标和验收要求，Codex 自己读项目、查资料、拆任务、动手做。出问题就查原因、继续修，做完把成品和检查结果交回来。任务太长，先把进度写下来，下次接着干。重要取舍和最后验收，还是我来。

这些能力要靠规则、工具、资料和检查方法配合。把它们接起来的这套工作环境，就叫 **harness**。我主要抄了下面几招。

## ① 资料用到哪，读到哪

OpenAI 的 **渐进式披露**，意思就是先给目录，需要时再打开具体内容。Anthropic 的上下文工程也强调，把当前任务真正需要的信息交给 Agent。

我的全局 `AGENTS.md` 写通用工作习惯，项目里的同名文件写这个项目怎么运行、怎么检查。**Skill 可以理解成某类任务的操作说明**，比如查资料、排错、做复核。先看名称和用途，用得上再读步骤。我的技能组织也参考了 ECC。 [OpenAI Skills](https://learn.chatgpt.com/docs/build-skills) · [Anthropic 上下文工程](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) · [ECC](https://github.com/affaan-m/ECC)

工具负责把事做起来。MCP 把文档和外部服务接进来，CLI 就是可以在终端运行的程序。查接口就翻对应版本的官方文档，找代码就查定义和引用，分析数据就先筛选、汇总。每个工具在哪一步用，得想清楚，光装着容易吃灰。

## ② 能分头干的活，就分头干

主 Agent 负责整件事，子 Agent 接其中一项活。

我准备了查代码、查文档、挑问题、操作界面四类角色。开几个，由主 Agent 看任务决定。

**Beads 管先后顺序**，前面的任务完成了，后面才能接。**Worktrunk 管独立工作副本**，不同 Agent 可以在各自的目录和分支里改代码，最后再合到一起。这样既能并行，也能看清谁改了哪里。 [Beads](https://github.com/gastownhall/beads) · [Worktrunk](https://github.com/max-sixty/worktrunk)

查资料的子 Agent 把结论和出处带回来，主 Agent 需要时再追细节。这也是 Anthropic 多 Agent 研究系统采用的做法。 [Anthropic 多 Agent 研究](https://www.anthropic.com/research/multi-agent-research-system)

模型也按活选。工具允许时，简单活可以交给够用的便宜模型，或者调低同一模型的推理强度，也就是减少它投入的思考。复杂判断再加码。小事自己干就行，多开几个也得花时间交接。

## ③ 做完先验，再找另一个 Agent 挑刺

我参考 **Superpowers** 的排错方法，先把问题复现出来，找证据判断原因，改完再用原来的步骤检查。

代码跑测试，网页实际点流程，下载功能就把文件拿下来核内容。Boris Cherny 在 X 上也提过，让 Claude 用浏览器验收自己的改动。我用 Playwright 这类工具，让 Codex 看得到实际结果，才知道下一步该修哪儿。 [Superpowers](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md) · [Boris 原帖](https://x.com/bcherny/status/2007179832300581177) · [阅读存档](https://threadreaderapp.com/thread/2007179832300581177.html)

重要改动，再找一个独立的 Agent，给它原始需求、改动和检查结果，让它重新看一遍。主 Agent 还得核实它说的问题，再修、再测。

我连自己的建议都要求它过脑子。有依据就反驳，别陪我一路“你说得对”。

## ④ 长任务，留一份能接班的进度单

这叫**状态外置**，把进度存成文件。Anthropic 的长任务文章和团队实践 PDF 都讲过这个思路。 [长任务 Harness](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) · [团队实践 PDF](https://www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf)

我会让 Codex 写清楚目标是什么、做了哪些决定、卡在哪里、检查过什么、下一步干什么。换个 chat，就先给它读这份交接文件，再核对当前项目。

任务账本还能在查进度时检查登记过的结果文件，有变动就提醒重新验。这样一个项目分几次做，也能查清楚进度，省得每次都从头讲前情。

## ⑤ 让它帮我比较，哪种工作方式更合适

Google 的 **Harness²** 研究让 Agent 提出工作方式的改法，试跑、比较，再留下有依据的经验。我参考这个思路，以及 OpenAI 的 Skill 评测方法，让 Codex 也参与改进这套 workflow。 [Harness²](https://github.com/google-research/harness2) · [OpenAI Skill 评测](https://developers.openai.com/blog/eval-skills)

做法挺直白。给它常做的任务和反馈，让它找出最卡的一两步。原方案先留着，用同样的输入和验收标准试新方案，看结果、耗时和开销，再决定留不留。工具箱里也有可复跑的评测和检查记录，方便回头核对。

我也会担心规则和 Skills 越堆越多，多花 token，还把解题路子写死。所以先在当前项目试，好用就留，累赘就删。GitHub Trending 可以多逛，自己的活也得真拿来跑。

## 想抄作业，链接放这了

我的配置、Skills 和环境复现入口都在仓库里，中英文 README 都有。可以自己看，也可以把链接直接发给你的 Codex，让它帮你按自己的电脑和任务来配置。

[我的 Codex 工作流工具箱](https://github.com/Naaeeen/codex-agent-workflow)

可以连这句话一起发。

“请阅读这个仓库，检查我的现有环境。先完整备份我的项目和 Agent 配置，再按仓库说明在独立目录里复现。逐项检查哪些已经能用，哪些需要我自己安装客户端或登录账号。请按我的实际任务选配置，保留恢复方法。”

最后叠个甲。这是我的个人用法，换台电脑、换个项目都可能踩坑，照着改出了问题得自己负责哈。**建议先做好完整备份，确认能恢复，再动手。**备份放在自己的安全位置，密钥和私人资料别传到公开仓库。

欢迎拍砖。你最离不开哪条规则、哪个 Skill？它到底帮你省了哪一步，我也想抄抄。

---

本文由 Codex 辅助整理资料、文字与配图。
