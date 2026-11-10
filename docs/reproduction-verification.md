# Environment reproduction verification

Checked on Windows x64 during the environment-package revision. The dependency reference uses Codex CLI 0.157.1, Node 24.22.2, and Python 3.13.7/3.14.3. These records describe the tested conditions and package behavior.

## Completed checks

| Check | Observed result |
| --- | --- |
| Production manifest | All declared payloads render, hash-check and stage in a new directory. Existing targets and changed managed files are rejected |
| Full dependency restoration | All 30 automatic groups installed in an isolated validation directory. Includes six npm environments, eight Python environments, two exact wheel rebuilds, native tools, Chromium, QMD assets and Docling assets |
| Recovery during development | A source-only `proxy_tools` dependency blocked the first Serena install. An audited deterministic pure-Python wheel fixed it. Completed groups were hash-verified on retry, and the new wheel was added only after the original managed files matched their receipt |
| Model assets | Pinned public QMD and Docling assets downloaded and passed their SHA-256 checks. This establishes the files, not model-answer quality |
| Skill discovery | Native CLI discovery returned all 62 exported user Skill paths enabled from both the default workspace and an unrelated project, with zero Skill errors and no model turn |
| Fixed Codex entry | Official full CLI archive installed, retry verified, generated launcher selected its `bin/codex.exe` and reported 0.157.1 |
| Node in a clean PATH | Codex app-server command execution resolved the pinned Node as v24.22.2 when the caller had no Node. Explicit inherited-PATH mode preserved the caller's choice |
| Actual tool entries | Repomix, Beads, Worktrunk and Marimo returned expected versions. GitNexus's verified native binding loaded. PDF package import and both patched wheel hashes matched the reference |
| Restored browser operation | Pinned Chromium opened a controlled loopback page, clicked its button, verified the resulting page state and closed successfully through the restored Playwright route |
| Local MCP startup | Restored Serena initialized through its recorded arguments and reported exactly the five configured navigation tools |
| Optional Pi lab | The restored offline SDK trial completed through the unified launcher using a synthetic provider, with a passing result and private session output |
| Original harness and audit suites | 232 tests completed, 229 passed and three platform/privilege cases skipped, using the restored environment. Suites cover ledger/improvement, graders, observer, bridge, handoff, Skill-read evidence and environment audit |
| Installer regression suites | Windows and Ubuntu WSL runs cover traversal, links/reparse points, source integrity, atomic no-replace staging, existing-file protection, dependency receipts, group order, runtime preflight, hash-locked local wheel resolution and dry-run behavior |
| License-sensitive replacements | Restricted local `docx` is replaced with the pinned official Apache revision. The extra proxy wheel retains exact upstream code and BSD notice, despite conflicting MIT package metadata |

The base validation fixture was updated only for the newly added public proxy wheel and the known generated-launcher change, after its previous managed files were checked against the recorded hashes. Dependency packages were installed from the published recipes. No reader account, cloud job or paid model turn was used for these installation checks.

## Privacy and publication checks

- Multiple read-only passes covered both the old public repository and the new export, including source text, configuration, Git author metadata, binary metadata and asset provenance.
- Removed the original WSL project suffix, an author-machine build folder identifier, private-input fingerprints and the optional contact-bearing paper PDF.
- Retained only public-source integrity hashes. Command examples use synthetic identifiers or reader-owned placeholders.
- Excluded authentication state, chats, memory content, original approval commands, project data, indexes, runtime observations, browser sessions, raw logs and backups.
- PNG and remaining PDF assets were checked against public upstream content. Licenses and authorship notices remain with third-party source.

## Reader-side checks

The reference dependency installer targets Windows x64. Linux WSL tests cover installer file operations and contracts, not installation of the Windows tool set. System Skills and hosted plugins come from the reader's client. Account-backed MCP, cloud execution, platform availability and real task outcomes need validation using that reader's account and projects.

The reproduction receipt covers published managed files. Dependency receipts cover their installed code and artifacts. Private runtime state is created later in the reader's separate environment. Keep it outside the public source checkout.

## 中文摘要

30 个自动依赖组已在独立目录实际安装，公开模型资产也完成下载和哈希核对。原 harness 与审计源码的 232 项测试中，229 项通过、3 项因平台或权限条件跳过。原生 CLI 能发现全部 62 个用户 Skills。账号连接、宿主插件、云端与真实任务效果由使用者在自己的环境继续验证。

发布检查覆盖文本、配置、提交身份、图片/PDF 元数据和来源。原机项目指纹、私有输入哈希和无关个人数据均不属于复现包。
