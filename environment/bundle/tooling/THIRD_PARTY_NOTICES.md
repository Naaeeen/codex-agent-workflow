# Licenses and provenance

The root MIT license covers the author's original instructions, portable rewrites, installer code, harness utilities and documentation. Third-party components retain their own licenses and attribution. A dependency entry or download recipe grants no additional rights to that component.

| Material | Source and license record |
| --- | --- |
| ECC-derived Skills and adapted Git hooks | [ECC](https://github.com/affaan-m/ECC/tree/d2ef2680594f9a17526a6e1a2e18b3d242c5d17b), [MIT notice](licenses/ECC-MIT.txt). Local adaptations have different revisions. The original March generator input for `everything-claude-code` is unknown. |
| Superpowers-derived debugging | [Superpowers](https://github.com/obra/superpowers/tree/22f0b463e7a5e579904dd6211a520321035526f7), [MIT notice](licenses/SUPERPOWERS-MIT.txt), with local workflow adaptations. |
| Design taste Skill | [taste-skill](https://github.com/leonxlnx/taste-skill/tree/f6b76575f949707b4e3c37cd86cb44b0b98643e8), [MIT notice](licenses/TASTE-MIT.txt). |
| Research paper Skill | [AI Labs Skills](https://github.com/ailabs-393/ai-labs-claude-skills/tree/1a12bc7aadcc7b211f77a7455db454b77a71f827), [MIT notice](licenses/AI-LABS-MIT.txt). Optional rendered paper examples are linked upstream. |
| Vercel-derived Skills | [Pinned repository license declaration](https://github.com/vercel-labs/agent-skills/blob/1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62/README.md#L214-L216) states MIT. Existing per-Skill MIT declarations are preserved. Local authorization and credential-handling adaptations are retained. |
| Anthropic-derived Skills | [Official pinned Skills](https://github.com/anthropics/skills/tree/2c5958ecac7cee2b583967a2c4981d0f4a75c579) and each included license file. `docx` uses this Apache-licensed revision in place of the author's old redistribution-restricted installation. |
| Playwright Skill | [OpenAI curated source](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/playwright). Its local Apache license and Microsoft NOTICE are preserved. |
| Good-learning | [Recorded upstream revision](https://github.com/yoli-mi/good-learning/tree/1255c4d7f0b602901100d29d85235ad2537eec31) and its included MIT license. Course-specific paths and progress locations are removed. |
| Downloaded tool and model dependencies | Their source licenses apply. See the pinned dependency manifest and upstream release/model pages. GitNexus is recorded with a noncommercial license. Host plugins are reinstalled through the reader's official client. |
| `proxy_tools` pure-Python wheel | The deterministic wheel preserves the exact upstream runtime file and BSD notice. [Rebuild source](https://github.com/Naaeeen/codex-agent-workflow/blob/main/tools/build_proxy_tools_wheel.py) verifies the public sdist and license bytes without executing `setup.py`. Upstream package metadata says MIT while its actual source and notice specify BSD; the latter notice is retained in the wheel. |

The environment portability record identifies copied, adapted and replaced files. Copy relevant third-party notices when extracting a Skill or helper from this repository. The repository's original-work MIT license does not override upstream restrictions.

## 中文说明

原创代码、说明和便携改写采用根目录 MIT 许可。第三方 Skills、脚本、依赖和模型保留各自的许可及署名。单独复制某个 Skill 时，请一起保留它的许可证和上面的来源说明。旧版受限 `docx` 已由明确标注的官方 Apache 版本替换。
