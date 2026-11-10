"""Deterministic synthetic CLI boundary tests; never invokes a model."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import native_observer
from native_observer import Limits, ObserverConfig, run_observer


UUID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CANARY = "SENSITIVE_CANARY_8a772_prompt_command_text"
NORMAL = [
    {"type": "thread.started", "thread_id": UUID},
    {"type": "turn.started"},
    {"type": "item.started", "item": {"type": "command_execution", "status": "in_progress"}},
    {"type": "item.completed", "item": {"type": "command_execution", "status": "completed", "exit_code": 0, "command": CANARY, "aggregated_output": CANARY}},
    {"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok":true}'}},
    {"type": "turn.completed", "usage": {"input_tokens": 11, "cached_input_tokens": 5, "output_tokens": 3}},
]
FAKE = r'''
import json, os, subprocess, sys, time
from pathlib import Path
f=json.loads(Path("fixture.json").read_text())
if f.get("ignore_stdin"): time.sleep(120)
prompt=sys.stdin.buffer.read()
Path("invocation.json").write_text(json.dumps({"argv":sys.argv[1:],"stdin_sha256":__import__("hashlib").sha256(prompt).hexdigest()}))
if f.get("tree"):
    code="import subprocess,sys,time; from pathlib import Path; p=subprocess.Popen([sys.executable,'-c',\"import time; time.sleep(120)\"]); Path('grandchild.pid').write_text(str(p.pid)); Path('child.pid').write_text(str(__import__('os').getpid())); time.sleep(120)"
    subprocess.Popen([sys.executable,"-c",code])
    end=time.time()+4
    while not Path('grandchild.pid').exists() and time.time()<end: time.sleep(.01)
for event in f.get("events",[]):
    sys.stdout.write(json.dumps(event)+"\n"); sys.stdout.flush()
if "raw" in f: sys.stdout.write(f["raw"]); sys.stdout.flush()
if "stderr" in f: sys.stderr.write(f["stderr"]); sys.stderr.flush()
if f.get("flood_stderr"):
    for _ in range(3000): sys.stderr.write("z"*4096); sys.stderr.flush()
time.sleep(f.get("sleep",0))
sys.exit(f.get("exit",0))
'''


def alive(pid):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        h = k.OpenProcess(0x00100000, False, pid)
        if not h: return False
        try: return k.WaitForSingleObject(h, 0) == 258
        finally: k.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError: return False


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "exec").write_text(FAKE, encoding="utf-8")
        self.result = self.root / "result"
        self.launched_commands = []
        original_start = native_observer._start_owned
        def fake_python_adapter(args, *positional, **options):
            # Python cannot accept Codex's global --no-daemon option. Preserve
            # the observed production argv, strip only that option, then run
            # the real owned-process implementation and fake CLI fixture.
            self.launched_commands.append(list(args))
            adapted = [args[0], *args[2:]] if args[1:2] == ["--no-daemon"] else args
            return original_start(adapted, *positional, **options)
        self.start_patch = patch("native_observer._start_owned", side_effect=fake_python_adapter)
        self.start_patch.start()
        self.addCleanup(self.start_patch.stop)

    def tearDown(self): self.tmp.cleanup()

    def run_fake(self, fixture=None, **kwargs):
        (self.workspace / "fixture.json").write_text(json.dumps(fixture or {"events": NORMAL}), encoding="utf-8")
        config = ObserverConfig(executable=Path(sys.executable), workspace=self.workspace,
                                result_dir=self.result, **{"cli_version": "codex-cli 0.166.0-alpha.6", **kwargs})
        return run_observer(config, CANARY, expected_final={"ok": True})

    def assert_saved_safe(self, data):
        text = (self.result / "metadata.json").read_text()
        self.assertEqual(json.loads(text), data)
        self.assertNotIn(CANARY, text)
        self.assertEqual([p.name for p in self.result.iterdir()], ["metadata.json"])

    def test_normal_safe_projection_and_stdin(self):
        data = self.run_fake()
        self.assertEqual(data["outcome"], "success")
        self.assertEqual(data["thread_id"], UUID)
        self.assertEqual(data["usage"], {"input_tokens": 11, "cached_input_tokens": 5, "cache_write_input_tokens": None, "output_tokens": 3, "reasoning_output_tokens": None})
        self.assertTrue(data["expected_final_matched"])
        argv = json.loads((self.workspace / "invocation.json").read_text())
        self.assertNotIn(CANARY, " ".join(argv["argv"]))
        self.assertEqual(argv["stdin_sha256"], hashlib.sha256(CANARY.encode()).hexdigest())
        self.assertEqual(argv["argv"], ["--sandbox", "read-only", "--cd", str(self.workspace), "--color", "never", "--json", "--skip-git-repo-check", "--ephemeral", "-"])
        self.assert_saved_safe(data)

    def test_zero_exit_without_terminal_is_incomplete(self):
        data = self.run_fake({"events": NORMAL[:2]})
        self.assertEqual(data["outcome"], "incomplete")
        self.assertFalse(data["success"])

    def test_turn_failure_is_distinct(self):
        data = self.run_fake({"events": NORMAL[:2] + [{"type": "turn.failed", "error": {"message": CANARY}}]})
        self.assertEqual(data["outcome"], "turn_failed")
        self.assert_saved_safe(data)

    def test_nonzero_overrides_success(self):
        data = self.run_fake({"events": NORMAL, "exit": 9})
        self.assertEqual(data["outcome"], "nonzero_exit")
        self.assertEqual(data["exit_code"], 9)

    def test_invalid_json_and_truncated_line_distinct(self):
        data = self.run_fake({"events": NORMAL, "raw": "{oops}\n"})
        self.assertEqual(data["outcome"], "invalid_json")
        self.assertEqual(data["invalid_json_lines"], 1)
        self.assert_saved_safe(data)
        self.result = self.root / "result2"
        data = self.run_fake({"events": NORMAL, "raw": '{"type":"turn.started"}'})
        self.assertEqual(data["outcome"], "truncated_stream")

    def test_line_total_event_and_stderr_limits(self):
        cases = [({"raw": "x" * 5000 + "\n"}, Limits(max_line_bytes=1024), "line_bytes"),
                 ({"raw": ("{}\n" * 2000)}, Limits(max_stdout_bytes=1024), "stdout_bytes"),
                 ({"events": NORMAL}, Limits(max_events=2), "event_count"),
                 ({"flood_stderr": True}, Limits(max_stderr_bytes=8192), "stderr_bytes")]
        for index, (fixture, limits, reason) in enumerate(cases):
            with self.subTest(reason=reason):
                self.result = self.root / ("limits" + str(index))
                data = self.run_fake(fixture, limits=limits)
                self.assertEqual(data["outcome"], "limit_exceeded")
                self.assertIn(reason, data["limit_reasons"])
                self.assert_saved_safe(data)

    def test_timeout_kills_owned_child_and_grandchild(self):
        data = self.run_fake({"tree": True, "sleep": 120}, limits=Limits(timeout_seconds=2))
        self.assertEqual(data["outcome"], "timeout")
        pids = [int((self.workspace / name).read_text()) for name in ("child.pid", "grandchild.pid")]
        end = time.monotonic() + 3
        while any(alive(pid) for pid in pids) and time.monotonic() < end: time.sleep(.02)
        self.assertFalse(any(alive(pid) for pid in pids), "owned descendants survived timeout")

    def test_blocked_stdin_and_large_both_streams_do_not_deadlock(self):
        (self.workspace / "fixture.json").write_text(json.dumps({"ignore_stdin": True}))
        config = ObserverConfig(Path(sys.executable), self.workspace, self.result,
                                cli_version="codex-cli 0.166.0-alpha.6", limits=Limits(timeout_seconds=.3))
        data = run_observer(config, "p" * 900000)
        self.assertEqual(data["outcome"], "timeout")
        self.assertLess(data["wall_seconds"], 3)
        self.result = self.root / "both-streams"
        data = self.run_fake({"events": NORMAL[:2] + [{"type": "item.completed", "item": {"type": "reasoning", "text": CANARY}}] * 2000 + NORMAL[-2:],
                              "stderr": "e" * 300000})
        self.assertEqual(data["outcome"], "success")
        self.assertEqual(data["stderr_bytes"], 300000)
        self.assert_saved_safe(data)

    def test_unknown_extra_and_sensitive_fields_are_dropped(self):
        events = NORMAL + [{"type": CANARY, "message": CANARY},
                           {"type": "item.completed", "item": {"type": CANARY, "status": CANARY, "exit_code": CANARY}},
                           {"type": "item.completed", "item": {"type": "reasoning", "text": CANARY}},
                           {"type": "item.completed", "item": {"type": "error", "message": CANARY}}]
        data = self.run_fake({"events": events, "stderr": "authentication failed " + CANARY})
        self.assertEqual(data["outcome"], "success")
        self.assertEqual(data["unknown_event_count"], 1)
        self.assertEqual(data["unknown_item_count"], 1)
        self.assertEqual(data["item_counts"]["error"], 1)
        self.assertTrue(data["stderr_categories"]["auth"])
        self.assert_saved_safe(data)

    def test_missing_and_invalid_usage_are_null(self):
        events = NORMAL[:-1] + [{"type": "turn.completed", "usage": {"input_tokens": True, "output_tokens": -1, "cached_input_tokens": CANARY}}]
        data = self.run_fake({"events": events})
        self.assertTrue(all(v is None for v in data["usage"].values()))
        self.assert_saved_safe(data)

    def test_absent_cache_write_usage_remains_null(self):
        data = self.run_fake()
        self.assertIsNone(data["usage"]["cache_write_input_tokens"])
        self.assertEqual(data["usage_source_event"], "turn.completed")

    def test_thread_usage_snapshots_are_annotated_and_never_added(self):
        for index, amount in enumerate((100, 150)):
            self.result = self.root / ("snapshot" + str(index))
            events = NORMAL[:-1] + [{"type": "turn.completed", "usage": {"input_tokens": amount, "cache_write_input_tokens": index * 5}}]
            data = self.run_fake({"events": events}, resume_id=UUID, persistent=True)
            self.assertEqual(data["usage"]["input_tokens"], amount)
            self.assertEqual(data["usage"]["cache_write_input_tokens"], index * 5)
            self.assertEqual(data["usage_scope"], "cumulative_thread_snapshot")
        self.result = self.root / "unknown-version"
        data = self.run_fake(cli_version="codex-cli 0.157.1")
        self.assertEqual(data["usage_scope"], "unknown_do_not_sum")

    def test_duplicate_or_conflicting_terminals_rejected(self):
        for terminal in ({"type": "turn.completed"}, {"type": "turn.failed"}):
            self.result = self.root / ("terminal" + terminal["type"])
            data = self.run_fake({"events": NORMAL + [terminal]})
            self.assertEqual(data["outcome"], "protocol_error")

    def test_required_thread_turn_terminal_order(self):
        cases = [
            [NORMAL[-1]],
            [NORMAL[0], NORMAL[-1]],
            [NORMAL[1], NORMAL[0], NORMAL[-1]],
            [NORMAL[0], NORMAL[-1], NORMAL[1]],
            [NORMAL[0], NORMAL[0], NORMAL[1], NORMAL[-1]],
            [{"type": "thread.started", "thread_id": "invalid"}, NORMAL[1], NORMAL[-1]],
        ]
        for index, events in enumerate(cases):
            with self.subTest(index=index):
                self.result = self.root / ("order" + str(index))
                data = self.run_fake({"events": events})
                self.assertEqual(data["outcome"], "protocol_error")
                self.assertFalse(data["success"])

    def test_resume_must_emit_requested_identity(self):
        data = self.run_fake(resume_id="01234567-89ab-cdef-0123-456789abcdef")
        self.assertEqual(data["outcome"], "protocol_error")
        self.assertFalse(data["success"])

    def test_top_level_error_never_silently_succeeds(self):
        events = NORMAL[:-1] + [{"type": "error", "message": CANARY}] + NORMAL[-1:]
        data = self.run_fake({"events": events})
        self.assertEqual(data["outcome"], "stream_error")
        self.assertFalse(data["success"])
        self.assertEqual(data["event_counts"]["error"], 1)
        self.assert_saved_safe(data)

    def test_startup_item_error_before_turn_is_nonfatal(self):
        events = NORMAL[:1] + [{"type": "item.completed", "item": {"type": "error", "message": CANARY}}] + NORMAL[1:]
        data = self.run_fake({"events": events})
        self.assertEqual(data["outcome"], "success")
        self.assertEqual(data["item_counts"]["error"], 1)
        self.assert_saved_safe(data)

    def test_shared_daemon_is_disabled_before_exec(self):
        self.run_fake()
        args = self.launched_commands[-1]
        self.assertEqual(args[:3], [str(Path(sys.executable).resolve()), "--no-daemon", "exec"])
        self.assertNotIn(CANARY, " ".join(args))

    def test_exact_resume_guard_and_parent_options(self):
        data = self.run_fake(resume_id=UUID, persistent=True, sandbox="workspace-write")
        args = json.loads((self.workspace / "invocation.json").read_text())["argv"]
        self.assertEqual(args[:6], ["--sandbox", "workspace-write", "--cd", str(self.workspace), "--color", "never"])
        self.assertEqual(args[6:], ["resume", "--json", "--skip-git-repo-check", UUID, "-"])
        self.assertEqual(data["resume_id"], UUID)
        for value in ("last", "--last", "latest", UUID.upper(), "../" + UUID):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_fake(resume_id=value)

    def test_no_auth_or_global_mutation_and_no_overwrite(self):
        sentinel = self.root / "auth.json"
        sentinel.write_text(CANARY)
        previous = dict(os.environ)
        data = self.run_fake()
        self.assertEqual(sentinel.read_text(), CANARY)
        self.assertEqual(dict(os.environ), previous)
        with self.assertRaises(FileExistsError): self.run_fake()
        self.assert_saved_safe(data)

    def test_reject_relative_paths_traversal_links_and_bad_sandbox(self):
        for field, value in (("executable", Path("python")), ("workspace", Path(".")),
                             ("result_dir", self.root / ".." / "escape"), ("sandbox", "danger-full-access")):
            options = dict(executable=Path(sys.executable), workspace=self.workspace, result_dir=self.result,
                           cli_version="codex-cli 0.166.0-alpha.6")
            options[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): run_observer(ObserverConfig(**options), "x")
        linked = self.root / "linked"
        if os.name == "nt":
            result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                                     "New-Item -ItemType Junction -Path $env:OBSERVER_TEST_LINK -Target $env:OBSERVER_TEST_TARGET | Out-Null"],
                                    env={**os.environ, "OBSERVER_TEST_LINK": str(linked), "OBSERVER_TEST_TARGET": str(self.workspace)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            self.assertEqual(result.returncode, 0, "junction fixture creation failed")
        else:
            linked.symlink_to(self.workspace, target_is_directory=True)
        with self.assertRaises(ValueError):
            run_observer(ObserverConfig(Path(sys.executable), linked, self.result, cli_version="codex-cli 0.166.0-alpha.6"), "x")

    def test_profile_is_bounded_and_global(self):
        data = self.run_fake(profile="local-analysis", resume_id=UUID)
        args = json.loads((self.workspace / "invocation.json").read_text())["argv"]
        self.assertEqual(args[6:9], ["--profile", "local-analysis", "resume"])
        self.assertEqual(data["caller_declared_profile"], "local-analysis")
        for value in ("../escape", "--disable safety", "x" * 65):
            with self.assertRaises(ValueError): self.run_fake(profile=value)

    def test_surrogate_output_is_not_logged_or_matched(self):
        events = NORMAL[:-2] + [{"type": "item.completed", "item": {"type": "agent_message", "text": "\ud800"}}] + NORMAL[-1:]
        data = self.run_fake({"events": events})
        self.assertEqual(data["outcome"], "success")
        self.assertFalse(data["expected_final_matched"])
        self.assert_saved_safe(data)

    def test_default_never_retains_final_output(self):
        (self.workspace / "fixture.json").write_text(json.dumps({"events": NORMAL}))
        data = run_observer(ObserverConfig(Path(sys.executable), self.workspace, self.result, cli_version="codex-cli 0.166.0-alpha.6"), CANARY)
        self.assertIsNone(data["expected_final_matched"])
        self.assert_saved_safe(data)

    def test_version_is_verified_or_explicitly_supplied(self):
        with self.assertRaises(ValueError):
            run_observer(ObserverConfig(Path(sys.executable), self.workspace, self.result), "x")
        self.assertFalse(self.result.exists())
        with self.assertRaises(ValueError): self.run_fake(cli_version="codex-cli " + CANARY)


if __name__ == "__main__": unittest.main()
