"""Local artifact evaluation. This is not a security sandbox or a model runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import time
import uuid
from datetime import datetime, timezone

from graders import checks

ROOT = Path(__file__).resolve().parent
MAX_FINAL_BYTES = 16384
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TREE_BYTES = 128 * 1024 * 1024
MAX_FILES = 4096


class InvalidTrial(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise InvalidTrial("unsafe_relative_path")
    parts = value.split("/")
    if any(p in ("", ".", "..") for p in parts) or PurePosixPath(value).is_absolute():
        raise InvalidTrial("unsafe_relative_path")
    return value


def is_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def plain_path(path):
    path = Path(os.path.abspath(path))
    for ancestor in (path, *path.parents):
        if (ancestor.exists() or ancestor.is_symlink()) and is_link(ancestor):
            raise InvalidTrial("link_or_reparse_point")
    return path


def bounded_read(path, limit=MAX_FILE_BYTES):
    path = plain_path(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1 or info.st_size > limit:
        raise InvalidTrial("unsafe_or_oversized_file")
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise InvalidTrial("oversized_file")
    return data


def tree_hashes(root):
    root = plain_path(root)
    if not root.is_dir():
        raise InvalidTrial("missing_directory")
    result = {}
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            if is_link(Path(directory) / name):
                raise InvalidTrial("link_or_reparse_point")
        for name in files:
            path = Path(directory) / name
            relative = safe_relative(path.relative_to(root).as_posix())
            data = bounded_read(path)
            total += len(data)
            if len(result) >= MAX_FILES or total > MAX_TREE_BYTES:
                raise InvalidTrial("tree_limit_exceeded")
            result[relative] = digest(data)
    return dict(sorted(result.items()))


def load_suite():
    suite = json.loads(bounded_read(ROOT / "suite.json", 65536))
    if suite.get("version") != 1 or len(suite.get("cases", [])) != 8:
        raise InvalidTrial("unsupported_suite")
    ids = [case["id"] for case in suite["cases"]]
    if len(set(ids)) != len(ids):
        raise InvalidTrial("duplicate_case")
    for case in suite["cases"]:
        safe_relative(case["id"])
        for name in case["allowed_edits"]:
            safe_relative(name)
    return suite


def case_by_id(case_id):
    return next((c for c in load_suite()["cases"] if c["id"] == case_id), None)


def generated_files(case):
    task = bounded_read(ROOT / "prompts" / (case["id"] + ".txt"))
    instructions = ("# Synthetic evaluation workspace\n\n"
                    "Work only inside this workspace. No network, installs, account actions, "
                    "private data, or global configuration changes are authorized.\n"
                    "Allowed edits: " + ", ".join(case["allowed_edits"]) + ".\n"
                    "Preserve every other file. TASK.txt states the requested result.\n"
                    "This directory is a scope agreement, not an OS security sandbox.\n")
    return {"TASK.txt": task, "AGENTS.md": instructions.encode("utf-8")}


def expected_initial(case):
    result = tree_hashes(ROOT / "fixtures" / case["id"])
    for name, data in generated_files(case).items():
        if name in result:
            raise InvalidTrial("reserved_fixture_name")
        result[name] = digest(data)
    return dict(sorted(result.items()))


def trusted_hashes(case):
    paths = [ROOT / "runner.py", ROOT / "suite.json", ROOT / "prompts" / (case["id"] + ".txt")]
    paths += sorted((ROOT / "graders").glob("*.py"))
    paths += [ROOT / "fixtures" / case["id"] / name for name in tree_hashes(ROOT / "fixtures" / case["id"])]
    return {safe_relative(p.relative_to(ROOT).as_posix()): digest(bounded_read(p)) for p in paths}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(case_id, runs_root=None):
    case = case_by_id(case_id)
    if case is None:
        raise InvalidTrial("unknown_case")
    runs_root = plain_path(runs_root or ROOT / "runs")
    runs_root.mkdir(parents=True, exist_ok=True)
    initial = expected_initial(case)
    trusted = trusted_hashes(case)
    trial_id = case_id + "-" + uuid.uuid4().hex
    trial = runs_root / trial_id
    trial.mkdir(exist_ok=False)
    workspace = trial / "workspace"
    workspace.mkdir()
    fixture = ROOT / "fixtures" / case_id
    for name in tree_hashes(fixture):
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bounded_read(fixture / name))
    for name, data in generated_files(case).items():
        (workspace / name).write_bytes(data)
    if tree_hashes(workspace) != initial or trusted_hashes(case) != trusted:
        raise InvalidTrial("preparation_drift")
    receipt = {"version": 1, "trial_id": trial_id, "case_id": case_id,
               "prepared_at": datetime.now(timezone.utc).isoformat(),
               "initial_hashes": initial, "trusted_hashes": trusted,
               "allowed_edits": case["allowed_edits"], "security_sandbox": False,
               "adapter": "external-native-dispatch", "model": None, "usage": None}
    write_json(trial / "receipt.json", receipt)
    return trial


def ingest_final(trial):
    candidates = [trial / "final-answer.json", trial / "final-answer.txt"]
    present = [p for p in candidates if p.exists() or p.is_symlink()]
    if not present:
        return {"status": "ABSENT"}
    if len(present) != 1:
        raise InvalidTrial("ambiguous_final_answer")
    path = present[0]
    raw = bounded_read(path, MAX_FINAL_BYTES)
    text = raw.decode("utf-8-sig")
    value = json.loads(text) if path.suffix == ".json" else text
    if path.suffix == ".json" and not isinstance(value, dict):
        raise InvalidTrial("final_json_must_be_object")
    return {"status": "INGESTED", "format": path.suffix[1:], "bytes": len(raw),
            "sha256": digest(raw), "value": value, "used_for_grading": False}


def grade(trial):
    started = time.monotonic()
    result = {"status": "INVALID_TRIAL", "checks": [], "scope_changes": [],
              "security_sandbox": False, "workflow_compliance": "NOT_VERIFIED",
              "visual_quality": "NOT_RUN", "independent_content_review": "NOT_RUN",
              "final_answer": {"status": "ABSENT"}}
    try:
        trial = plain_path(trial)
        receipt = json.loads(bounded_read(trial / "receipt.json", 1024 * 1024))
        if not isinstance(receipt, dict):
            raise InvalidTrial("invalid_receipt_shape")
        case = case_by_id(receipt.get("case_id"))
        if case is None or receipt.get("version") != 1 or receipt.get("trial_id") != trial.name:
            raise InvalidTrial("receipt_identity_mismatch")
        result["case_id"] = case["id"]
        if receipt.get("trusted_hashes") != trusted_hashes(case):
            raise InvalidTrial("trusted_input_drift")
        if receipt.get("initial_hashes") != expected_initial(case) or receipt.get("allowed_edits") != case["allowed_edits"]:
            raise InvalidTrial("receipt_contract_mismatch")
        workspace = trial / "workspace"
        current = tree_hashes(workspace)
        initial = receipt["initial_hashes"]
        changed = sorted(name for name in set(initial) | set(current) if initial.get(name) != current.get(name))
        forbidden = sorted(set(changed) - set(case["allowed_edits"]))
        result["scope_changes"] = changed
        result["checks"].append({"name": "scope", "status": "FAIL" if forbidden else "PASS", "details": forbidden})
        try:
            result["final_answer"] = ingest_final(trial)
            result["checks"].append({"name": "final_answer", "status": "PASS", "details": "Optional final answer is data only; claims are not scores."})
        except (InvalidTrial, UnicodeError, ValueError, OSError) as error:
            result["checks"].append({"name": "final_answer", "status": "FAIL", "details": type(error).__name__})
        result["checks"].extend(checks.grade_case(case["id"], workspace))
        # Execute graders outside the mutable workspace; then recheck both sides.
        if trusted_hashes(case) != receipt["trusted_hashes"]:
            raise InvalidTrial("trusted_input_drift_during_grade")
        post = tree_hashes(workspace)
        if post != current:
            result["checks"].append({"name": "grader_side_effect", "status": "FAIL", "details": "Workspace changed during execution."})
        result["artifact_hashes"] = post
        statuses = {item["status"] for item in result["checks"]}
        result["status"] = "INFRA_ERROR" if "INFRA_ERROR" in statuses else "FAIL" if "FAIL" in statuses else "PASS"
    except InvalidTrial as error:
        result["status"] = "INVALID_TRIAL"
        result["error"] = str(error)
    except Exception as error:
        result["status"] = "INFRA_ERROR"
        result["error"] = type(error).__name__
    result["grading_seconds"] = round(time.monotonic() - started, 4)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest")
    prep = sub.add_parser("prepare")
    prep.add_argument("--case", required=True)
    prep.add_argument("--runs-root", type=Path)
    grading = sub.add_parser("grade-existing")
    grading.add_argument("--trial", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "selftest":
        import unittest
        suite = unittest.defaultTestLoader.discover(str(ROOT), pattern="test_*.py")
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if args.command == "prepare":
        try:
            trial = prepare(args.case, args.runs_root)
        except Exception as error:
            print(json.dumps({"status": "INFRA_ERROR", "error": type(error).__name__}))
            return 2
        print(json.dumps({"trial": str(trial), "workspace": str(trial / "workspace"), "prompt": str(trial / "workspace/TASK.txt")}, ensure_ascii=False))
        return 0
    result = grade(args.trial)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Never write results into a workspace. The caller can redirect this JSON.
    return 0 if result["status"] == "PASS" else 1 if result["status"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
