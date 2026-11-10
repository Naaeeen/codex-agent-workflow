# Good Learning - local exam sprint adaptation

Installed from [yoli-mi/good-learning](https://github.com/yoli-mi/good-learning), commit 1255c4d7f0b602901100d29d85235ad2537eec31, under its MIT license. See LICENSE and PROVENANCE.json.

This adaptation combines the upstream progressive teaching approach with OpenAI's [exam study system](https://learn.chatgpt.com/use-cases/build-exam-study-system). It is a local customization, not an official OpenAI endorsement.

- Selected default: guided practice (teach a concept/example, then practice and repair).
- Other flows: problem-first, slides-first and daily-pack; switch using ordinary language.
- A 3–7 day sprint is the initial preference; actual dates and daily hours are not assumed.
- Original slides, questions and official answers define the source boundary.
- Actual attempts, assistance, errors and review dates persist in the course workspace.
- The added Python helper records evidence and renders views; it does not grade answers.
- PDFs and mind maps are on request; no TeX/Pillow installation is required to start learning.

Use $good-learning and point it at the course workspace or its study/course.json. The workspace profile controls sources and teaching flow; progress is not stored globally in the skill folder.

See SKILL.md. Read references/progress-recording.md for the state helper. The original PDF/map helpers are retained as optional exports with their existing limitations.
