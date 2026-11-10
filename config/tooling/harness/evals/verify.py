"""Run the real selftests with stdlib line coverage and preserve their exit code."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
import time
import trace
import threading
import unittest

ROOT = Path(__file__).resolve().parent


def main():
    evidence = ROOT / "verification"
    evidence.mkdir(exist_ok=True)
    stream = io.StringIO()
    tracer = trace.Trace(count=True, trace=False)
    selected = {os.path.normcase(str(path)) for path in
                [ROOT / "runner.py", ROOT / "test_runner.py", ROOT / "graders/checks.py", ROOT / "graders/__init__.py"]}
    # trace's default module-name ignore cache conflates our runner.py with
    # unittest/runner.py. Filter exact source paths instead, including I/O threads.
    def selected_trace(frame, event, arg):
        if event == "call" and os.path.normcase(os.path.abspath(frame.f_code.co_filename)) in selected:
            return tracer.localtrace
        return None
    tracer.globaltrace = selected_trace
    def run_tests():
        tests = unittest.defaultTestLoader.discover(str(ROOT), pattern="test_*.py")
        return unittest.TextTestRunner(stream=stream, verbosity=2).run(tests)
    started = time.monotonic()
    old_thread_trace = threading.gettrace()
    threading.settrace(selected_trace)
    try:
        result = tracer.runfunc(run_tests)
    finally:
        threading.settrace(old_thread_trace)
    elapsed = time.monotonic() - started
    coverage = io.StringIO()
    with redirect_stdout(coverage):
        tracer.results().write_results(show_missing=True, summary=True, coverdir=str(evidence / "trace"))
    (evidence / "test-output.txt").write_text(stream.getvalue(), encoding="utf-8")
    (evidence / "coverage-summary.txt").write_text(coverage.getvalue(), encoding="utf-8")
    report = {"recorded_at": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0],
              "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skips": len(result.skipped), "success": result.wasSuccessful(), "seconds": round(elapsed, 3),
              "model_calls": 0, "calibration_cases": 8, "golden_variants_per_case": 4,
              "coverage_kind": "stdlib executable-line coverage; not branch coverage"}
    (evidence / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(coverage.getvalue())
    if not result.wasSuccessful():
        print(stream.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
