# Improving the workflow over time

[中文](evolution.md)

My suggestion is to revisit GitHub Trending, widely used projects, and new research periodically. Try promising ideas on your own tasks. A tool worth keeping should fit an actual step in the workflow; if it does not, record why and move on.

This is a procedure readers can follow. It does not start a background task, install tools, change global settings, or approve candidates automatically. Reading it does not enable an improvement service.

## Start with an observed problem

A monthly manual review is one possible cadence. A recurring failure is another useful trigger. This is a suggested habit, not a scheduled automation. Describe an observable problem first—for example, a PDF extractor reads two columns in the wrong order—then look for tools that might address it. Stars and Trending help discover candidates; task results determine adoption.

Keep a short record for each candidate:

| Field | What to record |
| --- | --- |
| Problem | Failing input, current behavior, and expected outcome |
| Source | Primary repository or paper, version actually read, and access date; pin repositories to a commit or tag |
| Fit | Where it enters the workflow and whether it overlaps with or complements existing tools |
| Cost | License, maintenance, dependencies, platform, data destinations, telemetry, permissions, and fees |
| Comparison | Baseline A, candidate B, the main changed factor, acceptance criteria, and stopping rule |
| Decision | Adopt, try within a limited scope, reject, or leave unverified; include recovery instructions |

Prefer services already connected. Choose models by current capability, cost, and task complexity. Bounded work may suit a capable cheaper model or lower reasoning effort on the same model. Avoid fixing a model name in reusable rules; record the actual model and settings when evaluating results.

## Compare in isolation

1. **Preserve the baseline.** Keep the files, versions, dependencies, and recovery copies. Inspect licenses and installation scripts. Installation and network execution must remain within current authorization.
2. **Define acceptance first.** Separate development examples from held-out acceptance cases, and include negative controls whose behavior should remain unchanged. Set cost and time limits; identify measurements that are unavailable.
3. **Calibrate the checker.** Test it against a known correct result and a plausible incorrect one. Keep the checker, expected answers, and task boundaries outside the candidate's edit scope.
4. **Run A/B from equivalent starting states.** Use separate workspaces and match inputs, permissions, model, reasoning effort, and budget. Change only the factor being studied. If that factor is the model or budget, say so. Retain failures, timeouts, and infrastructure errors.
5. **Inspect actual outputs.** Run code tests, check document order and layout, and inspect final browser state. Prose may benefit from independent review with variant labels hidden. Separate model preference from human reader feedback.
6. **Review and decide.** Give an independent reviewer the goal, raw outputs, rubric, and failed cases. Reproduce actionable findings and rerun affected checks after fixes. When independent review is unavailable, mark it NOT RUN; renaming self-review does not make it independent.

A small diagnostic can reveal clear defects. A claim of consistent benefit needs a repetition count and stopping rule chosen in advance. After a candidate changes, do not merge the previous version's results into its score.

## An example promotion gate

The following is an **unexecuted example**. Its thresholds belong to this task, not to every workflow.

> Candidate: add layout ordering to a two-column PDF extractor. A is the existing extractor; B adds only the ordering step. Use 3 development documents, 4 held-out acceptance documents, and 2 single-column regression controls. Freeze the files and checker, using manually verified reading order as the reference. Run each variant twice from clean directories, retaining failures. Adopt B for this extraction workflow only if it handles every acceptance document correctly in both runs, introduces no single-column errors, loses no text, takes no more than 1.5 times A's total runtime, and passes independent review. Otherwise reject it or keep it experimental. Passing does not establish correctness on every unseen PDF.

On adoption, record the final files and hashes, invocation path, supported scope, and recovery commands. Inspect the first real use; restore the saved baseline if a regression appears. Without held-out cases, actual execution, or a trustworthy checker, retain the unverified status. A structural validator checks that records and references are complete; it cannot prove execution or improved capability.

## What I take from Harness²

The earlier reference was **Harness² (harness squared)**. Its Google Research repository and paper, with authors from Google Cloud AI Research and other affiliations, describe proposing edits, comparing executions, composing harness changes, and retaining evidence-supported lessons. Model weights remain fixed. The repository identifies it as a research project rather than an officially supported Google product. [Repository](https://github.com/google-research/harness2) · [Paper v1, October 9, 2026](https://arxiv.org/html/2610.14224v1)

I would borrow the practice of proposing a candidate and examining execution evidence. The held-out acceptance, external checks, and recovery requirements above are this workflow's adoption conditions. Published benchmark gains do not establish gains on my tasks, and task-local self-assessment does not justify changing rules across every project.

Try tools, skills, and configuration changes freely within the authorized scope. Before making them part of everyday work, establish which task improved, what changed, what it cost, and how to recover if it fails.
