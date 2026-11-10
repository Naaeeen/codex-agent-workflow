import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import improvement_bundle as bundle


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def protocol(document):
    return {key: document[key] for key in
            ("version", "hypothesis", "changed_factor", "acceptance", "artifacts", "workload", "plan", "trials")}


def specimen(root, decision="reject"):
    document = {"version": 1, "hypothesis": "A synthetic arithmetic score increases.",
                "changed_factor": "Replace synthetic constant 1 with 2; no model ran.",
                "acceptance": {"min_delta": 0.5}, "artifacts": [], "workload": [],
                "plan": [], "trials": [], "review": {}, "decision": decision}
    def artifact(identifier, content):
        data = content.encode()
        (root / (identifier + ".txt")).write_bytes(data)
        document["artifacts"].append({"id": identifier, "path": identifier + ".txt",
                                      "sha256": hashlib.sha256(data).hexdigest(), "requires": []})
        return identifier
    for name in ("base", "candidate", "grader", "environment"):
        artifact(name, "Synthetic fixture: " + name)
    for split in ("dev", "heldout", "negative"):
        case = split + "-case"
        artifact(case, "Synthetic " + case)
        document["workload"].append({"id": case, "split": split, "fixture": case})
        document["plan"].append({"id": split + "-trial", "case": case})
        trial = {"id": split + "-trial", "case": case}
        for arm, source, score in (("baseline", "base", 1), ("candidate", "candidate", 2)):
            result_id = artifact(split + "-" + arm, "Synthetic retained result: " + arm)
            trial[arm] = {"bindings": {"source": source, "fixture": case, "grader": "grader",
                                       "environment": "environment"},
                          "result": {"status": "pass", "score": score, "evidence": result_id}}
        document["trials"].append(trial)
    artifact("review", "Synthetic review fixture only; not a real independent review.")
    document["review"] = {"evidence": "review", "independent": True, "supports": decision,
                           "bindings": {}, "protocol_sha256": ""}
    refresh_review(document)
    return document


