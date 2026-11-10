"""Bridge a fresh synthetic artifact trial to an explicitly gated Codex run."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys


CASES = ("C1", "C2", "C3", "D1", "D2", "L1", "R1", "N1")
GRADE_STATUSES = ("PASS", "FAIL", "INVALID_TRIAL", "INFRA_ERROR")
OBSERVER_OUTCOMES = ("success", "incomplete", "turn_failed", "nonzero_exit", "invalid_json",
                     "truncated_stream", "limit_exceeded", "timeout", "launch_error",
                     "io_error", "protocol_error", "stream_error")


@dataclass(frozen=True)
class Dependencies:
    runner: object
    observer: object


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("dependency unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


@lru_cache(maxsize=1)
def load_dependencies():
    """Load the existing local grader and sibling frozen observer; no execution."""
    runner_root = Path(__file__).resolve().parent.parent / "evals"
    observer_path = Path(__file__).resolve().parent.parent / "native-observer" / "native_observer.py"
    existing_graders = sys.modules.get("graders")
    if existing_graders is not None and Path(existing_graders.__file__).resolve().parent != runner_root / "graders":
        raise ValueError("conflicting grader import")
    sys.path.insert(0, str(runner_root))
    try:
        runner = _load_module("_native_eval_artifact_runner", runner_root / "runner.py")
    finally:
        sys.path.pop(0)
    observer = _load_module("_native_eval_observer", observer_path)
    return Dependencies(runner, observer)


def _hash(path, runner):
    return hashlib.sha256(runner.bounded_read(path)).hexdigest()


def _save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def _grade_summary(grade):
    status = grade.get("status") if isinstance(grade, dict) else None
    status = status if status in GRADE_STATUSES else "INFRA_ERROR"
    counts = {key: 0 for key in ("PASS", "FAIL", "INFRA_ERROR")}
    scope = "NOT_RUN"
    checks = grade.get("checks", []) if isinstance(grade, dict) else []
    for check in checks:
        if not isinstance(check, dict):
            continue
        check_status = check.get("status")
        if check_status in counts:
            counts[check_status] += 1
        if check.get("name") == "scope" and check_status in ("PASS", "FAIL"):
            scope = check_status
    # Never propagate arbitrary check names/details, stdout, stderr, or final answer.
    return {"status": status, "check_status_counts": counts, "scope_status": scope}


def run_case(case_id, runs_root, executable, *, execute=False, profile=None,
             timeout_seconds=120, cli_version=None, dependencies=None, observer_call=None):
    """Prepare fresh; execute only if explicitly requested; grade observed artifacts.

    dependencies/observer_call are test injection seams. They are unavailable
    through the CLI. Every retry creates a new trial instead of altering receipts.
    """
    if case_id not in CASES or type(execute) is not bool:
        raise ValueError("unknown case or invalid execution gate")
    if profile is not None and (not isinstance(profile, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", profile)):
        raise ValueError("invalid profile")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("invalid timeout")
    deps = dependencies or load_dependencies()
    runner, observer = deps.runner, deps.observer
    for path in (Path(runs_root), Path(executable)):
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError("absolute paths without parent traversal required")
        runner.plain_path(path)
    if not Path(executable).is_file():
        raise ValueError("executable must exist")
    limits = observer.Limits(timeout_seconds=timeout_seconds)
    limits.validate()
    case = runner.case_by_id(case_id)
    if case is None:
        raise ValueError("case unavailable in installed suite")
    trial = runner.prepare(case_id, Path(runs_root))
    receipt_file = trial / "receipt.json"
    receipt_hash = _hash(receipt_file, runner)
    receipt = json.loads(runner.bounded_read(receipt_file, 1024 * 1024))
    # Prepared evidence remains outside the model's allowed workspace.
    dependency_hashes = {"controller": _hash(Path(__file__), runner),
                         "observer": _hash(Path(observer.__file__), runner)}
    task = runner.bounded_read(trial / "workspace" / "TASK.txt", limits.max_prompt_bytes).decode("utf-8-sig")
    prompt = ("Complete this synthetic task in the current workspace. "
              "Edit only these files: " + ", ".join(case["allowed_edits"]) + ". "
              "Preserve every other file. Do not inspect or change paths outside "
              "this workspace. No network, installs, account actions, private data "
              "or global configuration changes are authorized.\n\n" + task)
    if len(prompt.encode("utf-8")) > limits.max_prompt_bytes:
        raise ValueError("task prompt exceeds observer limit")
    dispatch = {"schema_version": 1, "trial_id": trial.name, "case_id": case_id,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "execution_requested": execute, "sandbox": "workspace-write", "persistent": False,
                "caller_declared_profile": profile, "receipt_sha256": receipt_hash,
                "dependency_sha256": dependency_hashes,
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "observer_metadata": "observer/metadata.json"}
    _save(trial / "dispatch.json", dispatch)
    result = {"schema_version": 1, "trial_id": trial.name, "case_id": case_id,
              "status": "PREPARED", "artifact_status": "NOT_RUN", "observer_outcome": "NOT_RUN",
              "observer_metadata_sha256": None, "receipt_unchanged": True,
              "dependencies_unchanged": True, "grade_summary": None}
    if execute:
        native = None
        observer_failed = False
        config = observer.ObserverConfig(executable=Path(executable), workspace=trial / "workspace",
                                         result_dir=trial / "observer", sandbox="workspace-write",
                                         persistent=False, profile=profile, cli_version=cli_version,
                                         limits=limits)
        try:
            native = (observer_call or observer.run_observer)(config, prompt)
            raw = runner.bounded_read(trial / "observer" / "metadata.json", 1024 * 1024)
            saved = json.loads(raw)
            if (not isinstance(native, dict) or saved != native or native.get("schema_version") != 1
                    or native.get("outcome") not in OBSERVER_OUTCOMES
                    or type(native.get("success")) is not bool
                    or native["success"] != (native["outcome"] == "success")
                    or native.get("raw_streams_saved") is not False):
                raise ValueError("invalid observer result")
            result["observer_metadata_sha256"] = hashlib.sha256(raw).hexdigest()
            result["observer_outcome"] = native["outcome"]
        except Exception:
            # Exceptions may contain prompt/output/secrets; retain only a fixed label.
            observer_failed = True
            result["observer_outcome"] = "OBSERVER_ERROR"
        try:
            grade = runner.grade(trial)
            result["grade_summary"] = _grade_summary(grade)
            result["artifact_status"] = result["grade_summary"]["status"]
            result["receipt_unchanged"] = _hash(receipt_file, runner) == receipt_hash
            result["dependencies_unchanged"] = (
                _hash(Path(__file__), runner) == dependency_hashes["controller"]
                and _hash(Path(observer.__file__), runner) == dependency_hashes["observer"]
                and runner.trusted_hashes(case) == receipt["trusted_hashes"])
        except Exception:
            result["artifact_status"] = "INFRA_ERROR"
            result["receipt_unchanged"] = False
            result["dependencies_unchanged"] = False
        if not result["receipt_unchanged"] or not result["dependencies_unchanged"] or result["artifact_status"] == "INVALID_TRIAL":
            result["status"] = "INVALID_TRIAL"
        elif observer_failed or result["artifact_status"] == "INFRA_ERROR":
            result["status"] = "INFRA_ERROR"
        elif native["success"] and result["artifact_status"] == "PASS":
            result["status"] = "PASS"
        else:
            result["status"] = "FAIL"
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    _save(trial / "evaluation.json", result)
    return {**result, "trial": str(trial)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--execute", action="store_true", help="Explicitly authorize one actual native Codex invocation")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--cli-version")
    args = parser.parse_args(argv)
    try:
        result = run_case(args.case, args.runs_root, args.executable, execute=args.execute,
                          profile=args.profile, timeout_seconds=args.timeout, cli_version=args.cli_version)
    except Exception:
        print(json.dumps({"status": "INFRA_ERROR", "error": "bridge_configuration_or_storage_error"}))
        return 2
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["status"] in ("PREPARED", "PASS") else 1 if result["status"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
