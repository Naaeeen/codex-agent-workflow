"""Bounded, metadata-only observer for one explicitly chosen native Codex run.

This is not a sandbox. The selected CLI retains its normal authentication,
configuration, and policy behavior. Raw subprocess streams never reach disk.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid


EVENTS = ("thread.started", "turn.started", "item.started", "item.updated",
          "item.completed", "turn.completed", "turn.failed", "error")
ITEMS = ("agent_message", "reasoning", "command_execution", "file_change",
         "mcp_tool_call", "web_search", "todo_list", "error")
STATUSES = ("in_progress", "completed", "failed", "declined")
USAGE = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens")
CATEGORIES = {"auth": (b"auth", b"unauthorized", b"credential"),
              "permission": (b"permission", b"access denied"),
              "failed": (b"failed", b"failure"),
              "unsupported": (b"unsupported", b"not supported"),
              "error": (b"error",)}
VERSION = re.compile(r"codex-cli [0-9]{1,8}\.[0-9]{1,8}\.[0-9]{1,8}(?:-(?:alpha|beta|rc)\.[0-9]{1,8})?\Z")
UUID_PATTERN = re.compile(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\Z")


@dataclass(frozen=True)
class Limits:
    timeout_seconds: float = 120
    max_line_bytes: int = 131072
    max_stdout_bytes: int = 4194304
    max_stderr_bytes: int = 1048576
    max_events: int = 10000
    max_prompt_bytes: int = 1048576
    max_expected_bytes: int = 65536

    def validate(self):
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError("limits must be finite positive numbers")
            if name != "timeout_seconds" and not isinstance(value, int):
                raise ValueError("byte and event limits must be integers")
        if self.timeout_seconds > 86400 or any(getattr(self, k) > 67108864 for k in vars(self) if k != "timeout_seconds"):
            raise ValueError("limits exceed observer hard ceiling")


@dataclass(frozen=True)
class ObserverConfig:
    executable: Path
    workspace: Path
    result_dir: Path
    sandbox: str = "read-only"
    persistent: bool = False
    resume_id: str | None = None
    cli_version: str | None = None
    limits: Limits = field(default_factory=Limits)
    profile: str | None = None


def _safe_uuid(value):
    return value if isinstance(value, str) and UUID_PATTERN.fullmatch(value) else None


def _path(value, *, existing, directory):
    p = Path(value)
    if not p.is_absolute() or ".." in p.parts:
        raise ValueError("paths must be absolute without parent traversal")
    # lstat each lexical ancestor before resolve: resolve alone hides symlinks.
    for ancestor in reversed((p, *p.parents)):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            if ancestor != p or existing:
                raise ValueError("path or parent does not exist") from None
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("symlinks and Windows reparse points are not permitted")
    if existing and (not p.exists() or (p.is_dir() != directory)):
        raise ValueError("selected path has the wrong kind")
    return p.resolve(strict=existing)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


class _WindowsTree:
    """Documented Job Object + Toolhelp APIs; child starts suspended until owned."""
    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.k = c.WinDLL("kernel32", use_last_error=True)
        class Basic(c.Structure):
            _fields_ = [("ProcessTime", c.c_int64), ("JobTime", c.c_int64), ("Flags", w.DWORD),
                        ("MinWS", c.c_size_t), ("MaxWS", c.c_size_t), ("Active", w.DWORD),
                        ("Affinity", c.c_size_t), ("Priority", w.DWORD), ("Scheduling", w.DWORD)]
        class IO(c.Structure):
            _fields_ = [(name, c.c_uint64) for name in ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]
        class Extended(c.Structure):
            _fields_ = [("Basic", Basic), ("IO", IO), ("ProcessMem", c.c_size_t), ("JobMem", c.c_size_t),
                        ("PeakProcess", c.c_size_t), ("PeakJob", c.c_size_t)]
        class ThreadEntry(c.Structure):
            _fields_ = [("size", w.DWORD), ("usage", w.DWORD), ("tid", w.DWORD), ("pid", w.DWORD),
                        ("base_priority", w.LONG), ("delta_priority", w.LONG), ("flags", w.DWORD)]
        self.ThreadEntry = ThreadEntry
        prototypes = {
            "CreateJobObjectW": ([c.c_void_p, w.LPCWSTR], w.HANDLE),
            "SetInformationJobObject": ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD], w.BOOL),
            "OpenProcess": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
            "CreateToolhelp32Snapshot": ([w.DWORD, w.DWORD], w.HANDLE),
            "Thread32First": ([w.HANDLE, c.POINTER(ThreadEntry)], w.BOOL),
            "Thread32Next": ([w.HANDLE, c.POINTER(ThreadEntry)], w.BOOL),
            "OpenThread": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            "ResumeThread": ([w.HANDLE], w.DWORD),
            "CloseHandle": ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in prototypes.items():
            getattr(self.k, name).argtypes = args
            getattr(self.k, name).restype = result
        self.handle = self.k.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError("owned process container unavailable")
        info = Extended()
        info.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.k.SetInformationJobObject(self.handle, 9, c.byref(info), c.sizeof(info)):
            self.close()
            raise OSError("owned process container unavailable")

    def attach_and_resume(self, process):
        c, k = self.c, self.k
        handle = k.OpenProcess(0x0100 | 0x0001, False, process.pid)  # SET_QUOTA | TERMINATE
        if not handle:
            raise OSError("process ownership failed")
        try:
            if not k.AssignProcessToJobObject(self.handle, handle):
                raise OSError("process ownership failed")
        finally:
            k.CloseHandle(handle)
        snapshot = k.CreateToolhelp32Snapshot(4, 0)  # TH32CS_SNAPTHREAD
        if snapshot == c.c_void_p(-1).value:
            raise OSError("owned process resume failed")
        resumed = 0
        try:
            entry = self.ThreadEntry()
            entry.size = c.sizeof(entry)
            found = k.Thread32First(snapshot, c.byref(entry))
            while found:
                if entry.pid == process.pid:
                    thread = k.OpenThread(2, False, entry.tid)  # THREAD_SUSPEND_RESUME
                    if not thread:
                        raise OSError("owned process resume failed")
                    try:
                        if k.ResumeThread(thread) == 0xFFFFFFFF:
                            raise OSError("owned process resume failed")
                        resumed += 1
                    finally:
                        k.CloseHandle(thread)
                found = k.Thread32Next(snapshot, c.byref(entry))
        finally:
            k.CloseHandle(snapshot)
        if not resumed:
            raise OSError("owned process resume failed")

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None


def _start_owned(args, workspace, *, stdin, stdout, stderr):
    tree = _WindowsTree() if os.name == "nt" else None
    process = None
    try:
        process = subprocess.Popen(args, cwd=workspace, stdin=stdin, stdout=stdout, stderr=stderr,
                                   shell=False, start_new_session=os.name != "nt",
                                   creationflags=(subprocess.CREATE_NO_WINDOW | 4) if os.name == "nt" else 0)
        if tree:
            tree.attach_and_resume(process)
        return process, tree
    except (OSError, subprocess.SubprocessError):
        _stop_owned(process, tree)
        if process:
            for pipe in (process.stdin, process.stdout, process.stderr):
                if pipe:
                    pipe.close()
        raise


def _stop_owned(process, tree):
    # The suspended Windows child cannot create descendants before assignment.
    # Closing the job also kills descendants after the parent has exited.
    if tree:
        tree.close()
    elif process:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


class _Projection:
    def __init__(self, limits, expected, resume_id=None):
        self.limits, self.expected = limits, expected
        self.resume_id = resume_id
        self.phase = 0  # thread.started -> turn.started -> exactly one terminal
        self.stop = threading.Event()
        self.limit_reasons = set()
        self.events = dict.fromkeys(EVENTS, 0)
        self.items = dict.fromkeys(ITEMS, 0)
        self.statuses = dict.fromkeys(STATUSES, 0)
        self.exit_codes = {}
        self.usage = dict.fromkeys(USAGE)
        self.thread_id = None
        self.unknown_events = self.unknown_items = self.invalid = self.event_total = 0
        self.stdout_bytes = self.stderr_bytes = 0
        self.stderr_hash = hashlib.sha256()
        self.categories = dict.fromkeys(CATEGORIES, False)
        self.truncated = self.protocol_error = self.reader_error = False
        self.matched = None if expected is None else False

    def limit(self, reason):
        self.limit_reasons.add(reason)
        self.stop.set()

    def consume(self, line):
        try:
            value = json.loads(line)
        except (ValueError, UnicodeError, RecursionError):
            self.invalid += 1
            return
        if not isinstance(value, dict):
            self.invalid += 1
            return
        self.event_total += 1
        if self.event_total > self.limits.max_events:
            self.limit("event_count")
            return
        kind = value.get("type")
        if not isinstance(kind, str) or kind not in self.events:
            self.unknown_events += 1
            return
        self.events[kind] += 1
        if kind == "thread.started":
            candidate = _safe_uuid(value.get("thread_id"))
            if (candidate is None or self.phase != 0 or self.events[kind] != 1
                    or self.event_total != 1
                    or (self.resume_id is not None and candidate != self.resume_id)):
                self.protocol_error = True
            self.thread_id = candidate
            self.phase = 1
        elif kind == "turn.started":
            if self.phase != 1 or self.events[kind] != 1 or self.events["thread.started"] != 1:
                self.protocol_error = True
            self.phase = 2
        elif kind in ("turn.completed", "turn.failed"):
            if self.phase != 2 or self.events["thread.started"] != 1 or self.events["turn.started"] != 1:
                self.protocol_error = True
            self.phase = 3
            if kind == "turn.completed":
                usage = value.get("usage")
                if isinstance(usage, dict):
                    for key in USAGE:
                        n = usage.get(key)
                        self.usage[key] = n if type(n) is int and 0 <= n <= 2**63 - 1 else None
        elif kind.startswith("item."):
            item = value.get("item")
            if not isinstance(item, dict):
                self.protocol_error = True
                return
            item_kind = item.get("type")
            if not isinstance(item_kind, str) or item_kind not in self.items:
                self.unknown_items += 1
                return
            self.items[item_kind] += 1
            status = item.get("status")
            if isinstance(status, str) and status in self.statuses:
                self.statuses[status] += 1
            code = item.get("exit_code")
            if type(code) is int and -(2**31) <= code <= 2**32 - 1:
                label = str(code)
                self.exit_codes[label] = self.exit_codes.get(label, 0) + 1
            if kind == "item.completed" and item_kind == "agent_message" and self.expected is not None:
                text = item.get("text")
                self.matched = False
                try:
                    if isinstance(text, str) and len(text.encode("utf-8")) <= self.limits.max_expected_bytes:
                        self.matched = _canonical(json.loads(text)) == self.expected
                except (ValueError, UnicodeError, RecursionError, TypeError):
                    pass

    def stdout(self, pipe):
        pending = bytearray()
        try:
            while chunk := os.read(pipe.fileno(), 4096):
                self.stdout_bytes += len(chunk)
                if self.stdout_bytes > self.limits.max_stdout_bytes:
                    self.limit("stdout_bytes")
                if self.stop.is_set():
                    pending.clear()
                    break
                pending.extend(chunk)
                while b"\n" in pending:
                    line, _, remainder = pending.partition(b"\n")
                    pending = bytearray(remainder)
                    if len(line) > self.limits.max_line_bytes:
                        self.limit("line_bytes")
                        pending.clear()
                        break
                    self.consume(line)
                    if self.stop.is_set():
                        pending.clear()
                        break
                if len(pending) > self.limits.max_line_bytes:
                    self.limit("line_bytes")
                    pending.clear()
                if self.stop.is_set():
                    break
            if pending:
                self.truncated = True
        except OSError:
            self.reader_error = True
            self.stop.set()
        finally:
            pipe.close()

    def stderr(self, pipe):
        tail = b""
        try:
            while chunk := os.read(pipe.fileno(), 4096):
                self.stderr_bytes += len(chunk)
                self.stderr_hash.update(chunk)
                sample = tail + chunk.lower()
                for category, terms in CATEGORIES.items():
                    if any(term in sample for term in terms):
                        self.categories[category] = True
                tail = sample[-32:]
                if self.stderr_bytes > self.limits.max_stderr_bytes:
                    self.limit("stderr_bytes")
                    break
        except OSError:
            self.reader_error = True
            self.stop.set()
        finally:
            pipe.close()


def _version(executable, supplied, workspace):
    if supplied is not None:
        if not isinstance(supplied, str) or not VERSION.fullmatch(supplied):
            raise ValueError("CLI version must be a bounded codex-cli version")
        return supplied, "supplied"
    # --version never starts a turn. Both streams are discarded from the artifact.
    # Output is read in bounded chunks, not communicate/capture_output.
    process, tree = _start_owned([str(executable), "--version"], workspace,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL)
    result = bytearray()
    def read_version():
        while chunk := os.read(process.stdout.fileno(), 256):
            if len(result) + len(chunk) > 256:
                process.kill()
                break
            result.extend(chunk)
        process.stdout.close()
    thread = threading.Thread(target=read_version, daemon=True)
    thread.start()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    finally:
        _stop_owned(process, tree)
    thread.join(timeout=5)
    try:
        text = bytes(result).decode("ascii").strip()
    except UnicodeError:
        text = ""
    if process.returncode != 0 or thread.is_alive() or not VERSION.fullmatch(text):
        raise ValueError("CLI version check failed")
    return text, "checked"


def run_observer(config: ObserverConfig, prompt: str, *, expected_final=None):
    """Run one turn; return and persist only the fixed metadata schema.

    expected_final is an in-memory JSON value; None disables comparison. Caller
    should supply an already known version for fake fixtures and pinned runs.
    """
    config.limits.validate()
    if config.sandbox not in ("read-only", "workspace-write"):
        raise ValueError("sandbox must be read-only or workspace-write")
    if type(config.persistent) is not bool:
        raise ValueError("persistent must be a boolean")
    if config.profile is not None and (not isinstance(config.profile, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", config.profile)):
        raise ValueError("profile must be a simple bounded name")
    if config.resume_id is not None and not _safe_uuid(config.resume_id):
        raise ValueError("resume requires an exact lowercase UUID")
    executable = _path(config.executable, existing=True, directory=False)
    workspace = _path(config.workspace, existing=True, directory=True)
    destination = _path(config.result_dir, existing=False, directory=True)
    if destination.exists():
        raise FileExistsError("result directory already exists")
    if not isinstance(prompt, str):
        raise ValueError("prompt must be text")
    prompt_bytes = prompt.encode("utf-8")
    if len(prompt_bytes) > config.limits.max_prompt_bytes:
        raise ValueError("prompt exceeds byte limit")
    expected = None if expected_final is None else _canonical(expected_final)
    if expected is not None and len(expected.encode("utf-8")) > config.limits.max_expected_bytes:
        raise ValueError("expected JSON exceeds byte limit")
    version, version_source = _version(executable, config.cli_version, workspace)
    destination.mkdir(mode=0o700)  # exclusive creation; never reuse an earlier result
    args = [str(executable), "--no-daemon", "exec", "--sandbox", config.sandbox, "--cd", str(workspace), "--color", "never"]
    if config.profile is not None:
        args.extend(["--profile", config.profile])
    if config.resume_id:
        args.append("resume")
    args.extend(["--json", "--skip-git-repo-check"])
    if not config.persistent:
        args.append("--ephemeral")
    if config.resume_id:
        args.append(config.resume_id)
    args.append("-")
    projection = _Projection(config.limits, expected, config.resume_id)
    started = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    tree = None
    process = None
    readers = []
    writer = None
    timed_out = launch_error = False
    try:
        process, tree = _start_owned(args, workspace, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        readers = [threading.Thread(target=projection.stdout, args=(process.stdout,), daemon=True),
                   threading.Thread(target=projection.stderr, args=(process.stderr,), daemon=True)]
        for reader in readers:
            reader.start()
        def write_prompt():
            try:
                process.stdin.write(prompt_bytes)
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
            finally:
                process.stdin.close()
        writer = threading.Thread(target=write_prompt, daemon=True)
        writer.start()
        while True:
            if time.monotonic() - start >= config.limits.timeout_seconds:
                timed_out = True
                break
            if projection.stop.is_set():
                break
            if process.poll() is not None:
                break
            time.sleep(0.01)
    except (OSError, subprocess.SubprocessError):
        launch_error = True
    finally:
        if process:
            try:
                _stop_owned(process, tree)
            except subprocess.TimeoutExpired:
                launch_error = True
            for reader in readers:
                reader.join(timeout=5)
            if writer:
                writer.join(timeout=5)
            if any(reader.is_alive() for reader in readers) or (writer and writer.is_alive()):
                projection.reader_error = True
            if not readers:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    if pipe:
                        pipe.close()
    terminals = projection.events["turn.completed"] + projection.events["turn.failed"]
    if terminals > 1 or projection.events["turn.started"] > 1:
        projection.protocol_error = True
    exit_code = process.returncode if process else None
    if timed_out:
        outcome = "timeout"
    elif projection.limit_reasons:
        outcome = "limit_exceeded"
    elif launch_error:
        outcome = "launch_error"
    elif projection.reader_error:
        outcome = "io_error"
    elif projection.truncated:
        outcome = "truncated_stream"
    elif projection.invalid:
        outcome = "invalid_json"
    elif projection.protocol_error:
        outcome = "protocol_error"
    elif exit_code != 0:
        outcome = "nonzero_exit"
    elif projection.events["turn.failed"]:
        outcome = "turn_failed"
    elif projection.events["error"]:
        outcome = "stream_error"
    elif projection.events["turn.completed"] == 1:
        outcome = "success"
    else:
        outcome = "incomplete"
    data = {"schema_version": 1, "run_id": str(uuid.uuid4()), "started_utc": started,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "wall_seconds": round(time.monotonic() - start, 6),
            "cli_version": version, "cli_version_source": version_source,
            "caller_declared_profile": config.profile,
            "sandbox": config.sandbox, "persistent": config.persistent, "resume_id": config.resume_id,
            "thread_id": projection.thread_id, "outcome": outcome, "success": outcome == "success",
            "exit_code": exit_code, "event_counts": projection.events, "item_counts": projection.items,
            "item_status_counts": projection.statuses, "item_exit_code_counts": projection.exit_codes,
            "unknown_event_count": projection.unknown_events, "unknown_item_count": projection.unknown_items,
            "usage": projection.usage,
            "usage_scope": "cumulative_thread_snapshot" if version == "codex-cli 0.166.0-alpha.6" else "unknown_do_not_sum",
            "usage_source_event": "turn.completed", "invalid_json_lines": projection.invalid,
            "terminal_count": terminals, "truncated_stream": projection.truncated,
            "timed_out": timed_out, "limit_reasons": sorted(projection.limit_reasons),
            "stdout_bytes": projection.stdout_bytes, "stderr_bytes": projection.stderr_bytes,
            "stderr_sha256": projection.stderr_hash.hexdigest(), "stderr_categories": projection.categories,
            "expected_final_matched": projection.matched, "raw_streams_saved": False}
    with (destination / "metadata.json").open("x", encoding="utf-8", newline="\n") as output:
        json.dump(data, output, indent=2, allow_nan=False)
        output.write("\n")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--sandbox", choices=("read-only", "workspace-write"), default="read-only")
    parser.add_argument("--persistent", action="store_true")
    parser.add_argument("--resume-id")
    parser.add_argument("--cli-version")
    parser.add_argument("--profile")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    try:
        limit = Limits(timeout_seconds=args.timeout)
        prompt = sys.stdin.buffer.read(limit.max_prompt_bytes + 1).decode("utf-8")
        config = ObserverConfig(args.executable, args.workspace, args.result_dir, args.sandbox,
                                args.persistent, args.resume_id, args.cli_version, limit, args.profile)
        result = run_observer(config, prompt)
    except (ValueError, OSError, TypeError):
        print("observer configuration or result storage failed", file=sys.stderr)
        return 2
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
