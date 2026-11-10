import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import reproduce


class ReproduceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.package = self.root / "source" / "environment"
        self.source = self.package / "bundle" / "config.toml"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b'root = "{{CODEX_HOME}}"\n')
        self.destination = self.root / "Codex test (private)"
        self.entry = {
            "source": "bundle/config.toml",
            "target": "codex-home/config.toml",
            "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "executable": False,
            "render": "paths",
        }
        self.manifest(self.entry)

    def manifest(self, *entries):
        (self.package / "manifest.json").write_text(
            json.dumps({"schema_version": 1, "files": entries}), encoding="utf-8"
        )

    def operate(self, mode="plan", *, destination=None):
        return reproduce.operate(destination or self.destination, mode, self.package)

    def test_plan_apply_verify_and_detect_tampering(self):
        planned = self.operate()
        self.assertFalse(self.destination.exists())
        self.assertEqual(planned, self.operate("apply"))
        self.assertEqual(planned, self.operate("verify"))
        installed = self.destination / "codex-home" / "config.toml"
        self.assertEqual(
            installed.read_text(encoding="utf-8"),
            f'root = "{(self.destination / "codex-home").as_posix()}"\n',
        )
        receipt = json.loads((self.destination / "reproduction-receipt.json").read_bytes())
        digests = {row["target"]: row["sha256"] for row in receipt["files"]}
        self.assertEqual(digests["codex-home/config.toml"], reproduce.sha256(installed.read_bytes()))
        self.assertIn("launch.py", digests)
        installed.write_bytes(b"modified")
        with self.assertRaisesRegex(reproduce.ReproduceError, "installed file differs"):
            self.operate("verify")

    def test_existing_and_racing_destinations_are_preserved(self):
        self.destination.mkdir()
        with self.assertRaisesRegex(reproduce.ReproduceError, "already exists"):
            self.operate("apply")
        self.destination.rmdir()
        real_rename = reproduce.rename_new

        def create_before_publish(stage, destination):
            destination.mkdir()
            real_rename(stage, destination)

        with patch.object(reproduce, "rename_new", create_before_publish):
            with self.assertRaises(OSError):
                self.operate("apply")
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertEqual(list(self.root.glob(".codex-stage-*")), [])

    def test_interrupted_staging_leaves_no_destination(self):
        with patch.object(reproduce, "rename_new", side_effect=OSError("publish failed")):
            with self.assertRaisesRegex(OSError, "publish failed"):
                self.operate("apply")
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob(".codex-stage-*")), [])

    def test_bad_source_digest_fails_before_staging(self):
        self.source.write_bytes(b"replaced source")
        with self.assertRaisesRegex(reproduce.ReproduceError, "source checksum mismatch"):
            self.operate("apply")
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob(".codex-stage-*")), [])

    def test_rejects_portability_and_private_path_violations(self):
        for field, path in (
            ("source", "bundle/../secrets.toml"),
            ("source", "bundle/auth.json"),
            ("source", "outside/file.toml"),
            ("target", "/etc/config.toml"),
            ("target", "codex-home/skills\\escape/SKILL.md"),
            ("target", "codex-home/skills/SKILL.md:stream"),
            ("target", "codex-home/skills/AUX.txt"),
            ("target", "codex-home/sessions/anything"),
            ("target", "codex-home/.env.production"),
            ("target", "launch.py"),
        ):
            with self.subTest(field=field, path=path):
                self.manifest(self.entry | {field: path})
                with self.assertRaises(reproduce.ReproduceError):
                    self.operate()

    def test_rejects_case_and_file_directory_conflicts(self):
        for first, second in (
            ("codex-home/Skills/one", "codex-home/skills/two"),
            ("codex-home/skills", "codex-home/skills/SKILL.md"),
            ("codex-home/skills/SKILL.md", "codex-home/skills"),
            ("codex-home/config.toml", "codex-home/Config.toml"),
        ):
            with self.subTest(first=first, second=second):
                self.manifest(self.entry | {"target": first}, self.entry | {"target": second})
                with self.assertRaisesRegex(reproduce.ReproduceError, "conflicting target"):
                    self.operate()

    def test_refuses_install_under_active_codex_home(self):
        with patch.dict(os.environ, {"CODEX_HOME": str(self.root)}):
            with self.assertRaisesRegex(reproduce.ReproduceError, "outside active Codex home"):
                self.operate("apply")
        self.assertFalse(self.destination.exists())

    def test_refuses_install_into_source_checkout(self):
        destination = self.package.parent / "private-install"
        with self.assertRaisesRegex(reproduce.ReproduceError, "outside the source checkout"):
            self.operate("apply", destination=destination)
        self.assertFalse(destination.exists())

    def test_refuses_install_into_enclosing_source_checkout(self):
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(reproduce.ReproduceError, "outside the source checkout"):
            self.operate("apply")
        self.assertFalse(self.destination.exists())

    def test_rejects_template_code_injection_characters(self):
        for component in ('a"b', "a'b", "a`b", "a$b", "a%b"):
            if os.name == "nt" and '"' in component:
                continue
            with self.subTest(component=component):
                with self.assertRaisesRegex(reproduce.ReproduceError, "portable path characters"):
                    self.operate(destination=self.root / component)
        self.source.write_bytes(b'root = "{{UNRECOGNIZED}}"')
        self.manifest(self.entry | {"sha256": reproduce.sha256(self.source.read_bytes())})
        with self.assertRaisesRegex(reproduce.ReproduceError, "unknown template token"):
            self.operate()

    def test_rejects_hardlinked_source(self):
        other = self.root / "linked.toml"
        try:
            os.link(self.source, other)
        except OSError as error:
            self.skipTest(f"hardlinks unavailable: {error}")
        with self.assertRaisesRegex(reproduce.ReproduceError, "unlinked regular file"):
            self.operate()

    def test_rejects_source_link_and_destination_parent_link(self):
        safe_file = self.root / "outside.toml"
        safe_file.write_bytes(self.source.read_bytes())
        self.source.unlink()
        try:
            self.source.symlink_to(safe_file)
            link = self.root / "alias"
            link.symlink_to(self.source.parent, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        with self.assertRaisesRegex(reproduce.ReproduceError, "unlinked regular file"):
            self.operate()
        with self.assertRaisesRegex(reproduce.ReproduceError, "real directory"):
            self.operate("apply", destination=link / "child")

    @unittest.skipUnless(os.name == "nt", "Windows junction")
    def test_rejects_real_windows_junction_in_source_or_destination(self):
        junction = self.root / "junction"
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "New-Item -ErrorAction Stop -ItemType Junction -Path $env:REPRO_TEST_LINK "
             "-Target $env:REPRO_TEST_LINK_TARGET | Out-Null"],
            capture_output=True,
            env=dict(os.environ, REPRO_TEST_LINK=str(junction), REPRO_TEST_LINK_TARGET=str(self.source.parent)),
        )
        if result.returncode:
            self.skipTest("creating a junction is unavailable")
        self.addCleanup(junction.rmdir)
        self.assertTrue(reproduce.is_link(junction.lstat()))
        with self.assertRaisesRegex(reproduce.ReproduceError, "real directory"):
            self.operate("apply", destination=junction / "child")
        with self.assertRaisesRegex(reproduce.ReproduceError, "real directory"):
            reproduce.read_regular(junction / self.source.name)

    def test_verify_checks_managed_files_without_reading_runtime_state(self):
        self.operate("apply")
        unrelated = self.destination / "codex-home" / "auth.json"
        unrelated.write_bytes(b"fake account state created after launch")
        original_read = reproduce.read_regular

        def refuse_runtime_state(path):
            self.assertNotEqual(path, unrelated)
            return original_read(path)

        with patch.object(reproduce, "read_regular", refuse_runtime_state):
            self.operate("verify")

    def test_verify_checks_ownership_before_opening_managed_paths(self):
        self.destination.mkdir()
        (self.destination / "launch.py").write_bytes(b"unrelated file")
        original_read = reproduce.read_regular

        def refuse_unowned_file(path):
            if path.is_relative_to(self.destination):
                self.assertEqual(path.name, "reproduction-receipt.json")
            return original_read(path)

        with patch.object(reproduce, "read_regular", refuse_unowned_file):
            with self.assertRaisesRegex(reproduce.ReproduceError, "no configuration installation receipt"):
                self.operate("verify")

    def test_launcher_uses_isolated_home_and_forwards_selected_project(self):
        self.operate("apply")
        launch = self.destination / "launch.py"
        project = self.root / "outside project"
        project.mkdir()
        binary = str(self.root / ("codex.exe" if os.name == "nt" else "codex"))
        argv = [str(launch), "--project", str(project), "--codex", binary, "--", "login"]
        parent_env = {"HOME": "caller-home", "CODEX_HOME": "caller-codex", "OPENAI_API_KEY": "fake"}
        with (
            patch.object(sys, "argv", argv),
            patch.dict(os.environ, parent_env),
            patch("shutil.which", return_value=binary),
            patch("subprocess.call", return_value=0) as spawn,
        ):
            with self.assertRaises(SystemExit) as exit_status:
                runpy.run_path(str(launch), run_name="__main__")
            self.assertEqual(exit_status.exception.code, 0)
            self.assertEqual(os.environ["CODEX_HOME"], "caller-codex")
        command, = spawn.call_args.args
        env = spawn.call_args.kwargs["env"]
        self.assertEqual(command, [binary, "--no-daemon", "-c", 'cli_auth_credentials_store="file"', "login"])
        self.assertEqual(spawn.call_args.kwargs["cwd"], project)
        self.assertEqual(env["CODEX_HOME"], str(self.destination / "codex-home"))
        self.assertEqual(env["HOME"], "caller-home")
        self.assertNotIn("OPENAI_API_KEY", env)

    @unittest.skipUnless(os.name == "nt", "Windows pinned CLI")
    def test_launcher_prefers_receipted_native_binary_and_rejects_drift(self):
        expected = reproduce.sha256(b"fake native executable")
        launcher_bytes = reproduce.LAUNCHER.replace(reproduce.PINNED_CODEX_SHA256.encode(), expected.encode())
        with patch.object(reproduce, "LAUNCHER", launcher_bytes):
            self.operate("apply")
        launch = self.destination / "launch.py"
        install = self.destination / "codex-home/tools/codex-cli/0.157.1"
        binary = install / "bin" / "codex.exe"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"fake native executable")
        receipt = {"files": {"bin/codex.exe": expected}}
        (install / ".dependency-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        with (
            patch.object(sys, "argv", [str(launch), "--", "--version"]),
            patch("shutil.which", side_effect=AssertionError("unexpected PATH fallback")),
            patch("subprocess.call", return_value=0) as spawn,
        ):
            with self.assertRaises(SystemExit) as status:
                runpy.run_path(str(launch), run_name="__main__")
            self.assertEqual(status.exception.code, 0)
            self.assertEqual(spawn.call_args.args[0][0], str(binary))
            binary.write_bytes(b"modified")
            receipt["files"]["bin/codex.exe"] = reproduce.sha256(binary.read_bytes())
            (install / ".dependency-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as status:
                    runpy.run_path(str(launch), run_name="__main__")
            self.assertEqual(status.exception.code, 2)
            self.assertEqual(spawn.call_count, 1)

    @unittest.skipUnless(os.name == "nt", "Windows pinned Node")
    def test_launcher_prefers_verified_node_and_preserves_reader_path_option(self):
        expected = reproduce.sha256(b"node fixture")
        launcher_bytes = reproduce.LAUNCHER.replace(reproduce.PINNED_NODE_SHA256.encode(), expected.encode())
        with patch.object(reproduce, "LAUNCHER", launcher_bytes):
            self.operate("apply")
        launch = self.destination / "launch.py"
        node = self.destination / "codex-home/tools/agent-kit/runtime/node-v24.22.2-win-x64/node.exe"
        node.parent.mkdir(parents=True)
        node.write_bytes(b"node fixture")
        node.with_name(".dependency-receipt.json").write_text(
            json.dumps({"files": {"node.exe": expected}}), encoding="utf-8"
        )
        binary = str(self.root / "codex.exe")
        reader_path = str(self.root / "reader-tools")
        argv = [str(launch), "--codex", binary]
        with (
            patch.dict(os.environ, {"PATH": reader_path}),
            patch("shutil.which", return_value=binary),
            patch("subprocess.call", return_value=0) as spawn,
        ):
            for args in (argv, [*argv, "--inherit-node-path"]):
                with patch.object(sys, "argv", args):
                    with self.assertRaises(SystemExit) as status:
                        runpy.run_path(str(launch), run_name="__main__")
                    self.assertEqual(status.exception.code, 0)
            self.assertEqual(os.environ["PATH"], reader_path)
        preferred, inherited = [call.kwargs["env"]["PATH"] for call in spawn.call_args_list]
        self.assertEqual(preferred.split(os.pathsep), [str(node.parent), reader_path])
        self.assertEqual(inherited, reader_path)

    @unittest.skipIf(os.name == "nt", "POSIX executable mode")
    def test_installed_executable_flag(self):
        self.manifest(self.entry | {"executable": True})
        self.operate("apply")
        target = self.destination / "codex-home" / "config.toml"
        self.assertTrue(target.stat().st_mode & stat.S_IXUSR)
        target.chmod(0o600)
        with self.assertRaisesRegex(reproduce.ReproduceError, "mode differs"):
            self.operate("verify")


if __name__ == "__main__":
    unittest.main()
