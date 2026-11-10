#!/usr/bin/env python3
"""Append supplied attempt evidence and derive readable study records; never grade."""

import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid


ARTIFACTS = ("course.json", "events.jsonl", "progress.md", "mistakes.md")
REQUIRED = {
    "topic_id", "question", "student_answer", "assessment", "assistance",
    "evidence", "answer_basis", "error_reason",
}
OPTIONAL = {"event_id", "feedback", "review_on"}
ENUMS = {
    "assessment": {"correct", "incorrect", "unverified"},
    "assistance": {"none", "hint", "solution"},
    "evidence": {"actual", "simulation"},
    "answer_basis": {"official", "model", "missing"},
}


class RecordError(ValueError):
    """Invalid input or an unsafe/inconsistent record location."""


def require_text(value, label, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise RecordError(f"{label} must be a nonempty string" if not allow_empty else f"{label} must be a string")


def validate_event(event, logged=False):
    if not isinstance(event, dict):
        raise RecordError("Each event must be a JSON object")
    allowed = REQUIRED | OPTIONAL | ({"recorded_at"} if logged else set())
    missing = REQUIRED - event.keys()
    if missing:
        raise RecordError(f"Missing event fields: {', '.join(sorted(missing))}")
    unknown = event.keys() - allowed
    if unknown:
        raise RecordError(f"Unknown event fields: {', '.join(sorted(unknown))}")
    require_text(event["topic_id"], "topic_id")
    for field, choices in ENUMS.items():
        if not isinstance(event[field], str) or event[field] not in choices:
            raise RecordError(f"{field} must be one of: {', '.join(sorted(choices))}")
    require_text(event["student_answer"], "student_answer", allow_empty=event["evidence"] == "simulation")
    question = event["question"]
    if not isinstance(question, dict):
        raise RecordError("question must be an object")
    if not {"file", "page", "id"}.issubset(question):
        raise RecordError("question requires file, page (nullable), and id")
    if question.keys() - {"file", "page", "id", "section", "answer_file", "answer_page"}:
        raise RecordError("Unknown question fields")
    for field in ("file", "id"):
        require_text(question[field], f"question.{field}")
    for field in ("section", "answer_file"):
        if field in question and question[field] is not None:
            require_text(question[field], f"question.{field}")
    for field in ("page", "answer_page"):
        value = question.get(field)
        if value is not None and (type(value) is not int or value < 1):
            raise RecordError(f"question.{field} must be a positive integer or null")
    for field in ("error_reason", "feedback"):
        if event.get(field) is not None:
            require_text(event[field], field)
    if event.get("review_on") is not None:
        require_text(event["review_on"], "review_on")
        try:
            if date.fromisoformat(event["review_on"]).isoformat() != event["review_on"]:
                raise ValueError()
        except ValueError as exc:
            raise RecordError("review_on must be an ISO date (YYYY-MM-DD)") from exc
    if "event_id" in event:
        require_text(event["event_id"], "event_id")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", event["event_id"]):
            raise RecordError("event_id must contain 1-128 letters, digits, dots, underscores, colons, or hyphens")
    if logged:
        if "event_id" not in event or "recorded_at" not in event:
            raise RecordError("Logged events require event_id and recorded_at")
        require_text(event["recorded_at"], "recorded_at")
        try:
            stamp = datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError()
        except ValueError as exc:
            raise RecordError("recorded_at must be an ISO timestamp with a time zone") from exc


def study_path(workspace):
    workspace = Path(workspace).expanduser().resolve()
    if not workspace.is_dir():
        raise RecordError("--workspace must name an existing directory")
    study = workspace / "study"
    if study.is_symlink() or study.resolve().parent != workspace:
        raise RecordError("study must be a real directory inside the selected workspace")
    if study.exists() and not study.is_dir():
        raise RecordError("study exists but is not a directory")
    for name in ARTIFACTS:
        path = study / name
        if path.is_symlink() or path.resolve().parent != study.resolve():
            raise RecordError(f"Refusing redirected study artifact: {name}")
        if path.exists() and not path.is_file():
            raise RecordError(f"Study artifact is not a regular file: {name}")
    return study


def read_events(study):
    log = study / "events.jsonl"
    if not log.exists():
        return [], False
    text = log.read_text(encoding="utf-8")
    events, seen = [], set()
    # JSON Lines uses LF delimiters. Unicode paragraph separators can be valid
    # characters inside JSON strings and must not be treated as record boundaries.
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
            validate_event(event, logged=True)
            if event["event_id"] in seen:
                raise RecordError(f"Duplicate event_id: {event['event_id']}")
        except (ValueError, TypeError) as exc:
            raise RecordError(f"Invalid events.jsonl at line {number}: {exc}. Log preserved.") from exc
        events.append(event)
        seen.add(event["event_id"])
    return events, bool(text) and not text.endswith("\n")


def has_official_reference(event):
    return event["answer_basis"] == "official" and bool(event["question"].get("answer_file"))


def is_independent_correct(event):
    return (
        event["evidence"] == "actual" and event["assessment"] == "correct"
        and event["assistance"] == "none" and has_official_reference(event)
    )


def question_identity(event):
    question = event["question"]
    return question["file"], question.get("section") or "", question["id"]


def summary(events):
    actual = [event for event in events if event["evidence"] == "actual"]
    return {
        "Actual attempts": len(actual),
        "Distinct actual questions": len({question_identity(event) for event in actual}),
        "Independent official-backed correct observations": sum(is_independent_correct(event) for event in actual),
        "Assisted actual attempts": sum(event["assistance"] != "none" for event in actual),
        "Recorded incorrect attempts": sum(event["assessment"] == "incorrect" for event in actual),
        "Unverified actual assessments": sum(event["assessment"] == "unverified" or not has_official_reference(event) for event in actual),
        "Simulation events (excluded)": len(events) - len(actual),
    }


def summary_text(events):
    return "\n".join(f"{label}: {count}" for label, count in summary(events).items()) + "\nMastery: Not inferred."


def inline(value):
    value = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = re.sub(r"([\\`*_\[\]|])", r"\\\1", value)
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def answer_block(value):
    runs = [len(match.group()) for match in re.finditer(r"`+", value)]
    fence = "`" * max(3, max(runs, default=0) + 1)
    return f"{fence}text\n{value}\n{fence}"


def question_label(question):
    pieces = [question["file"]]
    if question.get("section"):
        pieces.append(question["section"])
    pieces.append(question["id"])
    page = f"page {question['page']}" if question["page"] is not None else "page unknown"
    return inline(" / ".join(pieces) + f" ({page})")


def reference_label(event):
    question = event["question"]
    if not question.get("answer_file"):
        return "Not supplied"
    page = f"page {question['answer_page']}" if question.get("answer_page") is not None else "page unknown"
    return inline(f"{question['answer_file']} ({page}); basis: {event['answer_basis']}")


def render_progress(events):
    actual = [event for event in events if event["evidence"] == "actual"]
    lines = [
        "# Study progress", "", "Derived from events.jsonl. Supplied assessments and references are recorded without grading or reading source answers.",
        "", *(f"- {line}" for line in summary_text(events).splitlines()), "", "A correct observation never establishes mastery. Simulations are excluded from all actual-attempt details below.",
        "", "## Topic observations", "", "| Topic | Actual attempts | Independent official-backed correct | Recorded incorrect |",
        "| --- | ---: | ---: | ---: |",
    ]
    for topic in sorted({event["topic_id"] for event in actual}):
        observations = [event for event in actual if event["topic_id"] == topic]
        lines.append(f"| {inline(topic)} | {len(observations)} | {sum(is_independent_correct(event) for event in observations)} | {sum(event['assessment'] == 'incorrect' for event in observations)} |")
    if not actual:
        lines.extend(["", "No actual attempts recorded."])
    for event in actual:
        verification = "Official answer reference supplied" if has_official_reference(event) and event["assessment"] != "unverified" else "Unverified"
        lines.extend([
            "", f"## Attempt {inline(event['event_id'])}", "", f"- Recorded at: {inline(event['recorded_at'])}",
            f"- Topic: {inline(event['topic_id'])}", f"- Question: {question_label(event['question'])}",
            f"- Recorded assessment: {event['assessment']}", f"- Assessment evidence: {verification}",
            f"- Answer reference: {reference_label(event)}", f"- Assistance: {event['assistance']}",
            f"- Independent correct observation: {'Yes' if is_independent_correct(event) else 'No'}",
            "", "Student answer:", "", answer_block(event["student_answer"]),
        ])
        if event.get("feedback"):
            lines.extend(["", f"Feedback: {inline(event['feedback'])}"])
    return "\n".join(lines) + "\n"


def render_mistakes(events):
    mistakes = [event for event in events if event["evidence"] == "actual" and event["assessment"] == "incorrect"]
    if not mistakes:
        return "No actual incorrect attempts recorded.\n"
    lines = []
    for event in mistakes:
        lines.extend([
            f"# Attempt {inline(event['event_id'])}", "", f"- Recorded at: {inline(event['recorded_at'])}",
            f"- Topic: {inline(event['topic_id'])}", f"- Question: {question_label(event['question'])}",
            f"- Recorded assessment: incorrect; basis: {event['answer_basis']}",
            f"- Answer reference: {reference_label(event)}", f"- Assistance: {event['assistance']}",
            f"- Error reason: {inline(event['error_reason']) if event['error_reason'] else 'Unconfirmed'}",
            f"- Feedback: {inline(event['feedback']) if event.get('feedback') else 'Not supplied'}",
            f"- Review on: {event.get('review_on') or 'Not scheduled'}",
            "- Review status: Pending explicit review; later answers do not close this record.",
            "", "Student answer:", "", answer_block(event["student_answer"]), "",
        ])
    return "\n".join(lines)


def write_views(study, events):
    # Each replacement is atomic. A pair of files is not a filesystem transaction.
    for name, content in (("progress.md", render_progress(events)), ("mistakes.md", render_mistakes(events))):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=study, prefix=f".{name}.", delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, study / name)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()


