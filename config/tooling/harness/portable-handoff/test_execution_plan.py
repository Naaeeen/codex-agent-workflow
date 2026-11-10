import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from execution_plan import plan

NOW = datetime(2026, 11, 6, 1, 0, tzinfo=timezone.utc)
TASK = {"local_ui": False, "local_private_state": False, "os": "linux",
        "remote_separable": False, "linux_reproducible": True}
CAPS = {"observed_at": "2026-11-06T01:00:00Z",
        "codex_cloud": {"available": True, "repo_match": True, "execution_authorized": True},
        "vercel": {"available": True, "execution_authorized": True}}


class ExecutionPlanTests(unittest.TestCase):
    def test_table(self):
        cases = [
            ("separable claim stays hybrid and prefers Codex", {"remote_separable": True, "os": "any"}, {}, "hybrid", "codex_cloud"),
            ("UI cannot migrate whole", {"local_ui": True}, {}, "local", None),
            ("private state only separable unit", {"local_private_state": True, "remote_separable": True}, {}, "hybrid", "codex_cloud"),
            ("Windows task cannot migrate whole", {"os": "windows"}, {}, "local", None),
            ("Linux claim alone insufficient", {"linux_reproducible": False}, {}, "local", None),
            ("mismatched Codex uses authorized Vercel", {}, {"codex_cloud": {"repo_match": False}}, "cloud", "vercel"),
            ("empty cloud and preparation-only Vercel", {}, {"codex_cloud": {"available": False, "repo_match": False}, "vercel": {"execution_authorized": False}}, "local", None),
            ("stale ready declarations do not dispatch", {}, {"observed_at": "2026-11-05T01:00:00Z"}, "local", None),
        ]
        for label, task_changes, cap_changes, route, provider in cases:
            with self.subTest(case=label):
                task, caps = copy.deepcopy(TASK), copy.deepcopy(CAPS)
                task.update(task_changes)
                for key, value in cap_changes.items():
                    if isinstance(value, dict): caps[key].update(value)
                    else: caps[key] = value
                before = copy.deepcopy((task, caps))
                result = plan(task, caps, now=NOW)
                self.assertEqual((result["route"], result["provider"]), (route, provider))
                self.assertTrue(result["advisory_only"])
                self.assertTrue(result["reasons"])
                self.assertTrue(any("grants no execution authorization" in gate for gate in result["gates"]))
                self.assertEqual((task, caps), before)

    def test_rejects_string_boolean_and_naive_timestamp(self):
        task = copy.deepcopy(TASK); task["local_ui"] = "false"
        with self.assertRaises(ValueError): plan(task, CAPS, now=NOW)
        caps = copy.deepcopy(CAPS); caps["observed_at"] = "2026-11-06T01:00:00"
        with self.assertRaises(ValueError): plan(TASK, caps, now=NOW)

    def test_cli_is_advisory_and_reads_fresh_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            caps = copy.deepcopy(CAPS)
            caps["observed_at"] = datetime.now(timezone.utc).isoformat()
            (root / "task.json").write_text(json.dumps(TASK), encoding="utf-8")
            (root / "caps.json").write_text(json.dumps(caps), encoding="utf-8")
            script = Path(__file__).with_name("execution_plan.py")
            run = subprocess.run([sys.executable, str(script), str(root / "task.json"), str(root / "caps.json")],
                                 capture_output=True, check=True, timeout=5, text=True)
            result = json.loads(run.stdout)
            self.assertEqual(result["route"], "cloud")
            self.assertEqual(result["provider"], "codex_cloud")
            self.assertTrue(result["advisory_only"])
            self.assertEqual({p.name for p in root.iterdir()}, {"task.json", "caps.json"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
