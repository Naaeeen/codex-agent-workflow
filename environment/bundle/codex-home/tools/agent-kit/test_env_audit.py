"""Behavioral contract tests; every fixture is disposable and synthetic."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import env_audit


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ToolkitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "root"
        self.root.mkdir()
        self.backup = self.base / "backup"

    def write(self, relative: str, data: str = "original") -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf-8")
        return target

    def test_audit_redacts_values_and_reports_safe_metadata(self) -> None:
        secret = "secret_" + "SENTINEL_DO_NOT_PRINT"  # Synthetic test canary
        self.write("config.toml", f'''model = "{secret}"
[mcp_servers.demo]
command = "npx"
args = ["pkg@latest", "{secret}"]
url = "https://{secret}.invalid"
enabled = false
[mcp_servers.demo.env]
TOKEN = "{secret}"
[agents.checker]
config_file = "agents/checker.toml"
''')
        self.write("agents/checker.toml", "[settings]\n")
        self.write("skills/one/SKILL.md", "---\nname: repeated\ndescription: A useful description.\n---\n[missing](absent.md)\n")
        agents = self.base / "agent_skills"
        (agents / "two").mkdir(parents=True)
        (agents / "two/SKILL.md").write_text("---\nname: repeated\ndescription: Another description.\n---\n", encoding="utf-8")
        report = env_audit.audit(self.root, agents)
        serialized = json.dumps(report)
        self.assertNotIn(secret, serialized)
        self.assertNotIn("https://", serialized)
        self.assertNotIn("TOKEN", serialized)
        self.assertEqual(report["config"]["top_level_keys"], ["agents", "mcp_servers", "model"])
        self.assertEqual(report["config"]["mcp_servers"], [{"name": "demo", "enabled": False, "transport": "http", "floating_latest": True}])
        self.assertEqual(report["roles"], [{"name": "checker", "config_file_exists": True, "status": "present"}])
        self.assertEqual(report["duplicate_skill_names"], ["repeated"])
        self.assertEqual(len(report["skills"]), 2)
        self.assertTrue(any(item["code"] == "missing_reference" for item in report["issues"]))
        self.assertTrue(all("description" not in item for item in report["skills"]))

    def test_audit_bad_frontmatter_and_invalid_toml_do_not_echo_content(self) -> None:
        self.write("config.toml", "secret='unclosed")
        self.write("skills/bad/SKILL.md", "---\nname: bad\nsecret='redact_me'\n")
        report = env_audit.audit(self.root, self.base / "absent")
        self.assertFalse(report["config"]["valid"])
        self.assertTrue(any(item["code"] == "bad_frontmatter" for item in report["issues"]))
        self.assertNotIn("redact_me", json.dumps(report))

    def test_audit_untrusted_metadata_names_are_redacted(self) -> None:
        self.write("config.toml", '''"https://synthetic-key.invalid" = "private"
[mcp_servers."https://synthetic-server.invalid"]
command = "private"
[agents."https://synthetic-role.invalid"]
config_file = "missing.toml"
''')
        self.write("skills/bad/SKILL.md", "---\nname: API_KEY_CANARY\ndescription: test\n---\n")
        report = env_audit.audit(self.root, self.base / "absent")
        serialized = json.dumps(report)
        self.assertNotIn("https://", serialized)
        self.assertNotIn("API_KEY_CANARY", serialized)
        self.assertIn("redacted", serialized)

    def test_audit_redacts_sensitive_path_components_without_false_duplicates(self) -> None:
        self.write("skills/API_KEY_CANARY/SKILL.md", "---\nname: API_KEY_ONE\ndescription: one\n---\n[missing](absent.md)\n")
        self.write("skills/other/SKILL.md", "---\nname: https://synthetic.invalid\ndescription: two\n---\n")
        report = env_audit.audit(self.root, self.base / "absent")
        self.assertNotIn("API_KEY_CANARY", json.dumps(report))
        self.assertEqual(report["duplicate_skill_names"], [])

    def test_audit_ignores_links_inside_code_examples(self) -> None:
        self.write("skills/good/SKILL.md", "---\nname: good\ndescription: test\n---\n```markdown\n[example](fake-in-code.md)\n```\n`[inline](fake-inline.md)`\n~~~text\n[other](fake-tilde.md)\n~~~\n[real](actually-missing.md)\n")
        report = env_audit.audit(self.root, self.base / "absent")
        missing = [item for item in report["issues"] if item["code"] == "missing_reference"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["line"], 12)

    def test_fence_with_trailing_text_does_not_close_code_block(self) -> None:
        self.write("skills/good/SKILL.md", "---\nname: good\ndescription: test\n---\n```text\n```not-a-closing-fence\n[example](inside-code.md)\n```\n[real](outside-code.md)\n")
        report = env_audit.audit(self.root, self.base / "absent")
        self.assertEqual([item["line"] for item in report["issues"] if item["code"] == "missing_reference"], [9])

    def test_reference_checks_allow_sensitive_document_names_without_reading(self) -> None:
        canary = "REFERENCE_CONTENT_CANARY_MUST_NOT_BE_READ_OR_PRINTED"
        references = {
            self.write("skills/good/references/identity-and-sessions.md", canary),
            self.write("skills/good/references/authentication.md", canary),
        }
        self.write("skills/good/SKILL.md", "---\nname: good\ndescription: test\n---\n[session](references/identity-and-sessions.md)\n[auth](references/authentication.md)\n")
        original_open = Path.open
        def reject_reference_content(path: Path, *args, **kwargs):
            self.assertNotIn(path, references, "Reference existence must not read document contents")
            return original_open(path, *args, **kwargs)
        with mock.patch.object(Path, "open", reject_reference_content):
            report = env_audit.audit(self.root, self.base / "absent")
        self.assertEqual(report["issues"], [])
        self.assertNotIn(canary, json.dumps(report))

    def test_reference_name_exception_preserves_path_boundaries(self) -> None:
        self.write("skills/good/SKILL.md", "---\nname: good\ndescription: test\n---\n[missing](references/auth-missing.md)\n[escape](../sessions.md)\n[absolute](/sessions.md)\n")
        report = env_audit.audit(self.root, self.base / "absent")
        self.assertEqual([(item["code"], item["line"]) for item in report["issues"]], [
            ("missing_reference", 5), ("unsafe_reference", 6), ("unsafe_reference", 7),
        ])

    def test_role_absolute_paths_are_scoped_to_codex_home(self) -> None:
        inside = self.write("agents/reviewer.toml", "model = 'local'\n")
        outside = self.base / "outside.toml"
        outside.write_text("must not read", encoding="utf-8")
        self.write("config.toml", f"[agents.inside]\nconfig_file = {json.dumps(str(inside))}\n[agents.outside]\nconfig_file = {json.dumps(str(outside))}\n")
        report = env_audit.audit(self.root, self.base / "absent")
        self.assertEqual(report["roles"], [
            {"name": "inside", "config_file_exists": True, "status": "present"},
            {"name": "outside", "config_file_exists": False, "status": "outside_scope"},
        ])
        self.assertNotIn(str(outside), json.dumps(report))

    def test_snapshot_and_rollback_restore_file(self) -> None:
        target = self.write("config.toml", "old")
        result = env_audit.snapshot(self.root, self.backup, ["config.toml"])
        self.assertEqual(result["files"]["config.toml"], digest(b"old"))
        target.write_text("new", encoding="utf-8")
        env_audit.rollback(self.backup, self.root, {"config.toml": digest(b"new")})
        self.assertEqual(target.read_text(), "old")
        self.assertTrue((self.backup / "manifest.json").is_file())

    def test_snapshot_absent_file_then_rollback_deletes_exact_new_file(self) -> None:
        env_audit.snapshot(self.root, self.backup, ["new.toml"])
        target = self.write("new.toml", "new")
        env_audit.rollback(self.backup, self.root, {"new.toml": digest(b"new")})
        self.assertFalse(target.exists())

    def test_rollback_null_means_expected_absent(self) -> None:
        self.write("old.toml", "old")
        env_audit.snapshot(self.root, self.backup, ["old.toml"])
        (self.root / "old.toml").unlink()
        env_audit.rollback(self.backup, self.root, {"old.toml": None})
        self.assertEqual((self.root / "old.toml").read_text(), "old")

    def test_rollback_drift_is_checked_before_any_restore(self) -> None:
        a = self.write("a.toml", "a old")
        b = self.write("b.toml", "b old")
        env_audit.snapshot(self.root, self.backup, ["a.toml", "b.toml"])
        a.write_text("a new", encoding="utf-8")
        b.write_text("unexpected", encoding="utf-8")
        with self.assertRaises(env_audit.AuditError):
            env_audit.rollback(self.backup, self.root, {"a.toml": digest(b"a new"), "b.toml": digest(b"b new")})
        self.assertEqual(a.read_text(), "a new")
        self.assertEqual(b.read_text(), "unexpected")

    def test_rollback_refuses_tampered_backup_before_any_restore(self) -> None:
        a = self.write("a.toml", "a old")
        b = self.write("b.toml", "b old")
        env_audit.snapshot(self.root, self.backup, ["a.toml", "b.toml"])
        a.write_text("a new", encoding="utf-8")
        b.write_text("b new", encoding="utf-8")
        (self.backup / "files/b.toml").write_text("tampered", encoding="utf-8")
        with self.assertRaises(env_audit.AuditError):
            env_audit.rollback(self.backup, self.root, {"a.toml": digest(b"a new"), "b.toml": digest(b"b new")})
        self.assertEqual(a.read_text(), "a new")

    def test_expected_manifest_must_cover_snapshot_exactly(self) -> None:
        self.write("a.toml")
        env_audit.snapshot(self.root, self.backup, ["a.toml"])
        for expected in ({}, {"a.toml": digest(b"original"), "extra.toml": None}):
            with self.assertRaises(env_audit.AuditError):
                env_audit.rollback(self.backup, self.root, expected)

    def test_snapshot_rejects_traversal_absolute_and_sensitive_files(self) -> None:
        for index, relative in enumerate(["../outside", "/absolute", "C:\\absolute", "//server/share", "a/../b", "a//b", "./a", "con.txt", "LPT1", "a.", "a ", "a:stream", "auth.json", "settings.auth.json", "foo.secrets.toml", "cache.sessions/data.jsonl", "nested/secrets.toml", "sessions/x.json", "state.db", "state.sqlite3", "state.db-wal", ".env"]):
            with self.subTest(relative=relative):
                backup = self.base / f"backup-{index}"
                with self.assertRaises(env_audit.AuditError):
                    env_audit.snapshot(self.root, backup, [relative])
                self.assertFalse(backup.exists())

    def test_sensitive_root_is_rejected(self) -> None:
        sensitive_root = self.base / "sessions"
        sensitive_root.mkdir()
        (sensitive_root / "ordinary.jsonl").write_text("private", encoding="utf-8")
        with self.assertRaises(env_audit.AuditError):
            env_audit.snapshot(sensitive_root, self.backup, ["ordinary.jsonl"])
        self.assertFalse(self.backup.exists())

    def test_duplicate_paths_are_rejected_case_insensitively(self) -> None:
        self.write("a.toml")
        with self.assertRaises(env_audit.AuditError):
            env_audit.snapshot(self.root, self.backup, ["a.toml", "A.toml"])
        self.assertFalse(self.backup.exists())

    def test_snapshot_refuses_hardlinks(self) -> None:
        source = self.write("a.toml")
        target = self.root / "b.toml"
        try:
            target.hardlink_to(source)
        except (OSError, NotImplementedError):
            self.skipTest("OS does not permit creating hardlinks")
        with self.assertRaises(env_audit.AuditError):
            env_audit.snapshot(self.root, self.backup, ["b.toml"])
        self.assertFalse(self.backup.exists())

    def test_modified_new_file_is_not_deleted(self) -> None:
        env_audit.snapshot(self.root, self.backup, ["new.toml"])
        target = self.write("new.toml", "changed after expected hash")
        with self.assertRaises(env_audit.AuditError):
            env_audit.rollback(self.backup, self.root, {"new.toml": digest(b"expected")})
        self.assertEqual(target.read_text(), "changed after expected hash")

    def test_corrupt_manifest_cannot_escape_root(self) -> None:
        self.write("a.toml")
        env_audit.snapshot(self.root, self.backup, ["a.toml"])
        manifest_path = self.backup / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"] = {"../outside": None}
        manifest["modes"] = {}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(env_audit.AuditError):
            env_audit.rollback(self.backup, self.root, {"../outside": None})

    def test_audit_skips_sensitive_subdirectories_and_block_description(self) -> None:
        self.write("skills/auth/SKILL.md", "this must not be read")
        self.write("skills/good/SKILL.md", "---\nname: good\ndescription: >\n  A first line\n  and a second line\n---\n")
        report = env_audit.audit(self.root, self.base / "absent")
        self.assertEqual([item["name"] for item in report["skills"]], ["good"])
        self.assertGreater(report["skills"][0]["description_length"], 20)

    def test_nested_absent_file_can_be_restored_and_then_deleted(self) -> None:
        env_audit.snapshot(self.root, self.backup, ["new/nested/file.toml"])
        target = self.write("new/nested/file.toml", "created")
        env_audit.rollback(self.backup, self.root, {"new/nested/file.toml": digest(b"created")})
        self.assertFalse(target.exists())

    def test_snapshot_requires_empty_separate_backup_directory(self) -> None:
        self.write("config.toml")
        self.backup.mkdir()
        (self.backup / "unrelated").write_text("preserve", encoding="utf-8")
        with self.assertRaises(env_audit.AuditError):
            env_audit.snapshot(self.root, self.backup, ["config.toml"])
        with self.assertRaises(env_audit.AuditError):
            env_audit.snapshot(self.root, self.root / "backup", ["config.toml"])

    def test_symlinks_are_not_followed_by_audit_or_snapshot(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text("---\nname: outside\ndescription: private\n---\n", encoding="utf-8")
        (self.root / "skills").mkdir()
        link = self.root / "skills/linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("OS does not permit creating symlinks")
        report = env_audit.audit(self.root, self.base / "absent")
        self.assertEqual(report["skills"], [])
        with self.assertRaises(env_audit.AuditError):
            env_audit.snapshot(self.root, self.backup, ["skills/linked/SKILL.md"])

    def test_cli_outputs_only_json_and_safe_error_code(self) -> None:
        script = Path(env_audit.__file__)
        result = subprocess.run([sys.executable, str(script), "snapshot", "--root", str(self.root), "--backup-dir", str(self.backup), "--paths", "../secret"], capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["error"], "unsafe_relative_path")
        self.assertEqual(result.stderr, "")

    def test_cli_audit_snapshot_and_rollback_round_trip(self) -> None:
        script = Path(env_audit.__file__)
        target = self.write("config.toml", 'model = "original"\n')
        def invoke(*arguments: str) -> dict:
            result = subprocess.run([sys.executable, str(script), *arguments], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(result.stderr, "")
            return json.loads(result.stdout)
        report = invoke("audit", "--codex-home", str(self.root), "--agent-skills", str(self.base / "absent"))
        self.assertEqual(report["config"]["top_level_keys"], ["model"])
        invoke("snapshot", "--root", str(self.root), "--backup-dir", str(self.backup), "--paths", "config.toml")
        target.write_text('model = "changed"\n', encoding="utf-8")
        expected = self.base / "expected.json"
        expected.write_text(json.dumps({"config.toml": digest(target.read_bytes())}), encoding="utf-8")
        invoke("rollback", "--root", str(self.root), "--backup-dir", str(self.backup), "--expected-current", str(expected))
        self.assertEqual(target.read_text(), 'model = "original"\n')


if __name__ == "__main__":
    unittest.main()
