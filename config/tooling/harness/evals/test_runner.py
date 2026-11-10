"""Behavioral tests for the local, model-free evaluation controller."""
from __future__ import annotations

import json
import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest

import runner


class RunnerContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runs = Path(self.temp.name) / "runs"

    def trial(self, case="C1"):
        return runner.prepare(case, self.runs)

    def golden(self, trial, case, variant):
        source = runner.ROOT / "golden" / case / variant
        for path in source.rglob("*"):
            if path.is_file():
                target = trial / "workspace" / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)

    def test_prepare_is_unique_and_never_resets_existing_work(self):
        a = self.trial()
        marker = a / "workspace" / "private-work.txt"
        marker.write_text("preserve", encoding="utf-8")
        b = self.trial()
        self.assertNotEqual(a, b)
        self.assertEqual(marker.read_text(), "preserve")
        self.assertTrue((a / "receipt.json").is_file())

    def test_unfinished_fixture_fails_behavior_not_infrastructure(self):
        result = runner.grade(self.trial())
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(x["name"] == "behavior" and x["status"] == "FAIL" for x in result["checks"]))

    def test_all_golden_outcomes_are_discriminating(self):
        for case in runner.load_suite()["cases"]:
            for variant in ("good", "alternative", "bad", "scope-violation"):
                with self.subTest(case=case["id"], variant=variant):
                    trial = self.trial(case["id"])
                    self.golden(trial, case["id"], variant)
                    result = runner.grade(trial)
                    expected = "PASS" if variant in ("good", "alternative") else "FAIL"
                    self.assertEqual(result["status"], expected, result)
                    if variant == "scope-violation":
                        self.assertEqual(next(x for x in result["checks"] if x["name"] == "scope")["status"], "FAIL")

    def test_changed_controller_or_fixture_is_refused(self):
        trial = self.trial()
        receipt = json.loads((trial / "receipt.json").read_text())
        receipt["trusted_hashes"]["runner.py"] = "0" * 64
        (trial / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        result = runner.grade(trial)
        self.assertEqual(result["status"], "INVALID_TRIAL")

    def test_receipt_cannot_redirect_workspace_or_controller_read(self):
        trial = self.trial()
        receipt = json.loads((trial / "receipt.json").read_text())
        receipt["trusted_hashes"]["../outside"] = "0" * 64
        (trial / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "INVALID_TRIAL")

    def test_final_answer_is_bounded_data_and_never_executes_commands(self):
        trial = self.trial("N1")
        self.golden(trial, "N1", "good")
        answer = {"summary": "Fixed.", "commands": ["write a marker"]}
        (trial / "final-answer.json").write_text(json.dumps(answer), encoding="utf-8")
        result = runner.grade(trial)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["final_answer"]["format"], "json")
        self.assertFalse((trial / "marker").exists())
        (trial / "final-answer.json").write_text("x" * (runner.MAX_FINAL_BYTES + 1), encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_malformed_final_and_two_formats_fail(self):
        trial = self.trial("N1")
        self.golden(trial, "N1", "good")
        (trial / "final-answer.json").write_text("{broken", encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")
        (trial / "final-answer.txt").write_text("done", encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_grader_exception_is_infrastructure_not_agent_failure(self):
        from unittest.mock import patch
        trial = self.trial("N1")
        with patch("runner.checks.grade_case", side_effect=RuntimeError("synthetic crash")):
            result = runner.grade(trial)
        self.assertEqual(result["status"], "INFRA_ERROR")
        self.assertEqual(result["error"], "RuntimeError")

    def test_command_fail_timeout_and_output_limit_are_distinct(self):
        from graders.checks import run_command
        self.assertEqual(run_command([sys.executable, "-c", "raise SystemExit(7)"], Path(self.temp.name), 3)["returncode"], 7)
        self.assertTrue(run_command([sys.executable, "-c", "import time; time.sleep(10)"], Path(self.temp.name), .2)["timed_out"])
        self.assertTrue(run_command([sys.executable, "-c", "print('x' * 1000000)"], Path(self.temp.name), 3)["output_limited"])

    def test_new_unallowed_file_fails_scope(self):
        trial = self.trial("N1")
        self.golden(trial, "N1", "good")
        (trial / "workspace" / "unexpected.txt").write_text("new", encoding="utf-8")
        result = runner.grade(trial)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("unexpected.txt", result["scope_changes"])

    def test_actual_fixture_and_grader_tamper_are_refused(self):
        from unittest.mock import patch
        for target in ("fixtures/N1/README.md", "graders/checks.py"):
            with self.subTest(target=target):
                copy_root = Path(self.temp.name) / ("copy-" + target.split("/")[0])
                copy_root.mkdir()
                for name in ("fixtures", "prompts", "graders"):
                    shutil.copytree(runner.ROOT / name, copy_root / name)
                for name in ("suite.json", "runner.py"):
                    shutil.copyfile(runner.ROOT / name, copy_root / name)
                with patch("runner.ROOT", copy_root):
                    trial = self.trial("N1")
                    (copy_root / target).write_text("tampered", encoding="utf-8")
                    self.assertEqual(runner.grade(trial)["status"], "INVALID_TRIAL")

    def test_workspace_hardlink_is_refused(self):
        trial = self.trial("N1")
        source = trial / "workspace/README.md"
        linked = trial / "workspace/linked.txt"
        linked.hardlink_to(source)
        self.assertEqual(runner.grade(trial)["status"], "INVALID_TRIAL")

    def test_timeout_terminates_spawned_child(self):
        from graders.checks import run_command
        marker = Path(self.temp.name) / "child-survived.txt"
        ready = Path(self.temp.name) / "child-started.txt"
        release = Path(self.temp.name) / "release.txt"
        child = ("import time,pathlib\npathlib.Path(" + repr(str(ready)) + ").write_text('started')\n"
                 "deadline=time.monotonic()+15\n"
                 "while not pathlib.Path(" + repr(str(release)) + ").exists() and time.monotonic()<deadline: time.sleep(.05)\n"
                 "if pathlib.Path(" + repr(str(release)) + ").exists(): pathlib.Path(" + repr(str(marker)) + ").write_text('survived')")
        parent = "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c'," + repr(child) + "]);time.sleep(10)"
        result = run_command([sys.executable, "-c", parent], Path(self.temp.name), .4)
        self.assertTrue(result["timed_out"])
        self.assertTrue(ready.exists(), "Child must have actually started for this check to count")
        release.write_text("release after parent timeout", encoding="utf-8")
        time.sleep(1.2)
        self.assertFalse(marker.exists())

    def test_html_wrong_schedule_labels_fail_even_with_correct_times(self):
        trial = self.trial("D1")
        self.golden(trial, "D1", "good")
        path = trial / "workspace/brief.html"
        path.write_text(path.read_text().replace("Repair session resumes", "Coffee tasting"), encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_html_active_content_is_rejected(self):
        trial = self.trial("D1")
        self.golden(trial, "D1", "good")
        path = trial / "workspace/brief.html"
        path.write_text(path.read_text().replace('<body>', '<body onload="alert(1)">'), encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_document_numbers_require_numeric_boundaries(self):
        trial = self.trial("D2")
        self.golden(trial, "D2", "good")
        path = trial / "workspace/release-notes.md"
        path.write_text(path.read_text().replace("| 12 | 0 |", "| 112 | 20 |"), encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_cli_prepare_and_grade_machine_contract(self):
        from unittest.mock import patch
        output = io.StringIO()
        with patch.object(sys, "argv", ["runner.py", "prepare", "--case", "N1", "--runs-root", str(self.runs)]), redirect_stdout(output):
            self.assertEqual(runner.main(), 0)
        prepared = json.loads(output.getvalue())
        trial = Path(prepared["trial"])
        self.golden(trial, "N1", "good")
        output = io.StringIO()
        with patch.object(sys, "argv", ["runner.py", "grade-existing", "--trial", str(trial)]), redirect_stdout(output):
            self.assertEqual(runner.main(), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "PASS")

    def test_invalid_case_returns_machine_readable_error(self):
        from unittest.mock import patch
        output = io.StringIO()
        with patch.object(sys, "argv", ["runner.py", "prepare", "--case", "../escape"]), redirect_stdout(output):
            self.assertEqual(runner.main(), 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "INFRA_ERROR")

    def test_malformed_artifact_is_failure_not_infrastructure(self):
        trial = self.trial("R1")
        self.golden(trial, "R1", "good")
        path = trial / "workspace/analysis.json"
        data = json.loads(path.read_text())
        data["sources"]["throughput"] = [{"bad": "not a source id"}]
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_unsafe_relative_paths_are_rejected(self):
        for name in ("../x", "/x", "C:/x", "a\\b", "a//b", "a/./b", ""):
            with self.subTest(name=name), self.assertRaises(runner.InvalidTrial):
                runner.safe_relative(name)

    def test_api_migration_preserves_comment_inside_editable_file(self):
        trial = self.trial("C2")
        self.golden(trial, "C2", "good")
        path = trial / "workspace/src/workflow.mjs"
        path.write_text("\n".join(line for line in path.read_text().splitlines() if "Keep this migration note" not in line), encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_html_remote_inline_css_fails(self):
        trial = self.trial("D1")
        self.golden(trial, "D1", "good")
        path = trial / "workspace/brief.html"
        path.write_text(path.read_text().replace('<body>', '<body style="background:url(https://example.test/bg.png)">'), encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_html_srcset_and_missing_attendee_facts_fail(self):
        for change in (lambda text: text.replace('</main>', '<img srcset="https://example.test/a.png 1x"></main>'),
                       lambda text: text.replace('Bring one small repairable item. All skill levels welcome.', 'No items allowed. Experts only.')):
            trial = self.trial("D1")
            self.golden(trial, "D1", "good")
            path = trial / "workspace/brief.html"
            path.write_text(change(path.read_text()), encoding="utf-8")
            self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_html_common_attendee_paraphrase_is_valid(self):
        trial = self.trial("D1")
        self.golden(trial, "D1", "good")
        path = trial / "workspace/brief.html"
        path.write_text(path.read_text().replace('Bring one small repairable item. All skill levels welcome.', 'Please bring 1 small item to repair. Everyone is welcome, including beginners.'), encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "PASS")

    def test_c3_timeout_or_output_limit_is_not_a_successful_rejection(self):
        from unittest.mock import patch
        from graders.checks import c3
        expected = ("traversal_preflight", "absolute_preflight", "partial_preflight", "collision_preflight", "no_overwrite")
        trial = self.trial("C3")
        for limited in (False, True):
            with patch("graders.checks.run_command", return_value={"returncode":1,"timed_out":not limited,"output_limited":limited}):
                result = c3(trial / "workspace")
            self.assertTrue(all(x["status"] == "FAIL" for x in result if x["name"] in expected))

    def test_early_zero_exit_cannot_skip_grader_assertions(self):
        for case, name, source in (("C1", "src/intervals.py", "raise SystemExit(0)\n"),
                                   ("C2", "src/workflow.mjs", 'process.exit(0);\n// Keep this migration note: client.legacySend("example") is old documentation.\n')):
            with self.subTest(case=case):
                trial = self.trial(case)
                (trial / "workspace" / name).write_text(source, encoding="utf-8")
                result = runner.grade(trial)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(next(item for item in result["checks"] if item["name"] == "behavior")["status"], "FAIL")

    def test_alias_check_covers_every_output_interval(self):
        trial = self.trial("C1")
        defective = '''def merge_intervals(intervals):
    if any(start > end for start, end in intervals):
        raise ValueError("reversed")
    result = []
    for pair in sorted(intervals):
        if result and pair[0] <= result[-1][1]:
            result[-1] = [result[-1][0], max(result[-1][1], pair[1])]
        else:
            result.append(list(pair) if not result else pair)
    return result
'''
        (trial / "workspace/src/intervals.py").write_text(defective, encoding="utf-8")
        self.assertEqual(runner.grade(trial)["status"], "FAIL")

    def test_python_optimization_cannot_disable_behavior_checks(self):
        from unittest.mock import patch
        trial = self.trial("C1")
        defective = 'def merge_intervals(intervals):\n    if any(a > b for a,b in intervals): raise ValueError("bad")\n    return []\n'
        (trial / "workspace/src/intervals.py").write_text(defective, encoding="utf-8")
        with patch.dict(os.environ, {"PYTHONOPTIMIZE":"1"}):
            self.assertEqual(runner.grade(trial)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