def refresh_review(document):
    review = document["review"]
    review["bindings"] = {item["id"]: item["sha256"] for item in document["artifacts"]
                          if item["id"] != review["evidence"]}
    review["protocol_sha256"] = digest(protocol(document))


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.document = specimen(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def check(self):
        (self.root / "improvement.json").write_text(json.dumps(self.document), encoding="utf-8")
        return bundle.validate(self.root)

    def assertDefect(self, code):
        result = self.check()
        self.assertEqual(result["status"], "contract_invalid")
        self.assertIn(code, result["defects"])
        self.assertEqual(set(result), {"status", "defects"})

    def test_valid_reject(self):
        self.assertEqual(self.check(), {"status": "contract_valid", "defects": []})

    def test_valid_adopt_and_defer(self):
        for decision in ("adopt", "defer"):
            self.document["decision"] = decision
            self.document["review"]["supports"] = decision
            self.assertEqual(self.check()["status"], "contract_valid")

    def test_tampered_source_and_grader(self):
        for name in ("base", "grader"):
            path = self.root / (name + ".txt")
            old = path.read_bytes()
            path.write_bytes(b"tampered")
            self.assertDefect("ARTIFACT_HASH")
            path.write_bytes(old)

    def test_missing_or_duplicate_trial(self):
        trial = self.document["trials"].pop()
        self.assertDefect("TRIAL_SET")
        self.document["trials"].extend([trial, copy.deepcopy(trial)])
        self.assertDefect("DUPLICATE_ID")

    def test_failed_unknown_aborted_results_retained_for_reject(self):
        for status in ("fail", "unknown", "aborted", "error", "not-run"):
            arm = self.document["trials"][0]["candidate"]
            arm["result"].update(status=status, score=None)
            refresh_review(self.document)
            self.assertEqual(self.check()["status"], "contract_valid")
        del arm["result"]["evidence"]
        self.assertDefect("SCHEMA")

    def test_missing_failed_arm_is_invalid(self):
        del self.document["trials"][0]["candidate"]
        self.assertDefect("SCHEMA")

    def test_reviewer_stale_on_protocol_and_artifact(self):
        self.document["hypothesis"] += " Changed."
        self.assertDefect("REVIEW_PROTOCOL")
        refresh_review(self.document)
        artifact = self.document["artifacts"][0]
        data = b"new source"
        (self.root / artifact["path"]).write_bytes(data)
        artifact["sha256"] = hashlib.sha256(data).hexdigest()
        self.assertDefect("REVIEW_BINDINGS")

    def test_wrong_adopt_for_failed_or_unknown_result(self):
        self.document["decision"] = self.document["review"]["supports"] = "adopt"
        for status in ("fail", "unknown"):
            self.document["trials"][1]["candidate"]["result"].update(status=status, score=None)
            refresh_review(self.document)
            self.assertDefect("ADOPT_RESULTS")

    def test_wrong_adopt_insufficient_delta_or_review(self):
        self.document["decision"] = self.document["review"]["supports"] = "adopt"
        self.document["trials"][1]["candidate"]["result"]["score"] = 1
        refresh_review(self.document)
        self.assertDefect("ADOPT_DELTA")
        self.document["review"]["independent"] = False
        self.assertDefect("ADOPT_REVIEW")

    def test_missing_heldout_negative_and_unplanned_case(self):
        self.document["decision"] = self.document["review"]["supports"] = "adopt"
        self.document["workload"][1]["split"] = "dev"
        refresh_review(self.document)
        self.assertDefect("SPLIT_COVERAGE")
        self.document["workload"][1]["split"] = "heldout"
        self.document["plan"][0]["case"] = "absent"
        self.assertDefect("REFERENCE")

    def without_heldout(self):
        self.document["workload"] = [c for c in self.document["workload"] if c["split"] != "heldout"]
        for key in ("plan", "trials"):
            self.document[key] = [t for t in self.document[key] if t["case"] != "heldout-case"]
        refresh_review(self.document)

    def test_defer_without_heldout_is_valid(self):
        self.document["decision"] = self.document["review"]["supports"] = "defer"
        self.without_heldout()
        self.assertEqual(self.check(), {"status": "contract_valid", "defects": []})

    def test_same_bundle_cannot_adopt_without_heldout(self):
        self.without_heldout()
        self.document["decision"] = self.document["review"]["supports"] = "adopt"
        self.assertDefect("SPLIT_COVERAGE")

    def test_arm_matching(self):
        for role in ("fixture", "grader", "environment"):
            with self.subTest(role=role):
                bindings = self.document["trials"][0]["candidate"]["bindings"]
                old = bindings[role]
                bindings[role] = "base"
                self.assertDefect("ARM_BINDINGS")
                bindings[role] = old

    def test_heldout_fixture_cannot_be_dev_fixture(self):
        self.document["workload"][1]["fixture"] = self.document["workload"][0]["fixture"]
        self.assertDefect("SPLIT_OVERLAP")

    def test_changed_dependency_declaration_stales_review(self):
        self.document["artifacts"][0]["requires"] = ["grader"]
        self.assertDefect("REVIEW_PROTOCOL")

    def test_dependency_unknown_and_cycle(self):
        self.document["artifacts"][0]["requires"] = ["undeclared"]
        self.assertDefect("REFERENCE")
        self.document["artifacts"][0]["requires"] = ["base"]
        self.assertDefect("DEPENDENCY_CYCLE")

    def test_escape_absolute_unc_and_metadata(self):
        for path in ("../outside.txt", str(self.root / "base.txt"),
                     "\\\\server\\share\\file", "improvement.json", "base.txt:stream"):
            self.document["artifacts"][0]["path"] = path
            self.assertDefect("ARTIFACT_PATH")

    def test_hardlink_rejected(self):
        source = self.root / "base.txt"
        linked = self.root / "linked.txt"
        os.link(source, linked)
        self.assertDefect("ARTIFACT_PATH")
        linked.unlink()

    def test_symlink_rejected_when_available(self):
        source = self.root / "base.txt"
        linked = self.root / "linked.txt"
        try:
            linked.symlink_to(source)
        except OSError as error:
            self.skipTest("OS disallows symlink creation: " + str(error.winerror))
        self.document["artifacts"][0]["path"] = "linked.txt"
        self.assertDefect("ARTIFACT_PATH")
        linked.unlink()

    @unittest.skipUnless(sys.platform == "win32", "Windows junction test")
    def test_directory_junction_rejected(self):
        import _winapi
        junction = self.root / "junction"
        try:
            _winapi.CreateJunction(str(self.root), str(junction))
            self.document["artifacts"][0]["path"] = "junction/base.txt"
            self.assertDefect("ARTIFACT_PATH")
        finally:
            if junction.exists():
                junction.rmdir()

    def test_duplicate_json_keys(self):
        (self.root / "improvement.json").write_text('{"version":1,"version":1}')
        self.assertEqual(bundle.validate(self.root)["status"], "contract_invalid")

    def test_cli_only_status_and_codes_and_no_writes(self):
        self.check()
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        run = subprocess.run([sys.executable, str(Path(bundle.__file__)), str(self.root)],
                             capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), {"status": "contract_valid", "defects": []})
        self.assertEqual(run.stderr, "")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_malformed_input_does_not_leak(self):
        self.document["acceptance"]["min_delta"] = "PRIVATE-CONTENT"
        self.assertNotIn("PRIVATE", json.dumps(self.check()))

    def test_cli_missing_helper_does_not_leak(self):
        run = subprocess.run([sys.executable, "-I", str(Path(bundle.__file__)), str(self.root)],
                             capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout), {"status": "contract_invalid",
                                                 "defects": ["HELPER_UNAVAILABLE"]})
        self.assertEqual(run.stderr, "")

    def test_cli_argument_and_invalid_input_errors(self):
        for args, code in (([], "ARGUMENTS"), ([str(self.root)], "INPUT_INVALID")):
            run = subprocess.run([sys.executable, str(Path(bundle.__file__)), *args],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stdout), {"status": "contract_invalid", "defects": [code]})
            self.assertEqual(run.stderr, "")


if __name__ == "__main__":
    unittest.main()
