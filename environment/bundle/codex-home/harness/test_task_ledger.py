"""Behavioral checks for the offline task evidence ledger (Python stdlib only)."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import task_ledger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.task = self.root / "task"
        self.spec = self.root / "checks.json"
        self.spec.write_text(json.dumps([
            {"id": "test", "description": "Test report", "required": True, "type": "artifact"},
            {"id": "review", "description": "Review report", "required": True, "type": "review"},
        ]), encoding="utf-8")
        self.artifact = self.workspace / "report.txt"
        self.artifact.write_text("verified result", encoding="utf-8")

    def cli(self, *args, code=0):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = task_ledger.main(list(map(str, args)))
        self.assertEqual(code, result, err.getvalue() or out.getvalue())
        return json.loads(out.getvalue() if result == 0 else err.getvalue())

    def init(self):
        return self.cli("init", "--task-dir", self.task, "--workspace", self.workspace,
                        "--objective", "A checked local result", "--checks", self.spec)

    def record(self, check="test", result="pass", **kwargs):
        args = ["record", "--task-dir", self.task, "--check", check, "--result", result]
        if kwargs.pop("artifact", True):
            args.extend(["--artifact", self.artifact])
        args.extend(["--note", "Observed evidence"])
        if "revision" in kwargs:
            args.extend(["--expected-revision", kwargs["revision"]])
        return self.cli(*args, code=kwargs.get("code", 0))

    def complete(self, code=0):
        return self.cli("complete", "--task-dir", self.task, code=code)

    def test_lifecycle_and_resume_preserve_fixed_workspace_and_history(self):
        initial = self.init()
        self.assertEqual(str(self.workspace), initial["workspace"])
        self.assertEqual(1, initial["revision"])
        self.assertEqual(["test", "review"], initial["missing"])
        self.record()
        self.record("review")
        self.cli("checkpoint", "--task-dir", self.task, "--next-action", "Inspect final result",
                 "--note", "Ready for closure")
        resumed = self.cli("resume", "--task-dir", self.task)
        self.assertEqual("Inspect final result", resumed["next_action"])
        self.assertTrue(resumed["ready_to_complete"])
        self.assertEqual("complete", self.complete()["status"])
        self.assertEqual(5, self.cli("status", "--task-dir", self.task)["revision"])

    def test_no_required_review_never_completes(self):
        self.spec.write_text(json.dumps([
            {"id": "test", "description": "Test", "required": True, "type": "artifact"}
        ]), encoding="utf-8")
        self.init()
        self.record()
        self.assertIn("required review", self.complete(code=2)["error"])

    def test_changed_or_deleted_artifact_is_stale_and_cannot_complete(self):
        self.init()
        self.record()
        self.record("review")
        self.artifact.write_text("changed evidence", encoding="utf-8")
        status = self.cli("status", "--task-dir", self.task)
        self.assertEqual(["test", "review"], status["stale"])
        self.complete(code=2)
        self.artifact.unlink()
        self.assertEqual(["test", "review"], self.cli("resume", "--task-dir", self.task)["stale"])

    def test_failed_not_run_missing_and_failed_history_stay_visible(self):
        self.init()
        self.record(result="fail", artifact=False)
        failed = self.cli("status", "--task-dir", self.task)
        self.assertEqual(["test"], failed["failed"])
        self.complete(code=2)
        self.record(result="not-run", artifact=False)
        self.assertEqual(["test"], self.cli("status", "--task-dir", self.task)["not_run"])
        self.complete(code=2)
        self.record()
        self.record("review")
        completed = self.complete()
        self.assertEqual(1, len(completed["failure_history"]))
        self.assertEqual("fail", completed["failure_history"][0]["result"])
        self.assertIn("not-run", [e.get("result") for e in completed["events"]])

    def test_pass_requires_artifact_and_unknown_check_fails(self):
        self.init()
        self.record(artifact=False, code=2)
        self.record(check="unknown", code=2)
        self.assertEqual(1, self.cli("status", "--task-dir", self.task)["revision"])

    def test_outside_scope_and_hardlink_are_rejected(self):
        self.init()
        outsider = self.root / "outside.txt"
        outsider.write_text("outside", encoding="utf-8")
        self.cli("record", "--task-dir", self.task, "--check", "test", "--result", "pass",
                 "--artifact", outsider, code=2)
        link = self.workspace / "hardlink.txt"
        os.link(self.artifact, link)
        self.cli("record", "--task-dir", self.task, "--check", "test", "--result", "pass",
                 "--artifact", link, code=2)

    def test_artifact_inside_task_directory_is_accepted(self):
        self.init()
        report = self.task / "review.txt"
        report.write_text("review findings", encoding="utf-8")
        result = self.cli("record", "--task-dir", self.task, "--check", "review", "--result",
                          "pass", "--artifact", report)
        self.assertEqual("pass", result["checks"][1]["state"])

    def test_junction_or_symlink_directory_is_rejected(self):
        self.init()
        alias = self.workspace / "alias"
        if os.name == "nt":
            # Junction creation needs no elevated symlink privilege on Windows.
            command = f'New-Item -ItemType Junction -Path "{alias}" -Target "{self.workspace}" | Out-Null'
            result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr.decode(errors="replace"))
            self.addCleanup(lambda: os.rmdir(alias) if alias.exists() else None)
        else:
            alias.symlink_to(self.workspace, target_is_directory=True)
        self.cli("record", "--task-dir", self.task, "--check", "test", "--result", "pass",
                 "--artifact", alias / self.artifact.name, code=2)

    def test_revision_conflict_and_lock_preserve_state(self):
        self.init()
        self.record(revision=1)
        self.record("review", revision=1, code=2)
        lock = self.task / ".ledger.lock"
        lock.write_text("other writer", encoding="utf-8")
        self.record("review", code=2)
        lock.unlink()
        self.assertEqual(2, self.cli("status", "--task-dir", self.task)["revision"])

    def test_init_never_overwrites_and_corrupt_state_fails_closed(self):
        self.init()
        before = (self.task / "state.json").read_bytes()
        self.cli("init", "--task-dir", self.task, "--workspace", self.workspace,
                 "--objective", "overwrite", "--checks", self.spec, code=2)
        self.assertEqual(before, (self.task / "state.json").read_bytes())
        (self.task / "state.json").write_text('{"status":"complete"}', encoding="utf-8")
        self.cli("status", "--task-dir", self.task, code=2)
        self.complete(code=2)

    def test_invalid_specs_and_missing_workspace_are_rejected(self):
        self.spec.write_text('[{"id":"x","required":"yes","type":"artifact"}]', encoding="utf-8")
        self.cli("init", "--task-dir", self.task, "--workspace", self.workspace,
                 "--objective", "invalid", "--checks", self.spec, code=2)
        self.assertFalse((self.task / "state.json").exists())
        self.cli("init", "--task-dir", self.task, "--workspace", self.root / "missing",
                 "--objective", "invalid", "--checks", self.spec, code=2)

    def test_state_cannot_be_used_as_evidence(self):
        self.init()
        self.cli("record", "--task-dir", self.task, "--check", "test", "--result", "pass",
                 "--artifact", self.task / "state.json", code=2)

    def test_two_processes_cannot_commit_the_same_expected_revision(self):
        self.init()
        command = [sys.executable, str(Path(task_ledger.__file__)), "record", "--task-dir", str(self.task),
                   "--check", "test", "--result", "pass", "--artifact", str(self.artifact),
                   "--expected-revision", "1"]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        results = [process.communicate(timeout=15) for process in processes]
        self.assertEqual([0, 2], sorted(p.returncode for p in processes), results)
        status = self.cli("status", "--task-dir", self.task)
        self.assertEqual(2, status["revision"])
        self.assertEqual(2, len(status["events"]))

    def test_failed_atomic_replace_preserves_prior_state_and_releases_lock(self):
        self.init()
        before = (self.task / "state.json").read_bytes()
        with patch.object(task_ledger.os, "replace", side_effect=OSError("simulated disk error")):
            self.record(code=2)
        self.assertEqual(before, (self.task / "state.json").read_bytes())
        self.assertFalse((self.task / ".ledger.lock").exists())
        self.assertEqual([], list(self.task.glob(".ledger-tmp-*")))
        self.record()

    def test_event_limit_refuses_to_truncate_history(self):
        self.init()
        with patch.object(task_ledger, "MAX_EVENTS", 2):
            self.record(result="fail", artifact=False)
            self.record(code=2)
        status = self.cli("status", "--task-dir", self.task)
        self.assertEqual(2, status["revision"])
        self.assertEqual(1, len(status["failure_history"]))

    def test_duplicate_json_keys_and_oversized_state_fail_closed(self):
        self.init()
        state_file = self.task / "state.json"
        state_file.write_text('{"version":1,"version":1}', encoding="utf-8")
        self.cli("status", "--task-dir", self.task, code=2)
        state_file.write_bytes(b" " * (task_ledger.MAX_STATE_BYTES + 1))
        self.cli("resume", "--task-dir", self.task, code=2)

    def test_malformed_json_fails_and_relative_artifact_uses_fixed_workspace(self):
        self.init()
        result = self.cli("record", "--task-dir", self.task, "--check", "test", "--result",
                          "pass", "--artifact", self.artifact.name)
        self.assertEqual(str(self.artifact), result["checks"][0]["record"]["artifact"]["path"])
        (self.task / "state.json").write_text('{"broken":', encoding="utf-8")
        self.assertIn("Invalid JSON", self.cli("status", "--task-dir", self.task, code=2)["error"])

    def test_replaced_state_hardlink_is_rejected(self):
        self.init()
        os.link(self.task / "state.json", self.root / "state-alias.json")
        self.cli("status", "--task-dir", self.task, code=2)

    def test_oversized_artifact_fails_before_recording_a_pass(self):
        self.init()
        with self.artifact.open("wb") as stream:
            stream.truncate(task_ledger.MAX_ARTIFACT_BYTES + 1)
        error = self.record(code=2)
        self.assertIn("size limit", error["error"])
        self.assertEqual(["test", "review"], self.cli("status", "--task-dir", self.task)["missing"])

    def test_optional_failed_check_does_not_block_required_evidence(self):
        specs = json.loads(self.spec.read_text(encoding="utf-8"))
        specs.append({"id": "optional", "description": "Optional experiment", "required": False, "type": "artifact"})
        self.spec.write_text(json.dumps(specs), encoding="utf-8")
        self.init()
        self.record()
        self.record("review")
        self.record("optional", result="fail", artifact=False)
        summary = self.complete()
        self.assertEqual("fail", summary["checks"][2]["state"])
        self.assertEqual(1, len(summary["failure_history"]))


if __name__ == "__main__":
    unittest.main()
