# Persistent attempt records

Use `scripts/study_progress.py` to preserve supplied attempt evidence. The helper
uses only Python's standard library. It does not compare answers, grade numerical
or written responses, infer error causes, or decide mastery.

## Commands and storage

Pass the intended workspace explicitly, before the command. These examples use
`python`; use the available Python executable for the current host.

```powershell
python scripts/study_progress.py --workspace "C:\path\to\course-workspace" init
python scripts/study_progress.py --workspace "C:\path\to\course-workspace" status
python scripts/study_progress.py --workspace "C:\path\to\course-workspace" record --event-file "C:\path\to\attempt.json"
```

Run `init` before recording. Managed files stay under `<workspace>/study/`:

| File | Role |
| --- | --- |
| `course.json` | Course profile; existing contents are preserved byte for byte. |
| `events.jsonl` | Append-only source of attempt records. |
| `progress.md` | Derived observations and actual-attempt details. |
| `mistakes.md` | Derived actual incorrect attempts, each pending explicit review. |

`init` creates missing files and regenerates the two views. Its minimal default
profile is `{"schema_version": 1, "topics": []}`; it does not replace an existing
profile or infer a topic inventory from attempts. `status` only reads and reports;
it does not create files, update views, or initialize a missing study directory.
Topic coverage and teaching plans remain separate from attempt observations.

The helper reads the supplied event JSON file even if it is outside the workspace.
Question and answer filenames are references only: it does not open those sources.
It rejects redirected study artifacts and writes no files outside `study/`.

## Event input

Save one UTF-8 JSON object for each attempt. This example describes a real answer;
use the student's actual words, including incomplete or incorrect work.

```json
{
  "event_id": "d001-part-a-problem-1-attempt-1",
  "topic_id": "T01",
  "question": {
    "file": "materials/practice-paper.pdf",
    "page": 2,
    "section": "Part A",
    "id": "Problem 1",
    "answer_file": "materials/official-solutions.pdf",
    "answer_page": null
  },
  "student_answer": "My submitted working and final answer.",
  "assessment": "incorrect",
  "assistance": "none",
  "evidence": "actual",
  "answer_basis": "official",
  "error_reason": null,
  "feedback": "The second step needs review against the supplied solution.",
  "review_on": "2026-11-01"
}
```

Required fields are `topic_id`, `question`, `student_answer`, `assessment`,
`assistance`, `evidence`, `answer_basis`, and `error_reason`. `event_id`, `feedback`,
and `review_on` are optional. Unknown fields are rejected so an unsupported
grading or mastery field cannot silently affect the record.

| Field | Accepted value and meaning |
| --- | --- |
| `question.file`, `question.id` | Nonempty strings identifying the original question. |
| `question.page` | Positive integer or `null` when unknown; never invent a page. |
| `question.section` | Optional nonempty string, or `null` when unknown. |
| `question.answer_file` | Optional official/model answer reference; nonempty string or `null`. |
| `question.answer_page` | Optional positive integer or `null`. |
| `student_answer` | String; real attempts require a nonempty answer. Preserve its original wording. |
| `assessment` | `correct`, `incorrect`, or `unverified`; supplied after assessment outside this helper. |
| `assistance` | `none`, `hint`, or `solution`; use `solution` if an answer was exposed before/during the attempt. |
| `evidence` | `actual` for a real supplied attempt; `simulation` for invented or demonstration work. |
| `answer_basis` | `official`, `model`, or `missing`. A model response is not an official solution. |
| `error_reason` | Confirmed reason as a nonempty string, or `null` to retain `Unconfirmed`. The helper does not confirm a supplied reason. |
| `feedback` | Optional nonempty string or `null`; feedback is recorded without making it a verified diagnosis. |
| `review_on` | Optional ISO date `YYYY-MM-DD`, or `null`; it schedules no notification. |
| `event_id` | Optional unique 1-128 character identifier: letters, digits, `.`, `_`, `:`, or `-`. |

The helper generates a UUID when `event_id` is omitted and always generates its
own UTC `recorded_at` timestamp. A supplied `recorded_at` is rejected. Repeat
submissions with the same `event_id` are rejected without appending; keep a stable
ID when retrying an uncertain submission. An omitted ID cannot deduplicate a retry.

## Interpretation rules

An independent correct observation requires all of the following supplied facts:

- A real `actual` attempt with a nonempty student answer.
- `assessment: "correct"`.
- `assistance: "none"`.
- `answer_basis: "official"` and a nonempty `question.answer_file`.

These counts report recorded evidence, not independent verification by the helper.
Check the official source before assigning `official`. Unknown answer pages remain
unknown. Correct answers backed only by a model, missing sources, or a missing
answer-file reference remain unverified. Hinted and solution-exposed answers never
count as independent. Even repeated unaided official-backed correct observations
do not automatically mark a topic as mastered.

Simulations remain explicitly tagged in `events.jsonl`; they contribute only to
the excluded-simulation count. Their answers never appear among actual progress
details or real mistakes. Never enter hypothetical answers as `actual` merely to
populate a view.

Question identity uses the original file, section, and question ID together.
`Part A / Problem 1` and `Part B / Problem 1` in the same file stay distinct.
Attempts retain their own IDs and dates. Every actual recorded incorrect attempt
remains in the mistake view; a later different or correct answer does not close
it. Unknown error reasons stay unconfirmed. Full corrections, additional practice,
and any explicit human review decision belong in the course's study notes until
an explicit review workflow is implemented.

## Integrity and recovery

The helper validates the complete existing log before changing it. Malformed JSON,
invalid event schemas, blank log lines, and duplicate logged IDs fail loudly; the
log and existing profile are not replaced. Preserve the damaged file for review
instead of deleting records to make an error disappear.

Recording appends and flushes the event first, then regenerates each Markdown view
using a temporary file in `study/` and an atomic replacement. Each replacement is
atomic; the two views are not one filesystem transaction. If view generation fails
after append, the error says the event is already recorded. Run `init` to rebuild
views from the log; do not submit that attempt again. `init` also rebuilds manually
edited or stale views, so keep durable annotations outside derived files.

Use one writer at a time. This small helper does not provide concurrent-writer
locking, cryptographic provenance, source-file verification, grading, mastery
decisions, automatic mistake closure, or notifications. It cannot establish that
a submitted event describes a real student; preserve the actual interaction as
the supporting evidence.

## Local checks

```powershell
python -B -m unittest discover -s setup/skills/good-learning/tests -p test_study_progress.py -v
```

The tests use isolated temporary workspaces below the test directory, including
Chinese filenames. They check actual/simulation separation, assistance and source
bounds, duplicate IDs, malformed-log preservation, profile preservation, read-only
status, question identity, input validation, and view regeneration, including
recovery after an injected view-replacement failure. They do not
simulate real learning or measure a student's progress.
