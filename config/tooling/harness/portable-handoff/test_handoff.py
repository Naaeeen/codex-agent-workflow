import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import handoff as h


PROGRAM = b'import pathlib\np = pathlib.Path("numbers.txt")\npathlib.Path("answer.txt").write_bytes((str(sum(map(int, p.read_text().split()))) + "\\n").encode())\n'
ANSWER = b"42\n"


def spec():
    return {"inputs": ["main.py", "numbers.txt"], "contract": {
        "runtime": {"name": "CPython", "version": ">=3.11", "recipe": ["Use an existing Python 3.11+ interpreter; no installation or network needed."]},
        "command": {"argv": ["python", "main.py"], "cwd": ".", "timeout_seconds": 5},
        "outputs": [{"path": "answer.txt", "max_bytes": 100, "sha256": hashlib.sha256(ANSWER).hexdigest()}],
        "acceptance": ["answer.txt contains the UTF-8 bytes 42 followed by a newline."]}}


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "main.py").write_bytes(PROGRAM)
        (self.source / "numbers.txt").write_bytes(b"13 29\n")
        self.bundle = h.prepare(self.source, spec())

    def replay(self):
        workspace = self.root / "clean-replay"
        h.extract_data(h.validate_bundle(self.bundle), workspace)
        # The tests explicitly select this locally authored fixture. The package
        # has no executor and does not execute arbitrary bundle argv.
        run = subprocess.run([sys.executable, "-I", "main.py"], cwd=workspace,
                             timeout=5, capture_output=True, check=True)
        self.assertEqual(run.returncode, 0)
        return workspace

    def test_clean_cross_directory_replay_and_return(self):
        workspace = self.replay()
        result = h.collect(self.bundle, workspace)
        returned = self.root / "returned"
        h.extract_data(h.validate_result(self.bundle, result), returned)
        self.assertEqual((returned / "answer.txt").read_bytes(), ANSWER)

    def test_paths_secret_names_and_case_collisions(self):
        for value in ("../x", "/x", "C:/x", "C:x", "//server/x", "\\\\?\\C:\\x", "a/../x", "a//b",
                      "NUL", "COM1.txt", "a:stream", "a\\b", ".env", "x/.env.local", "auth.json",
                      "keys/private.pem", ".codex/config.toml", "x/", "a.", "a ", "CONIN$",
                      "conout$.txt", "COM\u00b9.txt", "LPT\u00b2.txt", "CON .txt"):
            with self.subTest(value=value), self.assertRaises(h.LedgerError):
                h.relative(value)
        for names in (["a", "A"], ["a", "a/b"], ["a/one.txt", "A/two.txt"]):
            with self.assertRaises(h.LedgerError): h.paths_unique(names)

    def test_missing_source(self):
        (self.source / "numbers.txt").unlink()
        with self.assertRaises(h.LedgerError): h.prepare(self.source, spec())

    def test_hardlink_source(self):
        os.link(self.source / "numbers.txt", self.source / "alias.txt")
        with self.assertRaises(h.LedgerError): h.prepare(self.source, spec())

    def test_symbolic_link_source(self):
        target = self.source / "numbers.txt"
        alias = self.source / "alias.txt"
        try:
            alias.symlink_to(target)
        except OSError:
            self.skipTest("Windows symlink privilege unavailable; separate junction test covers reparse directories")
        s = spec(); s["inputs"][1] = "alias.txt"
        with self.assertRaises(h.LedgerError): h.prepare(self.source, s)

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_junction_source(self):
        junction = self.source / "linked"
        run = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(self.source)],
                             capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
        s = spec(); s["inputs"][1] = "linked/numbers.txt"
        with self.assertRaises(h.LedgerError): h.prepare(self.source, s)

    def test_tamper_does_not_create_destination(self):
        bad = copy.deepcopy(self.bundle)
        bad["files"][1]["sha256"] = "0" * 64
        dest = self.root / "not-created"
        with self.assertRaises(h.LedgerError): h.extract_data(h.validate_bundle(bad), dest)
        self.assertFalse(dest.exists())

    def test_oversized_declared_and_actual_source(self):
        bad = copy.deepcopy(self.bundle)
        bad["files"][0]["size"] = h.MAX_FILE + 1
        with self.assertRaises(h.LedgerError): h.validate_bundle(bad)
        (self.source / "numbers.txt").write_bytes(b"x" * (h.MAX_FILE + 1))
        with self.assertRaises(h.LedgerError): h.prepare(self.source, spec())

    def test_existing_destination_and_package_unchanged(self):
        dest = self.root / "existing"; dest.mkdir()
        marker = dest / "main.py"; marker.write_bytes(b"preserve")
        with self.assertRaises(h.LedgerError): h.extract_data(h.validate_bundle(self.bundle), dest)
        self.assertEqual(marker.read_bytes(), b"preserve")
        path = self.root / "package.json"; path.write_bytes(b"preserve")
        with self.assertRaises(FileExistsError): h.save_new(path, h.canonical(self.bundle))
        self.assertEqual(path.read_bytes(), b"preserve")

    def test_unknown_output(self):
        workspace = self.replay(); (workspace / "extra.txt").write_text("extra")
        with self.assertRaises(h.LedgerError): h.collect(self.bundle, workspace)

    def test_unknown_empty_directory(self):
        workspace = self.replay(); (workspace / "extra").mkdir()
        with self.assertRaises(h.LedgerError): h.collect(self.bundle, workspace)

    def test_missing_output(self):
        workspace = self.replay(); (workspace / "answer.txt").unlink()
        with self.assertRaises(h.LedgerError): h.collect(self.bundle, workspace)

    def test_changed_input(self):
        workspace = self.replay(); (workspace / "numbers.txt").write_bytes(b"0")
        with self.assertRaises(h.LedgerError): h.collect(self.bundle, workspace)

    def test_invalid_result_and_binding(self):
        workspace = self.replay(); result = h.collect(self.bundle, workspace)
        for edit in (lambda r: r.update(bundle_sha256="0" * 64),
                     lambda r: r["files"][0].update(path="unexpected.txt"),
                     lambda r: r["files"][0].update(sha256="0" * 64)):
            bad = copy.deepcopy(result); edit(bad)
            with self.assertRaises(h.LedgerError): h.validate_result(self.bundle, bad)

    def test_bad_output_size_or_hash(self):
        workspace = self.replay()
        for data in (b"wrong\n", b"x" * 101):
            (workspace / "answer.txt").write_bytes(data)
            with self.assertRaises(h.LedgerError): h.collect(self.bundle, workspace)

    def test_duplicate_json_keys(self):
        path = self.root / "duplicate.json"; path.write_text('{"a":1,"a":2}')
        with self.assertRaises(h.LedgerError): h.load(path)

    def test_command_metadata_is_bounded_and_portable(self):
        for timeout in (0, 61, True, "5"):
            c = spec()["contract"]; c["command"]["timeout_seconds"] = timeout
            with self.assertRaises(h.LedgerError): h.contract(c)
        for argv in (["C:/python.exe", "main.py"], ["python", "../main.py"], ["/bin/python", "main.py"]):
            c = spec()["contract"]; c["command"]["argv"] = argv
            with self.assertRaises(h.LedgerError): h.contract(c)
        c = spec()["contract"]; c["command"]["cwd"] = "../outside"
        with self.assertRaises(h.LedgerError): h.contract(c)

    def test_hardlinked_output(self):
        workspace = self.replay()
        os.link(workspace / "answer.txt", self.root / "answer-alias.txt")
        with self.assertRaises(h.LedgerError): h.collect(self.bundle, workspace)

    def test_output_total_limit(self):
        bundle = copy.deepcopy(self.bundle)
        content = b"x" * h.MAX_FILE
        bundle["contract"]["outputs"] = [
            {"path": f"output{i}.txt", "max_bytes": h.MAX_FILE, "sha256": h.digest(content)}
            for i in range(9)]
        workspace = self.root / "large-outputs"
        h.extract_data(h.validate_bundle(bundle), workspace)
        for output in bundle["contract"]["outputs"]:
            (workspace / output["path"]).write_bytes(content)
        with self.assertRaises(h.LedgerError): h.collect(bundle, workspace)

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_destination_parent_junction(self):
        junction = self.root / "linked-destination"
        real = self.root / "real-destination"; real.mkdir()
        run = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(real)],
                             capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
        with self.assertRaises(h.LedgerError):
            h.extract_data(h.validate_bundle(self.bundle), junction / "output")
        self.assertFalse((real / "output").exists())

    def test_cli_validation_and_replay(self):
        s = self.root / "spec.json"; s.write_text(json.dumps(spec()))
        bundle = self.root / "bundle.json"
        base = [sys.executable, str(Path(h.__file__))]
        for argv in (["prepare", str(self.source), str(s), str(bundle)], ["verify", str(bundle)],
                     ["extract", str(bundle), str(self.root / "cli-replay")]):
            subprocess.run(base + argv, check=True, capture_output=True, timeout=5)
        subprocess.run([sys.executable, "-I", "main.py"], cwd=self.root / "cli-replay",
                       check=True, capture_output=True, timeout=5)
        result = self.root / "result.json"
        for argv in (["collect", str(bundle), str(self.root / "cli-replay"), str(result)],
                     ["verify-result", str(bundle), str(result)],
                     ["extract-result", str(bundle), str(result), str(self.root / "cli-return")]):
            subprocess.run(base + argv, check=True, capture_output=True, timeout=5)
        self.assertEqual((self.root / "cli-return" / "answer.txt").read_bytes(), ANSWER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