def initialize(study):
    events, _ = read_events(study)  # Validate first; never conceal or replace a bad log.
    study.mkdir(exist_ok=True)
    if not (study / "course.json").exists():
        with (study / "course.json").open("x", encoding="utf-8", newline="\n") as handle:
            json.dump({"schema_version": 1, "topics": []}, handle, indent=2)
            handle.write("\n")
    if not (study / "events.jsonl").exists():
        (study / "events.jsonl").touch(exist_ok=False)
    write_views(study, events)
    print(summary_text(events))


def record(study, event_file):
    if not (study / "events.jsonl").is_file() or not (study / "course.json").is_file():
        raise RecordError("No initialized study record. Run init with the same --workspace first.")
    events, needs_newline = read_events(study)
    event = json.loads(Path(event_file).read_text(encoding="utf-8"))
    validate_event(event)
    event.setdefault("event_id", str(uuid.uuid4()))
    if any(previous["event_id"] == event["event_id"] for previous in events):
        raise RecordError(f"Duplicate event_id: {event['event_id']}. No event appended.")
    event["recorded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    with (study / "events.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        if needs_newline:
            handle.write("\n")
        handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        write_views(study, events + [event])
    except OSError as exc:
        raise RecordError(f"Event {event['event_id']} was appended, but views could not be regenerated: {exc}. Run init to regenerate; do not resubmit.") from exc
    print(f"Recorded event: {event['event_id']}")
    print(summary_text(events + [event]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Existing workspace directory; all managed files stay in its study directory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Initialize missing files or regenerate views; preserve course.json and the event log")
    commands.add_parser("status", help="Read summary without creating or changing files")
    record_parser = commands.add_parser("record", help="Append one supplied event and regenerate views")
    record_parser.add_argument("--event-file", required=True, help="UTF-8 JSON event to read; it may be outside the workspace")
    args = parser.parse_args(argv)
    try:
        study = study_path(args.workspace)
        if args.command == "init":
            initialize(study)
        elif args.command == "record":
            record(study, args.event_file)
        elif not (study / "events.jsonl").exists():
            print("No study record. Run init with this --workspace to create one.")
        else:
            events, _ = read_events(study)
            print(summary_text(events))
    except (OSError, ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
