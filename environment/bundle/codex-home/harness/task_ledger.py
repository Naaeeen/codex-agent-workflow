"""An offline evidence ledger, not a runner or an identity/approval verifier.

Python 3.11+, standard library only. CLI inputs are data; no shell, network,
environment, credentials, model or session interfaces are used.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

MAX_STATE_BYTES = 4 * 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_EVENTS = 512
MAX_CHECKS = 128
STATE_NAME = "state.json"
LOCK_NAME = ".ledger.lock"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


class LedgerError(Exception):
    """Expected input, evidence or state validation failure."""


def require(condition, message):
    if not condition:
        raise LedgerError(message)


def text_field(value, label, *, empty=False):
    require(isinstance(value, str) and len(value) <= 4096, f"Invalid {label}")
    require(empty or bool(value.strip()), f"Empty {label}")
    require("\x00" not in value, f"NUL in {label}")
    return value


def secure_path(value, *, kind=None, must_exist=True):
    """Check every existing component, including Windows junctions/reparse points."""
    require(isinstance(value, (str, Path)), "Path must be text")
    raw = str(value)
    require(len(raw) <= 4096 and "\x00" not in raw, "Invalid path")
    path = Path(raw)
    require(path.is_absolute(), "Paths must be absolute")
    require(".." not in path.parts, "Parent traversal is not allowed")
    if os.name == "nt":
        require(not raw.startswith(("\\\\", "//")), "Network/device paths are not allowed")
        require(all(":" not in part for part in path.parts[1:]), "Alternate streams are not allowed")
    path = Path(os.path.abspath(path))
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode), f"Symbolic links are not allowed: {part}")
        require(not (getattr(info, "st_file_attributes", 0) & 0x400),
                f"Reparse points are not allowed: {part}")
        if stat.S_ISREG(info.st_mode):
            require(info.st_nlink == 1, f"Hard-linked files are not allowed: {part}")
    if must_exist:
        require(path.exists(), f"Path does not exist: {path}")
    if path.exists() and kind == "dir":
        require(path.is_dir(), f"Directory required: {path}")
    if path.exists() and kind == "file":
        require(stat.S_ISREG(path.stat().st_mode), f"Regular file required: {path}")
    return path


def within(path, root):
    return path == root or root in path.parents


def regular_read(path, limit):
    path = secure_path(path, kind="file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "Unsafe file")
        require(before.st_size <= limit, f"File exceeds size limit: {path}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        after = os.fstat(fd)
        require(len(data) <= limit, "File grew beyond size limit")
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "File changed while reading")
        secure_path(path, kind="file")
        final = path.stat()
        require((final.st_dev, final.st_ino) == (after.st_dev, after.st_ino), "File was replaced while reading")
        return data
    finally:
        os.close(fd)


def read_json(path):
    try:
        return json.loads(regular_read(path, MAX_STATE_BYTES).decode("utf-8"),
                          object_pairs_hook=unique_object)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise LedgerError(f"Invalid JSON: {path}") from error


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def validate_checks(checks):
    require(isinstance(checks, list) and 0 < len(checks) <= MAX_CHECKS, "Invalid check count")
    ids = set()
    for check in checks:
        require(isinstance(check, dict) and set(check) == {"id", "description", "required", "type"},
                "Each check requires exactly id, description, required and type")
        require(isinstance(check["id"], str) and ID.fullmatch(check["id"]), "Invalid check id")
        require(check["id"] not in ids, "Duplicate check id")
        ids.add(check["id"])
        text_field(check["description"], "check description")
        require(type(check["required"]) is bool, "required must be a boolean")
        require(check["type"] in ("artifact", "review"), "Invalid check type")
    return ids


def artifact_path(value, state):
    path = Path(value)
    if not path.is_absolute():
        path = Path(state["workspace"]) / path
    path = secure_path(path, kind="file")
    require(within(path, Path(state["workspace"])) or within(path, Path(state["task_dir"])),
            "Artifact must be inside the fixed workspace or task directory")
    require(path != Path(state["task_dir"]) / STATE_NAME and
            path != Path(state["task_dir"]) / LOCK_NAME and
            not path.name.startswith(".ledger-tmp-"), "Ledger metadata cannot be evidence")
    return path


def snapshot(value, state):
    path = artifact_path(value, state)
    data = regular_read(path, MAX_ARTIFACT_BYTES)
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def validate_snapshot(artifact, state):
    require(isinstance(artifact, dict) and set(artifact) == {"path", "sha256", "size"},
            "Invalid artifact record")
    require(isinstance(artifact["path"], str) and Path(artifact["path"]).is_absolute(),
            "Invalid artifact path")
    require(isinstance(artifact["sha256"], str) and HASH.fullmatch(artifact["sha256"]),
            "Invalid artifact hash")
    require(type(artifact["size"]) is int and 0 <= artifact["size"] <= MAX_ARTIFACT_BYTES,
            "Invalid artifact size")
    path = Path(artifact["path"])
    require(".." not in path.parts and (within(path, Path(state["workspace"])) or
            within(path, Path(state["task_dir"]))), "Artifact record is outside allowed scope")


def validate_state(state, task):
    keys = {"version", "workspace", "task_dir", "objective", "revision", "status", "next_action", "checks", "events"}
    require(isinstance(state, dict) and set(state) == keys, "Invalid state schema")
    require(type(state["version"]) is int and state["version"] == 1, "Unsupported state version")
    require(str(task) == state["task_dir"], "Task directory differs from recorded path")
    workspace = secure_path(state["workspace"], kind="dir")
    require(str(workspace) == state["workspace"], "Workspace path is not canonical")
    text_field(state["objective"], "objective")
    text_field(state["next_action"], "next action", empty=True)
    ids = validate_checks(state["checks"])
    events = state["events"]
    require(isinstance(events, list) and 0 < len(events) <= MAX_EVENTS, "Invalid event history")
    require(type(state["revision"]) is int and state["revision"] == len(events), "Revision/history mismatch")
    status, next_action, latest = "active", "", {}
    base = {"revision", "kind", "at", "note"}
    for index, event in enumerate(events, 1):
        require(isinstance(event, dict), "Invalid history event")
        kind = event.get("kind")
        extra = {"check", "result", "artifact"} if kind == "record" else {"next_action"} if kind == "checkpoint" else set()
        require(set(event) == base | extra and kind in ("init", "record", "checkpoint", "complete"),
                "Invalid event schema")
        require(type(event["revision"]) is int and event["revision"] == index, "Invalid event revision")
        require((index == 1) == (kind == "init"), "Invalid init history")
        text_field(event["at"], "event timestamp")
        text_field(event["note"], "event note", empty=True)
        if kind == "record":
            require(event["check"] in ids and event["result"] in ("pass", "fail", "not-run"), "Invalid check result")
            require(event["result"] != "pass" or event["artifact"] is not None, "Pass requires evidence")
            if event["artifact"] is not None:
                validate_snapshot(event["artifact"], state)
            latest[event["check"]] = event
        if kind == "checkpoint":
            next_action = text_field(event["next_action"], "next action")
        if kind == "complete":
            require(any(c["required"] and c["type"] == "review" for c in state["checks"]),
                    "Completed state has no required review")
            require(all(c["id"] in latest and latest[c["id"]]["result"] == "pass"
                        for c in state["checks"] if c["required"]), "Invalid completed history")
        status = "complete" if kind == "complete" else "active"
    require(state["status"] == status and state["next_action"] == next_action, "State/history mismatch")
    return state


@contextmanager
def locked(task):
    task = secure_path(task, kind="dir")
    lock = task / LOCK_NAME
    secure_path(lock, kind="file", must_exist=False)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise LedgerError("Task is locked by another operation. A crashed writer may leave a lock; verify no writer is active before removing it.") from error
    identity = os.fstat(fd)
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.fsync(fd)
        yield
    finally:
        os.close(fd)
        if lock.exists():
            current = lock.lstat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                lock.unlink()


def atomic_save(state, task):
    validate_state(state, task)
    data = (json.dumps(state, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    require(len(data) <= MAX_STATE_BYTES, "State size limit reached; history was not truncated")
    secure_path(task / STATE_NAME, kind="file", must_exist=False)
    temp = task / (".ledger-tmp-" + uuid.uuid4().hex)
    try:
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        secure_path(task, kind="dir")
        secure_path(task / STATE_NAME, kind="file", must_exist=False)
        os.replace(temp, task / STATE_NAME)
    finally:
        if temp.exists():
            temp.unlink()


def append_event(state, kind, note="", **fields):
    require(len(state["events"]) < MAX_EVENTS, "Event limit reached; history was not truncated")
    state["revision"] += 1
    state["events"].append({"revision": state["revision"], "kind": kind,
                            "at": datetime.now(timezone.utc).isoformat(),
                            "note": text_field(note, "note", empty=True), **fields})
    state["status"] = "complete" if kind == "complete" else "active"
    if kind == "checkpoint":
        state["next_action"] = fields["next_action"]


def describe(state):
    latest = {event["check"]: event for event in state["events"] if event["kind"] == "record"}
    checks, groups = [], {name: [] for name in ("missing", "stale", "failed", "not_run")}
    for spec in state["checks"]:
        record = latest.get(spec["id"])
        result, reason = "missing", "No recorded result"
        if record is not None:
            result, reason = record["result"], record["note"]
            if result == "pass":
                try:
                    current = snapshot(record["artifact"]["path"], state)
                    if current != record["artifact"]:
                        result, reason = "stale", "Artifact content differs from recorded hash"
                except (LedgerError, OSError) as error:
                    result, reason = "stale", str(error)
        group = {"missing": "missing", "stale": "stale", "fail": "failed", "not-run": "not_run"}.get(result)
        if group is not None and spec["required"]:
            groups[group].append(spec["id"])
        checks.append({**spec, "state": result, "reason": reason, "record": record})
    has_review = any(c["required"] and c["type"] == "review" for c in checks)
    ready = has_review and not any(groups.values())
    return {"task_dir": state["task_dir"], "workspace": state["workspace"],
            "objective": state["objective"], "revision": state["revision"],
            "status": state["status"], "next_action": state["next_action"],
            "required_checks": [c["id"] for c in checks if c["required"]],
            "has_required_review": has_review, "ready_to_complete": ready,
            "completion_currently_valid": state["status"] == "complete" and ready,
            **groups, "checks": checks, "events": state["events"],
            "failure_history": [e for e in state["events"] if e.get("result") == "fail"],
            "review_limit": "A review artifact proves only that recorded evidence exists; reviewer identity, independence and human approval are not verified."}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--task-dir", required=True)
    init.add_argument("--workspace", required=True)
    init.add_argument("--objective", required=True)
    init.add_argument("--checks", required=True, help="Path to a JSON array of check specifications")
    for name in ("record", "checkpoint", "status", "resume", "complete"):
        command = commands.add_parser(name)
        command.add_argument("--task-dir", required=True)
        if name in ("record", "checkpoint", "complete"):
            command.add_argument("--expected-revision", type=int)
        if name == "record":
            command.add_argument("--check", required=True)
            command.add_argument("--result", choices=("pass", "fail", "not-run"), required=True)
            command.add_argument("--artifact")
            command.add_argument("--note", default="")
        if name == "checkpoint":
            command.add_argument("--next-action", required=True)
            command.add_argument("--note", default="")
    return result


def run(args):
    task = secure_path(args.task_dir, kind="dir", must_exist=args.command != "init")
    if args.command == "init":
        workspace = secure_path(args.workspace, kind="dir")
        checks = read_json(Path(os.path.abspath(args.checks)))
        validate_checks(checks)
        objective = text_field(args.objective, "objective")
        task.mkdir(parents=True, exist_ok=True)
        with locked(task):
            require(not (task / STATE_NAME).exists(), "Task already exists; init never overwrites")
            state = {"version": 1, "task_dir": str(task), "workspace": str(workspace),
                     "objective": objective, "revision": 0, "status": "active",
                     "next_action": "", "checks": checks, "events": []}
            append_event(state, "init")
            atomic_save(state, task)
            return describe(state)
    with locked(task):
        state = validate_state(read_json(task / STATE_NAME), task)
        if args.command in ("status", "resume"):
            return describe(state)
        expected = args.expected_revision
        require(expected is None or expected == state["revision"],
                f"Revision conflict: expected {expected}, actual {state['revision']}")
        if args.command == "record":
            require(args.check in {c["id"] for c in state["checks"]}, "Unknown check id")
            require(args.result != "pass" or args.artifact is not None, "Pass requires an artifact")
            evidence = snapshot(args.artifact, state) if args.artifact is not None else None
            append_event(state, "record", args.note, check=args.check, result=args.result, artifact=evidence)
        elif args.command == "checkpoint":
            append_event(state, "checkpoint", args.note,
                         next_action=text_field(args.next_action, "next action"))
        elif args.command == "complete":
            summary = describe(state)
            require(summary["has_required_review"], "At least one required review check is needed")
            require(summary["ready_to_complete"],
                    "Required checks are incomplete: " + json.dumps({k: summary[k] for k in
                     ("missing", "stale", "failed", "not_run")}))
            append_event(state, "complete")
        atomic_save(state, task)
        return describe(state)


def main(argv=None):
    try:
        result = run(parser().parse_args(argv))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (LedgerError, OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
