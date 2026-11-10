#!/usr/bin/env python3
"""Run foreground local servers, wait for TCP listeners, run a command, clean up.

Usage: python with_server.py --server "npm run dev" --port 5173 -- python test.py
Repeat --server/--port for multiple servers. Server output is discarded; run a
failing server directly for its logs. TCP readiness does not establish UI readiness.
"""

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time


class Cancelled(Exception):
    def __init__(self, signum):
        self.signum = signum


class Cancellation:
    """Record signals without interrupting process creation or cleanup."""

    def __init__(self):
        self.signum = None

    def record(self, signum, frame):
        if self.signum is None:
            self.signum = signum

    def check(self):
        if self.signum is not None:
            raise Cancelled(self.signum)


def port_is_open(port):
    """Check both loopback families; never terminate a listener by its port."""
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return True
        except OSError:
            pass
    return False


class WindowsJob:
    """Own a Windows process tree, including children surviving their shell."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class BasicLimit(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                        ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class ExtendedLimit(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", BasicLimit), ("IoInfo", IoCounters),
                        ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                          wintypes.DWORD], wintypes.BOOL),
            "OpenProcess": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits),
                                                ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, process):
        import ctypes
        # Open a public OS handle rather than rely on Popen's private attributes.
        handle = self.api.OpenProcess(0x0101, False, process.pid)  # SET_QUOTA | TERMINATE
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.api.AssignProcessToJobObject(self.handle, handle):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self.api.CloseHandle(handle)

    def stop(self):
        import ctypes
        if self.handle and not self.api.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


class OwnedProcess:
    def __init__(self, command, quiet=True):
        self.job = None
        self.process = None
        if os.name == "nt":
            self.job = WindowsJob()
            try:
                # The supervisor cannot start the shell until assignment succeeds.
                self.process = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), "--_server-supervisor"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL if quiet else None,
                    stderr=subprocess.DEVNULL if quiet else None,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                self.job.assign(self.process)
                self.process.stdin.write(json.dumps(command).encode("utf-8"))
                self.process.stdin.close()
            except BaseException:
                if self.process is not None:
                    if self.process.stdin and not self.process.stdin.closed:
                        self.process.stdin.close()
                    self.process.kill()
                    self.process.wait(timeout=5)
                self.job.close()
                raise
        else:
            self.process = subprocess.Popen(command, shell=isinstance(command, str), start_new_session=True,
                                            stdin=subprocess.DEVNULL,
                                            stdout=subprocess.DEVNULL if quiet else None,
                                            stderr=subprocess.DEVNULL if quiet else None)

    def wait_ready(self, port, timeout, cancellation):
        deadline = time.monotonic() + timeout
        while True:
            cancellation.check()
            code = self.process.poll()
            if code is not None:
                raise RuntimeError(f"Server on port {port} exited before readiness (exit {code})")
            if port_is_open(port) and self.process.poll() is None:
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(f"Server on port {port} did not listen within {timeout}s")
            time.sleep(min(0.1, remaining))

    def stop(self):
        if self.job:
            try:
                self.job.stop()
                self.process.wait(timeout=5)
            finally:
                self.job.close()
            return
        # The shell may already be gone while its foreground children remain.
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description="Run a command with foreground local servers")
    parser.add_argument("--server", action="append", dest="servers", required=True,
                        help="Foreground shell command (repeatable; keep secrets out of arguments)")
    parser.add_argument("--port", action="append", dest="ports", type=int, required=True,
                        help="Local listening port for each server (repeatable)")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Positive startup timeout per server in seconds (default: 30)")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("No command specified to run")
    if len(args.servers) != len(args.ports):
        parser.error("Number of --server and --port arguments must match")
    if any(not command.strip() for command in args.servers):
        parser.error("Server commands must not be empty")
    if any(not 1 <= port <= 65535 for port in args.ports):
        parser.error("Ports must be between 1 and 65535")
    if len(set(args.ports)) != len(args.ports):
        parser.error("Each server requires a distinct port")
    if args.timeout <= 0:
        parser.error("Timeout must be positive")

    cancellation = Cancellation()
    handled_signals = [signal.SIGINT]
    if os.name != "nt":
        handled_signals.append(signal.SIGTERM)
    previous_handlers = {signum: signal.signal(signum, cancellation.record)
                         for signum in handled_signals}
    servers = []
    code = 1
    try:
        # Check all ports first, so a later conflict starts no earlier servers.
        for port in args.ports:
            cancellation.check()
            if port_is_open(port):
                raise RuntimeError(f"Port {port} is already in use; no servers were started")
        for index, (command, port) in enumerate(zip(args.servers, args.ports), 1):
            cancellation.check()
            print(f"Starting server {index}/{len(args.servers)} on port {port}", flush=True)
            server = OwnedProcess(command)
            servers.append(server)
            cancellation.check()
            server.wait_ready(port, args.timeout, cancellation)
        cancellation.check()
        print(f"All {len(servers)} server(s) listening; running command", flush=True)
        command = OwnedProcess(args.command, quiet=False)
        servers.append(command)
        while True:
            cancellation.check()
            try:
                code = command.process.wait(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                pass
    except Cancelled as error:
        print("Interrupted", file=sys.stderr)
        code = 128 + error.signum
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
    except (OSError, subprocess.SubprocessError) as error:
        # Exception text can contain an entire command, arguments, or secrets.
        print(f"Error: process operation failed ({type(error).__name__}, "
              f"code {getattr(error, 'winerror', None) or getattr(error, 'errno', None)})",
              file=sys.stderr)
    finally:
        failures = 0
        for server in reversed(servers):
            try:
                server.stop()
            except (OSError, subprocess.SubprocessError):
                failures += 1
        if failures:
            print(f"Error: {failures} process group(s) could not be fully cleaned up", file=sys.stderr)
            if code == 0:
                code = 1
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    return code


if __name__ == "__main__":
    if os.name == "nt" and sys.argv[1:] == ["--_server-supervisor"]:
        # Read EOF only after our parent has attached us to its non-breakaway Job.
        command = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        sys.exit(subprocess.run(command, shell=isinstance(command, str), stdin=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW).returncode)
    sys.exit(main())
