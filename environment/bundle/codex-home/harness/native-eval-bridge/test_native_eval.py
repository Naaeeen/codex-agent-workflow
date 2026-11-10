"""Bridge integration tests: real artifact runner, injected model observer only."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from native_eval import load_dependencies, main, run_case


CANARY = "PRIVATE_PROMPT_OUTPUT_CANARY_b121"


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.dependencies = load_dependencies()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.suite = self.root / "suite"
        actual_root = self.dependencies.runner.ROOT
        shutil.copytree(actual_root, self.suite, ignore=shutil.ignore_patterns("runs", "verification", "__pycache__"))
        self.runner_patch = patch.object(self.dependencies.runner, "ROOT", self.suite)
        self.runner_patch.start()
        self.addCleanup(self.runner_patch.stop)
        self.runs = self.root / "runs"
        self.calls = []

    def tearDown(self): self.tmp.cleanup()

    def observer(self, outcome="success", scope_violation=False, mutate_receipt=False, mutate_grader=False):
        def call(config, prompt):
            self.calls.append((config, prompt))
            target = config.workspace / "README.md"
            target.write_bytes(target.read_bytes().replace(b"pakcage", b"package"))
            if scope_violation: (config.workspace / "unrequested.txt").write_text(CANARY)
            if mutate_receipt:
                receipt = config.workspace.parent / "receipt.json"
                receipt.write_text(receipt.read_text().replace('"model": null', '"model": "tampered"'))
            if mutate_grader:
                path = self.suite / "graders" / "checks.py"
                path.write_text(path.read_text() + "\n# stale\n")
            config.result_dir.mkdir()
            metadata = {"schema_version": 1, "run_id": str(uuid.uuid4()),
                        "thread_id": str(uuid.uuid4()), "outcome": outcome,
                        "success": outcome == "success", "raw_streams_saved": False}
            (config.result_dir / "metadata.json").write_text(json.dumps(metadata))
            return metadata
        return call

    def run_bridge(self, **options):
        return run_case("N1", self.runs, Path(sys.executable), dependencies=self.dependencies, **options)

    def read_json(self, result, name):
        return json.loads((Path(result["trial"]) / name).read_text())

    def test_default_only_prepares_without_execution(self):
        result = self.run_bridge(observer_call=self.observer())
        self.assertEqual(result["status"], "PREPARED")
        self.assertEqual(self.calls, [])
        self.assertEqual(self.read_json(result, "dispatch.json")["execution_requested"], False)
        self.assertFalse((Path(result["trial"]) / "observer").exists())
        self.assertIn("pakcage", (Path(result["trial"]) / "workspace" / "README.md").read_text())

    def test_success_requires_real_n1_artifact_and_preserves_receipt(self):
        result = self.run_bridge(execute=True, observer_call=self.observer(), profile="local-analysis")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["artifact_status"], "PASS")
        self.assertTrue(result["receipt_unchanged"])
        dispatch = self.read_json(result, "dispatch.json")
        self.assertEqual(dispatch["receipt_sha256"], self.dependencies.runner.digest((Path(result["trial"]) / "receipt.json").read_bytes()))
        config, prompt = self.calls[0]
        self.assertEqual(config.sandbox, "workspace-write")
        self.assertFalse(config.persistent)
        self.assertEqual(config.profile, "local-analysis")
        self.assertEqual(config.workspace, Path(result["trial"]) / "workspace")
        self.assertIn("Fix only", prompt)
        self.assertNotIn("receipt.json", prompt)
        self.assertNotIn("graders", prompt)
        self.assertIsNone(self.read_json(result, "receipt.json")["model"])

    def test_failed_observer_cannot_pass_with_correct_artifact(self):
        for index, outcome in enumerate(("timeout", "invalid_json", "turn_failed", "nonzero_exit")):
            with self.subTest(outcome=outcome):
                result = self.run_bridge(execute=True, observer_call=self.observer(outcome))
                self.assertEqual(result["artifact_status"], "PASS")
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(result["observer_outcome"], outcome)

    def test_scope_violation_fails_real_grading(self):
        result = self.run_bridge(execute=True, observer_call=self.observer(scope_violation=True))
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["artifact_status"], "FAIL")
        self.assertEqual(result["grade_summary"]["scope_status"], "FAIL")

    def test_any_receipt_mutation_invalidates_trial(self):
        result = self.run_bridge(execute=True, observer_call=self.observer(mutate_receipt=True))
        self.assertEqual(result["status"], "INVALID_TRIAL")
        self.assertFalse(result["receipt_unchanged"])

    def test_changed_grader_invalidates_trial(self):
        result = self.run_bridge(execute=True, observer_call=self.observer(mutate_grader=True))
        self.assertEqual(result["status"], "INVALID_TRIAL")
        self.assertEqual(result["artifact_status"], "INVALID_TRIAL")

    def test_unknown_case_and_implicit_execution_values_rejected(self):
        with self.assertRaises(ValueError):
            run_case("UNKNOWN", self.runs, Path(sys.executable), dependencies=self.dependencies)
        with self.assertRaises(ValueError): self.run_bridge(execute="yes")
        self.assertFalse(self.runs.exists())

    def test_metadata_projection_drops_grader_output_and_final_answer(self):
        prompt_file = self.suite / "prompts" / "N1.txt"
        prompt_file.write_text(prompt_file.read_text() + "\n" + CANARY)
        real_grade = self.dependencies.runner.grade
        def grade(trial):
            result = real_grade(trial)
            result["final_answer"] = {"value": CANARY}
            result["checks"][0]["details"] = {"stdout": CANARY, "stderr": CANARY}
            return result
        with patch.object(self.dependencies.runner, "grade", side_effect=grade):
            result = self.run_bridge(execute=True, observer_call=self.observer())
        for name in ("dispatch.json", "evaluation.json"):
            self.assertNotIn(CANARY, (Path(result["trial"]) / name).read_text())
        self.assertEqual(result["status"], "PASS")

    def test_observer_success_does_not_replace_artifact_grading(self):
        fixed = self.observer()
        def no_artifact(config, prompt):
            original = (config.workspace / "README.md").read_bytes()
            metadata = fixed(config, prompt)
            (config.workspace / "README.md").write_bytes(original)
            return metadata
        result = self.run_bridge(execute=True, observer_call=no_artifact)
        self.assertEqual(result["observer_outcome"], "success")
        self.assertEqual(result["artifact_status"], "FAIL")
        self.assertEqual(result["status"], "FAIL")

    def test_missing_observer_metadata_cannot_pass(self):
        fixed = self.observer()
        def missing(config, prompt):
            metadata = fixed(config, prompt)
            (config.result_dir / "metadata.json").unlink()
            return metadata
        result = self.run_bridge(execute=True, observer_call=missing)
        self.assertEqual(result["artifact_status"], "PASS")
        self.assertEqual(result["status"], "INFRA_ERROR")

    def test_observer_exception_is_not_success(self):
        def broken(config, prompt): raise RuntimeError(CANARY)
        result = self.run_bridge(execute=True, observer_call=broken)
        self.assertEqual(result["status"], "INFRA_ERROR")
        self.assertNotIn(CANARY, json.dumps(result))

    def test_cli_default_gate(self):
        with patch("native_eval.load_dependencies", return_value=self.dependencies), patch("builtins.print") as output:
            code = main(["--case", "N1", "--runs-root", str(self.runs), "--executable", sys.executable])
        self.assertEqual(code, 0)
        result = json.loads(output.call_args.args[0])
        self.assertEqual(result["status"], "PREPARED")
        self.assertEqual(self.calls, [])


if __name__ == "__main__": unittest.main()
