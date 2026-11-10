"""Read-only declared evidence contract; never a truth or quality verifier."""
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import sys

sys.dont_write_bytecode = True
try:
    from task_ledger import (HASH, ID, LedgerError, MAX_ARTIFACT_BYTES, read_json,
                             regular_read, secure_path, within)
except ImportError:
    if __name__ != "__main__":
        raise
    print('{"status":"contract_invalid","defects":["HELPER_UNAVAILABLE"]}')
    sys.exit(2)


class ContractError(Exception):
    pass


def need(condition, code):
    if not condition:
        raise ContractError(code)


def shape(value, keys):
    need(isinstance(value, dict) and set(value) == set(keys.split()), "SCHEMA")


def text(value):
    need(isinstance(value, str) and 0 < len(value) <= 4096 and value.strip()
         and "\x00" not in value, "SCHEMA")


def indexed(items):
    need(isinstance(items, list) and 0 < len(items) <= 256, "SCHEMA")
    result = {}
    for item in items:
        need(isinstance(item, dict), "SCHEMA")
        identifier = item.get("id")
        need(isinstance(identifier, str) and ID.fullmatch(identifier), "SCHEMA")
        need(identifier not in result, "DUPLICATE_ID")
        result[identifier] = item
    return result


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def protocol(document):
    return {key: document[key] for key in ("version", "hypothesis", "changed_factor",
            "acceptance", "artifacts", "workload", "plan", "trials")}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def check(document, root):
    shape(document, "version hypothesis changed_factor acceptance artifacts workload plan trials review decision")
    need(type(document["version"]) is int and document["version"] == 1, "SCHEMA")
    text(document["hypothesis"])
    text(document["changed_factor"])
    acceptance = document["acceptance"]
    shape(acceptance, "min_delta")
    need(number(acceptance["min_delta"]) and acceptance["min_delta"] >= 0, "SCHEMA")
    need(document["decision"] in ("adopt", "reject", "defer"), "SCHEMA")
    artifacts = indexed(document["artifacts"])
    total = 0
    for artifact in artifacts.values():
        shape(artifact, "id path sha256 requires")
        raw = artifact["path"]
        need(isinstance(raw, str) and 0 < len(raw) <= 4096, "ARTIFACT_PATH")
        parts = raw.replace("\\", "/").split("/")
        need(not PureWindowsPath(raw).is_absolute() and not Path(raw).is_absolute()
             and not PureWindowsPath(raw).drive and all(p not in ("", ".", "..") for p in parts)
             and ":" not in raw and "\x00" not in raw, "ARTIFACT_PATH")
        try:
            path = secure_path(root.joinpath(*parts), kind="file")
            need(within(path, root) and path != root / "improvement.json", "ARTIFACT_PATH")
            data = regular_read(path, MAX_ARTIFACT_BYTES)
        except (LedgerError, OSError, ValueError):
            raise ContractError("ARTIFACT_PATH") from None
        total += len(data)
        need(total <= 128 * 1024 * 1024, "BUNDLE_SIZE")
        need(isinstance(artifact["sha256"], str) and HASH.fullmatch(artifact["sha256"]), "SCHEMA")
        need(hashlib.sha256(data).hexdigest() == artifact["sha256"], "ARTIFACT_HASH")
        refs = artifact["requires"]
        need(isinstance(refs, list) and len(refs) <= 256
             and all(isinstance(ref, str) for ref in refs), "SCHEMA")
        need(len(set(refs)) == len(refs) and all(ref in artifacts for ref in refs), "REFERENCE")
    active, visited = set(), set()
    def visit(identifier):
        need(identifier not in active, "DEPENDENCY_CYCLE")
        if identifier not in visited:
            active.add(identifier)
            for reference in artifacts[identifier]["requires"]:
                visit(reference)
            active.remove(identifier)
            visited.add(identifier)
    for identifier in artifacts:
        visit(identifier)
    workload, plan, trials = (indexed(document[key]) for key in ("workload", "plan", "trials"))
    for case in workload.values():
        shape(case, "id split fixture")
        need(case["split"] in ("dev", "heldout", "negative"), "SCHEMA")
        need(isinstance(case["fixture"], str) and case["fixture"] in artifacts, "REFERENCE")
    need(all(len({c["split"] for c in workload.values() if c["fixture"] == fixture}) == 1
             for fixture in {c["fixture"] for c in workload.values()}), "SPLIT_OVERLAP")
    for trial in plan.values():
        shape(trial, "id case")
        need(isinstance(trial["case"], str) and trial["case"] in workload, "REFERENCE")
    need({t["case"] for t in plan.values()} == set(workload), "PLAN_COVERAGE")
    need(set(plan) == set(trials), "TRIAL_SET")
    sources = {"baseline": set(), "candidate": set()}
    for trial in trials.values():
        shape(trial, "id case baseline candidate")
        need(trial["case"] == plan[trial["id"]]["case"], "TRIAL_CASE")
        for arm in ("baseline", "candidate"):
            shape(trial[arm], "bindings result")
            bindings, result = trial[arm]["bindings"], trial[arm]["result"]
            shape(bindings, "source fixture grader environment")
            need(all(isinstance(ref, str) and ref in artifacts for ref in bindings.values()), "REFERENCE")
            sources[arm].add(bindings["source"])
            shape(result, "status score evidence")
            need(isinstance(result["evidence"], str) and result["evidence"] in artifacts, "REFERENCE")
            need(result["status"] in ("pass", "fail", "unknown", "error", "aborted", "not-run"), "SCHEMA")
            need(number(result["score"]) if result["status"] == "pass" else result["score"] is None, "SCHEMA")
        left, right = trial["baseline"]["bindings"], trial["candidate"]["bindings"]
        need(all(left[key] == right[key] for key in ("fixture", "grader", "environment"))
             and left["fixture"] == workload[trial["case"]]["fixture"], "ARM_BINDINGS")
    need(all(len(values) == 1 for values in sources.values()), "SOURCE_BINDINGS")
    review = document["review"]
    shape(review, "evidence independent supports bindings protocol_sha256")
    need(isinstance(review["evidence"], str) and review["evidence"] in artifacts, "REFERENCE")
    need(type(review["independent"]) is bool, "SCHEMA")
    need(review["supports"] == document["decision"], "REVIEW_DECISION")
    expected = {key: item["sha256"] for key, item in artifacts.items() if key != review["evidence"]}
    need(review["bindings"] == expected, "REVIEW_BINDINGS")
    need(review["protocol_sha256"] == digest(protocol(document)), "REVIEW_PROTOCOL")
    if document["decision"] == "adopt":
        need({c["split"] for c in workload.values()} == {"dev", "heldout", "negative"}, "SPLIT_COVERAGE")
        need(review["independent"], "ADOPT_REVIEW")
        need(all(t[arm]["result"]["status"] == "pass" for t in trials.values()
                 for arm in ("baseline", "candidate")), "ADOPT_RESULTS")
        need(all(t["candidate"]["result"]["score"] - t["baseline"]["result"]["score"]
                 >= acceptance["min_delta"] for t in trials.values()
                 if workload[t["case"]]["split"] != "negative"), "ADOPT_DELTA")


def validate(task_dir):
    try:
        root = secure_path(Path(task_dir).absolute(), kind="dir")
        check(read_json(root / "improvement.json"), root)
        return {"status": "contract_valid", "defects": []}
    except ContractError as error:
        code = str(error)
    except (LedgerError, OSError, ValueError, TypeError, KeyError, RecursionError, OverflowError):
        code = "INPUT_INVALID"
    return {"status": "contract_invalid", "defects": [code]}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    result = validate(args[0]) if len(args) == 1 else {"status": "contract_invalid", "defects": ["ARGUMENTS"]}
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["status"] == "contract_valid" else 2


if __name__ == "__main__":
    sys.exit(main())
