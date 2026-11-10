import contextlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import install_dependencies as deps
import reproduce


class DependencyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.package = self.root / "source" / "environment"
        self.destination = self.root / "install"
        config = self.package / "bundle" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_bytes(b"[analytics]\nenabled = false\n")
        document = {"schema_version": 1, "files": [{
            "source": "bundle/config.toml", "target": "codex-home/config.toml",
            "sha256": reproduce.sha256(config.read_bytes()), "executable": False,
        }]}
        (self.package / "manifest.json").write_text(json.dumps(document), encoding="utf-8")
        reproduce.operate(self.destination, "apply", self.package)
        self.download = {
            "id": "tool", "kind": "download", "target": "codex-home/tools/tool",
            "assets": [{
                "format": "file", "url": "https://example.com/tool.exe",
                "output": "tool.exe", "sha256": reproduce.sha256(b"test asset"),
            }],
        }
        self.write_manifest(self.download)

    def write_manifest(self, *groups):
        document = {"schema_version": 1, "platform": "windows-x64", "groups": groups}
        (self.package / "dependencies.json").write_text(json.dumps(document), encoding="utf-8")

    def test_default_preview_never_downloads_or_creates_tool_directory(self):
        with patch.object(deps, "download", side_effect=AssertionError("unexpected download")):
            with contextlib.redirect_stdout(io.StringIO()) as result:
                deps.operate(self.destination, [], package=self.package)
        self.assertIn("tool [plan download]", result.getvalue())
        self.assertFalse((self.destination / "codex-home" / "tools").exists())

    def test_cli_dry_run_does_not_write_a_python_bytecode_cache(self):
        for module in (reproduce, deps):
            source = Path(module.__file__)
            (self.package.parent / source.name).write_bytes(source.read_bytes())
        env = os.environ.copy()
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        result = subprocess.run(
            [sys.executable, str(self.package.parent / "install_dependencies.py"), str(self.destination)],
            env=env, check=True, capture_output=True, text=True,
        )
        self.assertIn("tool [plan download]", result.stdout)
        self.assertFalse((self.package.parent / "__pycache__").exists())

    def test_setup_selects_prerequisites_and_can_skip_model_weights(self):
        groups = {
            "consumer": {"kind": "npm", "requires": ["tool"]},
            "tool": {"kind": "download"},
            "qmd-models": {"kind": "download"},
            "account": {"kind": "manual", "instructions": "Sign in."},
        }
        self.assertEqual(deps.setup_order(groups, ["consumer", "tool"], False), ["tool", "consumer"])
        self.assertEqual(deps.setup_order(groups, [], True), ["tool", "consumer"])
        with self.assertRaisesRegex(reproduce.ReproduceError, "requires manual steps"):
            deps.setup_order(groups, ["account"], False)
        with self.assertRaisesRegex(reproduce.ReproduceError, "while model weights are skipped"):
            deps.setup_order(groups, ["qmd-models"], True)

    @unittest.skipUnless(os.name == "nt" and shutil.which("pwsh"), "PowerShell Windows CLI")
    def test_setup_powershell_dry_run_preserves_source_and_new_target(self):
        for module in (reproduce, deps):
            source = Path(module.__file__)
            (self.package.parent / source.name).write_bytes(source.read_bytes())
        setup_script = Path(deps.__file__).with_name("setup.ps1")
        (self.package.parent / setup_script.name).write_bytes(setup_script.read_bytes())
        consumer = self.download | {"id": "consumer", "target": "codex-home/tools/consumer", "requires": ["tool"]}
        self.write_manifest(consumer, self.download)
        new_target = self.root / "new install"
        result = subprocess.run(
            [shutil.which("pwsh"), "-NoProfile", "-NonInteractive", "-File",
             str(self.package.parent / "setup.ps1"), "-Destination", str(new_target),
             "-Python313", sys.executable, "-Group", "consumer,tool"],
            check=True, capture_output=True, text=True,
        )
        self.assertLess(result.stdout.index("tool [download]"), result.stdout.index("consumer [download]"))
        self.assertFalse(new_target.exists())
        self.assertFalse((self.package.parent / "__pycache__").exists())

    @unittest.skipUnless(os.name == "nt" and platform.machine().lower() in {"amd64", "x86_64"}, "Windows x64 apply")
    def test_setup_missing_interpreter_fails_before_installation(self):
        group = {"id": "python", "kind": "pip", "target": "codex-home/tools/python", "python_version": "3.13.7"}
        self.write_manifest(group)
        new_target = self.root / "new install"
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(reproduce.ReproduceError, "requires Python 3.13.7"):
                deps.setup(new_target, [], {}, True, package=self.package)
        self.assertFalse(new_target.exists())

    def test_setup_probe_checks_zlib_used_for_wheel_reproduction(self):
        executable = self.root / "python.exe"
        executable.touch()
        result = subprocess.CompletedProcess([], 0, '["3.13.7","amd64",8,"wrong"]', "")
        with patch.object(deps.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(reproduce.ReproduceError, "must have zlib 1.3.1"):
                deps.setup_probe_pythons({"3.13.7": executable}, {"3.13.7": {"1.3.1"}})

    def test_setup_retry_rejects_changed_managed_configuration(self):
        config = self.destination / "codex-home/config.toml"
        config.write_bytes(b"changed")
        with self.assertRaisesRegex(reproduce.ReproduceError, "installed file differs"):
            deps.setup(self.destination, [], {}, package=self.package)

    def test_apply_requires_explicit_group(self):
        with self.assertRaisesRegex(reproduce.ReproduceError, "at least one explicit --group"):
            deps.operate(self.destination, [], apply=True, package=self.package)

    def test_retries_verify_existing_files_and_reject_drift(self):
        with patch.object(deps, "download", side_effect=lambda asset, path: path.write_bytes(b"test asset")):
            deps.install(self.download, self.destination, {})
        target = self.destination / self.download["target"]
        with patch.object(deps, "download", side_effect=AssertionError("unexpected download")):
            with contextlib.redirect_stdout(io.StringIO()) as result:
                deps.operate(self.destination, ["tool"], package=self.package)
        self.assertIn("tool [verified]", result.getvalue())
        (target / "tool.exe").write_bytes(b"modified")
        with self.assertRaisesRegex(reproduce.ReproduceError, "installation drift"):
            deps.operate(self.destination, ["tool"], package=self.package)

    def test_verify_refuses_unmanaged_files_before_hashing_them(self):
        with patch.object(deps, "download", side_effect=lambda asset, path: path.write_bytes(b"test asset")):
            deps.install(self.download, self.destination, {})
        target = self.destination / self.download["target"]
        (target / "auth.json").write_text("reader-owned sample", encoding="utf-8")
        with patch.object(deps, "tree_digests", side_effect=AssertionError("read unexpected files")):
            with self.assertRaisesRegex(reproduce.ReproduceError, "installation drift"):
                deps.check_installed(self.download, target, {})

    @unittest.skipUnless(os.name == "nt", "dependency application targets Windows x64")
    def test_existing_group_still_requires_its_installed_prerequisites(self):
        group = self.download | {"id": "consumer", "target": "codex-home/tools/consumer", "requires": ["tool"]}
        self.write_manifest(self.download, group)
        with patch.object(deps, "download", side_effect=lambda asset, path: path.write_bytes(b"test asset")):
            deps.install(group, self.destination, {})
        with self.assertRaisesRegex(reproduce.ReproduceError, "Install prerequisite tool first"):
            deps.operate(self.destination, ["consumer"], apply=True, package=self.package)

    def test_windows_venv_is_built_at_final_path_and_failed_group_is_removed(self):
        group = {"id": "venv", "kind": "pip", "target": "codex-home/tools/venv", "python_version": "3.14.3"}
        target = self.destination / group["target"]

        def fail_at_final_path(group, output, state, destination, managed):
            self.assertEqual(output, target)
            (output / "file").write_text("partial", encoding="utf-8")
            raise OSError("venv setup failed")

        with patch.object(deps, "populate", side_effect=fail_at_final_path):
            with self.assertRaisesRegex(OSError, "venv setup failed"):
                deps.install(group, self.destination, {})
        self.assertFalse(target.exists())

    def test_checksum_mismatch_detected_before_extraction(self):
        class Response(io.BytesIO):
            def geturl(self):
                return "https://example.com/tool.exe"

        opener = unittest.mock.Mock()
        opener.open.return_value = Response(b"different bytes")
        with patch.object(deps, "build_opener", return_value=opener):
            with self.assertRaisesRegex(reproduce.ReproduceError, "checksum mismatch"):
                deps.install(self.download, self.destination, {})
        self.assertFalse((self.destination / self.download["target"]).exists())

    def test_zip_traversal_and_links_are_rejected_before_copying(self):
        output = self.root / "out"
        output.mkdir()
        asset = {"format": "zip", "output": ".", "strip_prefix": "release"}
        for bad in ("release/../escape.exe", "release/link.exe"):
            path = self.root / "asset.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("release/tool.exe", b"valid")
                item = zipfile.ZipInfo(bad)
                item.external_attr = (stat.S_IFLNK << 16) if "link.exe" in bad else 0
                archive.writestr(item, b"not safe")
            with self.subTest(member=bad):
                with self.assertRaises(reproduce.ReproduceError):
                    deps.extract(asset, path, output)
                self.assertEqual(list(output.iterdir()), [])

    def test_zip_release_npmrc_and_exact_tar_member(self):
        zip_path = self.root / "node.zip"
        tar_path = self.root / "tool.tar.gz"
        output = self.root / "out"
        output.mkdir()
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("node/node_modules/npm/.npmrc", b"pinned npm project config")
        deps.extract({"format": "zip", "output": ".", "strip_prefix": "node"}, zip_path, output)
        self.assertTrue((output / "node_modules/npm/.npmrc").is_file())
        with tarfile.open(tar_path, "w:gz") as archive:
            for name in ("release/tool.exe", "release/readme.md"):
                member = tarfile.TarInfo(name)
                member.size = 4
                archive.addfile(member, io.BytesIO(b"data"))
        deps.extract(
            {"format": "tar.gz", "output": "bin/tool.exe", "strip_prefix": "release", "member": "tool.exe"},
            tar_path, output,
        )
        self.assertEqual((output / "bin/tool.exe").read_bytes(), b"data")
        self.assertFalse((output / "readme.md").exists())

    def test_recipe_inputs_reject_unpinned_or_local_sources(self):
        for contents in (b"-r /home/user/secrets.txt", b"demo @ file:///a.whl", b"demo==1.2"):
            with self.subTest(contents=contents):
                with self.assertRaises(reproduce.ReproduceError):
                    deps.pip_inputs({"recipe": "tooling/a"}, {"tooling/a": contents})
        self.assertEqual(
            deps.pip_inputs({"recipe": "tooling/a", "integrity": "pins"}, {"tooling/a": b"demo==1.2"}),
            (b"demo==1.2", False, {}),
        )
        lock = {"lockfileVersion": 3, "packages": {
            "": {}, "node_modules/demo": {"resolved": "file:///elsewhere", "integrity": "sha512-Qg=="},
        }}
        with self.assertRaisesRegex(reproduce.ReproduceError, "HTTPS"):
            deps.npm_inputs(
                {"recipe": "tooling/npm"},
                {"tooling/npm/package.json": b"{}", "tooling/npm/package-lock.json": json.dumps(lock).encode()},
            )

    def test_pip_bootstrap_installs_hashed_pip_before_main_requirements(self):
        group = {
            "id": "semgrep", "kind": "pip", "python_version": platform.python_version(),
            "recipe": "tooling/main.txt", "bootstrap_recipe": "tooling/bootstrap.txt",
            "wheels": ["tooling/tool-1.0-py3-none-any.whl"],
        }
        bootstrap = f"pip==26.3 --hash=sha256:{'a' * 64}\n".encode()
        main = f"tool==1.0 --hash=sha256:{'b' * 64}\n".encode()
        output = self.root / "venv"
        output.mkdir()
        state = self.root / "state"
        state.mkdir()
        observed = []

        def simulated_python(command, cwd, env):
            if "venv" in command:
                executable = output / "Scripts/python.exe"
                executable.parent.mkdir()
                executable.touch()
            else:
                observed.append((command[-1].read_bytes(), command))

        managed = {
            "tooling/main.txt": main,
            "tooling/bootstrap.txt": bootstrap,
            "tooling/tool-1.0-py3-none-any.whl": b"mock wheel",
        }
        with patch.object(deps, "run", side_effect=simulated_python):
            deps.populate(group, output, state, self.destination, managed)
        self.assertEqual([data for data, _ in observed], [bootstrap, main])
        self.assertIn("--force-reinstall", observed[0][1])
        self.assertIn("--require-hashes", observed[0][1])
        self.assertIn("--find-links", observed[1][1])
        self.assertEqual((state / "wheelhouse/tool-1.0-py3-none-any.whl").read_bytes(), b"mock wheel")
        with self.assertRaisesRegex(reproduce.ReproduceError, "exactly one"):
            deps.pip_bootstrap(group, {"tooling/bootstrap.txt": main})

    def test_clean_child_environment_does_not_inherit_auth_or_injection(self):
        state = self.root / "state"
        state.mkdir()
        values = {"OPENAI_API_KEY": "fake", "NPM_TOKEN": "fake", "PYTHONPATH": "outside", "NODE_OPTIONS": "outside"}
        with patch.dict(os.environ, values):
            env = deps.child_environment(state)
        for key in values:
            self.assertNotIn(key, env)
        self.assertTrue(Path(env["NPM_CONFIG_USERCONFIG"]).is_relative_to(state))
        self.assertTrue(Path(env["USERPROFILE"]).is_relative_to(state))
        if os.name == "nt":
            self.assertEqual(env["PATHEXT"], ".COM;.EXE;.BAT;.CMD")

    def test_npm_layout_only_publishes_node_modules(self):
        group = {
            "id": "npm", "kind": "npm", "layout": "node_modules",
            "target": "codex-home/tools/example/node_modules",
            "recipe": "codex-home/tools/example",
            "node": "codex-home/tools/node/node.exe", "npm": "codex-home/tools/node/npm-cli.js",
            "verified_copies": [{
                "sources": ["node_modules/absent/binding.node", "node_modules/platform/binding.node"],
                "target": "node_modules/sample/binding.node",
                "sha256": reproduce.sha256(b"expected binary"),
            }],
        }
        for key in ("node", "npm"):
            path = self.destination / group[key]
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_bytes(b"fake pinned binary")
        recipe = group["recipe"]
        managed = {
            f"{recipe}/package.json": b'{"private":true,"description":"Portable tool","type":"module"}',
            f"{recipe}/package-lock.json": b'{"lockfileVersion":3,"packages":{"":{}}}',
        }

        def mock_npm_run(command, cwd, env):
            self.assertIn("--ignore-scripts", command)
            self.assertTrue((cwd / "package-lock.json").is_file())
            module = cwd / "node_modules" / "sample"
            module.mkdir(parents=True)
            (module / "index.js").write_text("sample", encoding="utf-8")
            binary = cwd / "node_modules" / "platform" / "binding.node"
            binary.parent.mkdir()
            binary.write_bytes(b"expected binary")

        with patch.object(deps, "run", side_effect=mock_npm_run):
            deps.install(group, self.destination, managed)
        target = self.destination / group["target"]
        self.assertTrue((target / "sample/index.js").is_file())
        self.assertEqual((target / "sample/binding.node").read_bytes(), b"expected binary")
        self.assertTrue((target / deps.RECEIPT).is_file())
        self.assertFalse((target / "package-lock.json").exists())
        deps.check_installed(group, target, managed)

    def test_wheel_rebuild_updates_metadata_and_record(self):
        src = self.root / "upstream.whl"
        out = self.root / "patched.whl"
        with zipfile.ZipFile(src, "w") as archive:
            archive.writestr("tool/memories/code.py", b"example")
            archive.writestr("tool-1.0.dist-info/METADATA", b"Version: 1.0\r\n")
            archive.writestr("tool-1.0.dist-info/RECORD", b"discard old record")
        recipe = {
            "old_dist_info": "tool-1.0.dist-info", "new_dist_info": "tool-1.0+local.dist-info",
            "normalize_metadata_newlines": True, "record_order": "sorted",
            "timestamps": [{"from_index": 0, "value": [2026, 11, 5, 18, 17, 2]}],
            "metadata_replacements": [{"old": "Version: 1.0", "new": "Version: 1.0+local"}],
        }
        deps.rebuild_wheel(src, out, recipe)
        with zipfile.ZipFile(out) as rebuilt:
            metadata = "tool-1.0+local.dist-info/METADATA"
            record = "tool-1.0+local.dist-info/RECORD"
            self.assertEqual(rebuilt.namelist(), ["tool/memories/code.py", metadata, record])
            self.assertEqual(rebuilt.read(metadata), b"Version: 1.0+local\n")
            self.assertIn(b"tool/memories/code.py,sha256=", rebuilt.read(record))
            self.assertTrue(rebuilt.read(record).endswith(f"{record},,\n".encode()))


if __name__ == "__main__":
    unittest.main()
