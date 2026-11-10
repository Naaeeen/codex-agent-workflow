# How this agent workflow works

I organize my agent setup around a few connected actions: define the result, collect evidence, divide the work, implement it, review it, and leave enough context to continue. This guide explains the mechanics so you can try the pieces that fit your own work. Suggestions are welcome, especially concrete examples of where a step adds more overhead than value.

The account is based on the current global working agreements and selected installed Skills. It describes the configured method. Historical execution and effectiveness require evidence from the corresponding task; this documentation audit does not supply that evidence.

## Three instruction layers

| Layer | Contents | Read when | Purpose |
| --- | --- | --- | --- |
| Global AGENTS.md | Cross-project scope, collaboration, verification, privacy and authorization defaults | The supporting client discovers and loads it; verify the target client's path | Keep shared decisions in one place |
| Project rules, README and CI | Architecture, actual commands, output locations and project acceptance | Working in that project | Avoid importing another project's stack, permissions or old PASS state |
| Skills and references | Procedures for a particular type of work | Select by description, then read relevant instructions and references | Keep detailed methods available without loading everything |

The [global template](../templates/global-AGENTS.md) preserves the standing working agreements. The [six portable Skills](skills-catalog.en.md#six-portable-skills) serve the smaller project starter. Full reproduction uses the [complete user Skill export](../environment/bundle/codex-home/skills/) and its companion tools, with provenance, licenses and privacy adaptations recorded separately.

The host's instruction hierarchy governs priority. The template follows the current request and more specific project guidance within that hierarchy; it does not override system/developer instructions or host permissions. Verify discovery in a new target session. Global guidance is recurring context; Skill names and descriptions support selection, their bodies provide task-specific detail. No token savings were measured here.

### What each global section changes

| Original section | Decision it governs | Example | Common mistake |
| --- | --- | --- | --- |
| Scope and execution | Inspect state, versions, capabilities and acceptance; continue authorized reversible work | Read export tests and dirty files before editing | Treat autonomy as publication permission |
| Communication and judgment | Separate facts, judgments and material limits; examine assumptions | Report local success and an untested remote boundary | Replace conclusions with disclaimers or accept every suggestion |
| Delegation and cost | Parallelize independent questions, assign files, review consequential work freshly | Separate API and UI ownership | Two workers overwrite one file; a new role label is called independent review |
| Implementation and verification | Use project tools; meaningful red/green; check user behavior | Reproduce duplicate submission before fixing it | A build becomes a claim of end-to-end success |
| Security and external actions | Preserve permissions; use scoped external authorization; back up global changes | Prepare a PR locally, push only within authorization | Enable a service because a guide recommends it |
| Context and evidence | Keep a requirement-to-verification record at meaningful checkpoints | Preserve a failed experiment and update the next step | Record only the final PASS or ritualize tiny edits |

## 1. Start with the result and current state

**When:** a new project, behavior change, or resumed long task. A small edit needs only a brief check.

**Mechanics:** read applicable instructions and project entry points. Inspect relevant source, working-tree changes, manifests, lockfiles and CI. Write the user-visible outcome and observable acceptance. For complex work, add dependencies, risks, ownership and a stopping condition. Discover tools actually exposed by the host before selecting them; names in another client's guide are not runtime capabilities.

**Why:** the plan must fit the current workspace and protect existing work.

**Example:** “CSV download preserves Chinese text and prevents duplicate requests.” Locate the download handler and existing tests, identify the actual package manager, and verify file contents and request count. A visible button is only part of that acceptance.

**Common mistake:** ignoring dirty files, choosing a new framework before reading the manifest, or reusing an old screenshot as current verification. Use the [task brief](../templates/task-brief.md).

## 2. Research questions that could change the decision

**When:** unfamiliar or changing APIs, consequential technical/product choices, and multi-source research.

**Mechanics:** split the decision into bounded questions. Inspect installed versions and project code first; then use available documentation tools or primary sources. Read decisive sections and limitations, recording URL, date/version and actual access scope. Resolve contradictions by checking definitions, environment and versions. Separate facts, inference and hypotheses.

**Why:** more search results do not automatically produce stronger evidence, and an API name can hide version differences.

**Example:** to determine whether cancelling a streaming response stops backend work, combine the documented contract, relevant implementation and a controlled project test. Client cancellation alone leaves server behavior unverified.

**Common mistake:** counting copied articles as independent confirmation, installing a new MCP merely to research, or describing a search excerpt as a full-source review. Use the [source record](../templates/source-record.md).

## 3. Revisit the evidence at meaningful checkpoints

**When:** substantial research, planning, design, implementation or agent-method changes.

**Mechanics:** at phase entry, after changed assumptions/check failures/review findings, and before acceptance, revisit requirement → evidence → decision → revision → verification. Record meaningful subsections individually rather than concealing gaps behind one aggregate PASS. End a work lane when acceptance and material findings are resolved.

**Why:** long tasks accumulate differences between the original plan and what the evidence now supports.

**Example:** discovering browser microphone restrictions changes both the promise of automatic recording and the permission-denied acceptance path. Update the product assumption before implementing the old plan further.

**Common mistake:** consulting the method only at the beginning, or repeating green suites without new information. A typo correction needs no synthetic experiment. Use the [evidence record](../templates/evidence-record.md).

## 4. Matched comparisons and negative controls

**When:** a material choice has credible alternatives, or a recurring prompt/Skill/harness issue warrants comparison. A definite correctness bug usually needs a discriminating reproduction first.

**Mechanics:** declare candidates, common task/input, source versions, criteria, disqualifiers and stopping rule before trials. Identify the changed factor. For agent comparisons, hold model/effort, tools, scope, permissions and environment constant where practical. Start every independent run from the same fixture in its own workspace. Protect the grader and expected outputs from candidate edits. Calibrate it against a plausible wrong result and a legitimate valid variant. Preserve failures, timeouts, aborts and infrastructure faults, including denominator effects.

When a consequential comparison cannot run, record the actual reason, evidence-based provisional choice, a result that would overturn it, and the next feasible check.

**Why:** success after changing guidance may also reflect extra context, repaired infrastructure or another attempt.

**Illustrative example, not a trial performed here:** compare immediate repair with reproduce-first guidance on a duplicate-export bug. A negative control changes only the success message while leaving duplicate requests. Both disabling the button and request deduplication can be valid repairs under the same contract.

**Common mistake:** calling sequential edits in one directory independent trials, changing the grader after seeing a failure, or retaining only the best run. Use the [comparison protocol](../templates/comparison-protocol.md).

## 5. Delegate bounded work and reconcile it

**When:** independent exploration, research, implementation or review can improve speed or confidence. Keep dependent work sequential.

**Mechanics:** discover actual available roles. Supply a goal, raw sources, constraints, ownership and completion condition. Writers receive explicit files/modules and the warning that others share the workspace; research and review remain read-only. Preserve the user's selected main model and effort. Choose routine subtask settings from current capability/cost controls without pinning model families or claiming unmeasured savings. The parent checks returned evidence, resolves disagreement, integrates and verifies.

**Why:** concurrency reduces independent waiting; it does not resolve conflicting edits or validate conclusions.

**Example:** one worker owns CSV serialization, another researches browser encoding read-only, and the parent owns download integration.

**Common mistake:** assigning “review everything” without a boundary, treating a completion message as acceptance, or using a desktop operator for shell work. Use the [worker packet](../templates/worker-task.md).

## 6. Give independent reviewers facts, not a verdict

**When:** substantive code, consequential plans and authority/data boundaries.

**Mechanics:** use a fresh reviewer without implementation chat history where supported. Provide the user outcome, necessary product requirements, current sources/diff, raw evidence and rubric. Leave preferred winners, previous verdicts and the author's suspected defect out of the initial discovery pass. Reproduce or inspect findings against the owning source; fix confirmed issues, explain evidence-backed disagreement, and rerun affected checks. A recheck by the same reviewer is a follow-up, not another independent trial.

**Why:** this reduces anchoring while retaining the information required to judge behavior.

**Example:** review an export that must exclude unauthorized records by providing the permission contract and diff, rather than telling the reviewer where the author expects a vulnerability.

**Common mistake:** changing the role name while sharing all history, marking review complete before results arrive, or hiding product requirements in the name of blindness. If review is unavailable, label self-review, independent review NOT RUN and the remaining gap; preserve stricter project gates. Use the [review brief](../templates/review-brief.md).

## 7. Reproduce the fault and repair its cause

**When:** new production behavior, bugs and substantive refactors. Configuration/environment repairs use native validation and the original failing operation.

**Mechanics:** capture expected/actual behavior, smallest input, runtime/revision and real exit status. Distinguish application faults from toolchain, network, permission and missing-service failures. State each hypothesis, its prediction and a falsifier; choose a small discriminating experiment. For bugs/new behavior, observe a meaningful red test caused by the target behavior, implement a cohesive fix, run green and then refactor if useful. A covered pure refactor keeps existing tests green without manufacturing failure.

Use the existing project's style, types, error contracts and commands. Report coverage only when measured, with scope; the configured 80% target applies to supported new production behavior and does not establish correctness by itself.

**Why:** changing several guesses together loses causal information, and tests that copy implementation formulas cannot independently constrain it.

**Example:** reproduce missing end-date records with boundary timestamps before deciding which timezone conversion layer needs repair.

**Common mistake:** rerunning until a flaky check passes, skipping tests to obtain green, or interpreting unavailable build dependencies as a business-logic defect. Use the [debug record](../templates/debug-record.md).

## 8. Verify at the boundary of the claim

**When:** after meaningful changes, after review fixes and before completion.

**Mechanics:** run required and relevant project checks. Preserve the command's own exit status before formatting logs. Distinguish baseline failures, new failures, skipped cases, timeouts and unavailable commands. Execute changed interactive flows in a real browser when available. A service/storage claim needs evidence at that real boundary. Render visual artifacts and inspect their contents, dimensions and overflow. Validate configuration using native parsers and actual runtime capability checks. Inspect staged, unstaged and untracked work and the appropriate base diff.

**Why:** evidence types support different conclusions.

| Evidence | Supports | Remaining boundary |
| --- | --- | --- |
| Unit test/mock | Local logic under controlled conditions | Actual external system |
| Build/type/lint | Build and static constraints | User behavior, readability and preference |
| Real browser operation | Executed flow under tested conditions | Untested devices, WAN and human value |
| Render inspection | Viewed artifact's layout/content | Reader comprehension and distribution |
| Agent rubric review | Model judgment against the rubric | Human study and general quality improvement |
| Real participant comparison | Observations for sampled people and conditions | Other populations/tasks |

**Example:** click download, wait for the request, inspect file bytes/content, and reopen the page to check restored state. A success toast leaves the file unverified.

**Common mistake:** using a formatter's zero exit as the underlying command's result, saving but never viewing a screenshot, or treating parsed TOML as proof that a server loaded in the current session.

## 9. Handoffs, compaction and execution location

**When:** long-task phase changes, bulky context or work spanning local/WSL/remote environments.

**Mechanics:** keep a concise note in existing task storage: objective, latest constraints, decisions and reasons, ownership/changed files, checks and failure history, active processes, blockers and one next action. Use only compaction controls the client actually supports. On resume, recheck unfinished state rather than restarting completed work.

Use the toolchain in the repository's chosen environment. Windows access to WSL files does not make Windows Node appropriate. Remote work needs a real matching environment, scoped authorization, minimal input allowlist or exact Git base/patch, and resource/network/output contracts. Check returned scope and run relevant local acceptance; remote success messages are inputs, not final acceptance.

**Why:** continuity needs the reasons for the next step, not every raw log or private state file.

**Example:** at research-to-implementation handoff, preserve source versions, choice rationale and acceptance. For a Linux project, run checks with an explicit distribution and directory, and identify Windows-to-WSL bridge verification accurately.

**Common mistake:** treating compaction as an authorization reset, assuming an installed cloud tool means a ready environment, or uploading an entire home directory. Use the [handoff](../templates/handoff.md).

## 10. Turn evidence into public material

**When:** transforming real work into articles, tutorials, posts, presentations or team runbooks.

**Mechanics:** select material permitted for public use, then extract one supported claim, reader question, limits and actionable step. Adapt structure to the medium while retaining the author's confirmed voice. Keep actual source links/read versions. Classify observed results, replays, illustrations, inferences and proposals. Use selected screenshots/code/log excerpts and review redaction. Drafting, uploading and publishing have distinct states and authorization.

**Why:** changing presentation should preserve what the evidence supports.

**Example:** “I extracted a recurring export check into a Skill” needs actual rule/artifact evidence. A neutral demonstration is labeled as a replay. The same procedure can become an internal operational guide without a social-media format.

**Common mistake:** inventing first-person experiences, turning model preferences into user feedback, or treating a finished draft as permission to post. Use the [public claim record](../templates/public-claim.md).

## A complete cross-project example

This is illustrative, not a newly executed trial. For “fix report-export date filtering,” read rules/state/CI and define end-date inclusion. Check the current date-library contract; identify timezone hypotheses. Observe a failing boundary test, then repair the appropriate layer. If useful, delegate read-only UI date-transfer inspection while the parent owns the service change. Request fresh review against the contract, current source/diff and raw checks. Reconcile findings, run affected checks and an actual browser download, inspect file contents and data provenance, then deliver changes with gaps and a resumable note. Publishing, pushing and deployment remain subject to their scoped authorization. Without the real data service, report controlled tests and the verified front-end portion precisely.
