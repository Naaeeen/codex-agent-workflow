"""Behavior tests for the local, standard-library study record CLI."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "study_progress.py"
MODULE_SPEC = importlib.util.spec_from_file_location("study_progress", SCRIPT)
PROGRESS = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(PROGRESS)


class StudyProgressTests(unittest.TestCase):
    def setUp(self):
        # Keep fixtures in this writable workspace, including in restricted Windows hosts.
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "Learning workspace 学习"
        self.workspace.mkdir()
        self.study = self.workspace / "study"

    def cli(self, *args, expected=0):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--workspace", str(self.workspace), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=self.root,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def event(self, **changes):
        event = {
            "topic_id": "T01",
            "question": {
                "file": "materials/试卷.pdf",
                "page": 2,
                "id": "Problem 1",
                "section": "Part A",
                "answer_file": "materials/官方答案.pdf",
                "answer_page": None,
            },
            "student_answer": "My actual answer: 3",
            "assessment": "correct",
            "assistance": "none",
            "evidence": "actual",
            "answer_basis": "official",
            "error_reason": None,
        }
        event.update(changes)
        return event

    def record(self, event, expected=0):
        event_file = self.root / "submitted-event.json"
        event_file.write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
        return self.cli("record", "--event-file", str(event_file), expected=expected)

    def events(self):
        return [json.loads(line) for line in (self.study / "events.jsonl").read_text(encoding="utf-8").splitlines()]

    def view(self, filename):
        return (self.study / filename).read_text(encoding="utf-8")

    def test_init_creates_empty_readable_records(self):
        result = self.cli("init")
        self.assertIn("Actual attempts: 0", result.stdout)
        self.assertEqual(self.events(), [])
        self.assertIn("Not inferred", self.view("progress.md"))
        self.assertIn("No actual incorrect attempts", self.view("mistakes.md"))
        self.assertEqual(json.loads(self.view("course.json"))["schema_version"], 1)

    def test_status_is_read_only_without_initialization(self):
        result = self.cli("status")
        self.assertIn("No study record", result.stdout)
        self.assertFalse(self.study.exists())

    def test_workspace_is_required_and_never_uses_current_directory(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "init"], cwd=self.root,
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--workspace", result.stderr)
        self.assertFalse((self.root / "study").exists())

    def test_preserves_existing_profile_bytes_and_status_changes_nothing(self):
        self.study.mkdir()
        profile = b'{"schema_version": 1, "student": "private", "topics": ["original"]}\n'
        (self.study / "course.json").write_bytes(profile)
        self.cli("init")
        self.record(self.event())
        before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.study.iterdir()}
        self.cli("status")
        after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.study.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual((self.study / "course.json").read_bytes(), profile)

    def test_records_unicode_source_and_generates_identity_and_time(self):
        self.cli("init")
        self.record(self.event(student_answer="手写答案：三"))
        recorded = self.events()[0]
        self.assertTrue(recorded["event_id"])
        self.assertTrue(recorded["recorded_at"].endswith("Z"))
        self.assertEqual(recorded["student_answer"], "手写答案：三")
        self.assertEqual(recorded["question"]["answer_page"], None)
        self.assertIn("试卷.pdf", self.view("progress.md"))
        self.assertIn("Independent official-backed correct observations: 1", self.view("progress.md"))
        self.assertIn("Mastery: Not inferred", self.view("progress.md"))

    def test_assisted_answers_never_count_as_independent(self):
        self.cli("init")
        self.record(self.event(assistance="hint"))
        self.record(self.event(assistance="solution"))
        result = self.cli("status")
        self.assertIn("Actual attempts: 2", result.stdout)
        self.assertIn("Independent official-backed correct observations: 0", result.stdout)
        self.assertIn("Assisted actual attempts: 2", result.stdout)

    def test_model_or_missing_answer_reference_never_verifies_correctness(self):
        self.cli("init")
        self.record(self.event(answer_basis="model"))
        self.record(self.event(answer_basis="missing"))
        question = self.event()["question"]
        question.pop("answer_file")
        self.record(self.event(question=question))
        result = self.cli("status")
        self.assertIn("Independent official-backed correct observations: 0", result.stdout)
        self.assertIn("Unverified actual assessments: 3", result.stdout)

    def test_simulations_are_logged_but_excluded_from_real_views(self):
        self.cli("init")
        event = self.event(evidence="simulation", assessment="incorrect", student_answer="Invented answer", event_id="sim-1")
        self.record(event)
        result = self.cli("status")
        self.assertIn("Actual attempts: 0", result.stdout)
        self.assertIn("Simulation events (excluded): 1", result.stdout)
        self.assertEqual(self.events()[0]["evidence"], "simulation")
        self.assertNotIn("Invented answer", self.view("progress.md"))
        self.assertNotIn("Invented answer", self.view("mistakes.md"))
        self.assertNotIn("sim-1", self.view("mistakes.md"))

    def test_missing_actual_answer_is_rejected_without_log_changes(self):
        self.cli("init")
        before = (self.study / "events.jsonl").read_bytes()
        result = self.record(self.event(student_answer="  \n "), expected=1)
        self.assertIn("student_answer", result.stderr)
        self.assertEqual((self.study / "events.jsonl").read_bytes(), before)

    def test_repeat_supplied_id_is_rejected_without_duplicate(self):
        self.cli("init")
        self.record(self.event(event_id="attempt-1"))
        before = (self.study / "events.jsonl").read_bytes()
        result = self.record(self.event(event_id="attempt-1"), expected=1)
        self.assertIn("Duplicate event_id", result.stderr)
        self.assertEqual((self.study / "events.jsonl").read_bytes(), before)
        self.assertEqual(len(self.events()), 1)

    def test_question_sections_remain_distinct_and_mistakes_stay_open(self):
        self.cli("init")
        self.record(self.event(assessment="incorrect", student_answer="wrong in A", event_id="wrong-a"))
        question = dict(self.event()["question"], section="Part B")
        self.record(self.event(question=question, assessment="incorrect", student_answer="wrong in B", event_id="wrong-b"))
        self.record(self.event(student_answer="later correct in A"))
        progress = self.view("progress.md")
        self.assertIn("Distinct actual questions: 2", progress)
        mistakes = self.view("mistakes.md")
        self.assertIn("wrong-a", mistakes)
        self.assertIn("wrong-b", mistakes)
        self.assertIn("Part A", mistakes)
        self.assertIn("Part B", mistakes)
        self.assertIn("Error reason: Unconfirmed", mistakes)
        self.assertNotIn("Resolved", mistakes)
        self.assertNotIn("later correct in A", mistakes)

    def test_malformed_existing_log_fails_loudly_and_preserves_all_files(self):
        self.cli("init")
        self.record(self.event())
        with (self.study / "events.jsonl").open("ab") as handle:
            handle.write(b'{"broken":\n')
        before = {path.name: path.read_bytes() for path in self.study.iterdir()}
        result = self.record(self.event(), expected=1)
        self.assertIn("line 2", result.stderr)
        self.cli("init", expected=1)
        self.cli("status", expected=1)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.study.iterdir()})

    def test_rejects_invalid_enums_dates_and_question_pages(self):
        self.cli("init")
        invalid_events = [
            self.event(assessment="mastered"),
            self.event(assistance="not sure"),
            self.event(evidence="inferred"),
            self.event(answer_basis="guess"),
            self.event(review_on="2026-02-30"),
            self.event(question=dict(self.event()["question"], page=True)),
        ]
        for event in invalid_events:
            with self.subTest(event=event):
                self.record(event, expected=1)
        self.assertEqual(self.events(), [])

    def test_existing_valid_log_without_final_newline_is_not_corrupted(self):
        self.cli("init")
        self.record(self.event(event_id="first"))
        log = self.study / "events.jsonl"
        original = log.read_bytes().rstrip(b"\n")
        log.write_bytes(original)
        self.record(self.event(event_id="second"))
        self.assertTrue(log.read_bytes().startswith(original + b"\n"))
        self.assertEqual([event["event_id"] for event in self.events()], ["first", "second"])

    def test_pasted_unicode_line_separators_remain_inside_json_values(self):
        self.cli("init")
        answer = "First line\u2028second line\u2029third line"
        self.record(self.event(student_answer=answer))
        self.cli("status")
        self.record(self.event(event_id="next-attempt"))
        log_lines = (self.study / "events.jsonl").read_text(encoding="utf-8").split("\n")
        self.assertEqual(json.loads(log_lines[0])["student_answer"], answer)
        self.assertEqual(len([line for line in log_lines if line]), 2)

    def test_views_can_be_regenerated_from_the_append_only_log(self):
        self.cli("init")
        self.record(self.event(assessment="incorrect", error_reason="Used the wrong sign", feedback="Recheck line 2", review_on="2026-11-01"))
        original_log = (self.study / "events.jsonl").read_bytes()
        expected = self.view("mistakes.md")
        (self.study / "mistakes.md").write_text("stale", encoding="utf-8")
        self.cli("init")
        self.assertEqual(self.view("mistakes.md"), expected)
        self.assertEqual((self.study / "events.jsonl").read_bytes(), original_log)
        self.assertIn("Used the wrong sign", expected)
        self.assertIn("2026-11-01", expected)

    def test_view_replacement_failure_preserves_appended_event_and_recovers(self):
        self.cli("init")
        old_views = {name: (self.study / name).read_bytes() for name in ("progress.md", "mistakes.md")}
        event_file = self.root / "recoverable-event.json"
        event_file.write_text(json.dumps(self.event(event_id="recoverable", assessment="incorrect")), encoding="utf-8")
        with mock.patch.object(PROGRESS.os, "replace", side_effect=OSError("simulated replacement failure")):
            with self.assertRaisesRegex(PROGRESS.RecordError, "was appended"):
                PROGRESS.record(self.study, event_file)
        self.assertEqual([event["event_id"] for event in self.events()], ["recoverable"])
        self.assertEqual(old_views, {name: (self.study / name).read_bytes() for name in old_views})
        self.assertEqual(sorted(path.name for path in self.study.iterdir()), sorted(["course.json", "events.jsonl", "progress.md", "mistakes.md"]))
        self.cli("init")
        self.assertIn("recoverable", self.view("progress.md"))
        self.assertIn("recoverable", self.view("mistakes.md"))
        self.record(self.event(event_id="recoverable"), expected=1)


if __name__ == "__main__":
    unittest.main()
