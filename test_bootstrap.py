import tempfile
import unittest
from pathlib import Path
from bootstrap import install


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-bootstrap-test-")
        self.base = Path(self.temp.name)
        self.root = self.base / "kit"
        for path, content in {
            "templates/global-AGENTS.md": "# Agreements\n",
            "skills/example/SKILL.md": "---\nname: example\ndescription: Test example\n---\n",
            "config/agents-current-schema/reviewer.toml": 'name = "reviewer"\n',
        }.items():
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content, encoding="utf-8")
        self.target = self.base / "project"

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_writes_nothing(self):
        result = install(self.root, self.target)
        self.assertEqual(result["mode"], "preview")
        self.assertFalse(self.target.exists())
        self.assertEqual(len(result["files"]), 3)

    def test_apply_preserves_source_bytes(self):
        install(self.root, self.target, apply=True)
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), (self.root / "templates/global-AGENTS.md").read_bytes())
        self.assertTrue((self.target / ".agents/skills/example/SKILL.md").is_file())
        self.assertTrue((self.target / ".codex/agents/reviewer.toml").is_file())

    def test_existing_project_is_preserved(self):
        self.target.mkdir()
        keep = self.target / "keep.txt"
        keep.write_text("user work")
        with self.assertRaisesRegex(ValueError, "already exists"):
            install(self.root, self.target, apply=True)
        self.assertEqual(keep.read_text(), "user work")

    def test_incomplete_kit_fails_before_write(self):
        (self.root / "templates/global-AGENTS.md").unlink()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            install(self.root, self.target, apply=True)
        self.assertFalse(self.target.exists())

    def test_live_user_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "fresh project"):
            install(self.root, Path.home() / ".codex" / "new-profile", apply=True)


if __name__ == "__main__":
    unittest.main()
