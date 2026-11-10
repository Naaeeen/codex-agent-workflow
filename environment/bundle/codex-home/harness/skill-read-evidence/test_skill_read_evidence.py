"""Behavioral tests use disposable fake skills, never the user's skill files."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
import unittest
from unittest import mock

from skill_read_evidence import SkillReadEvidenceCollector


BODY = """---
name: example
description: This metadata description alone must not prove a content read.
---
# Example skill

Read the project requirements carefully before selecting the smallest useful implementation, and preserve unrelated changes throughout the work.

Run the focused verification checks after editing the relevant files, then report the observed result and any remaining uncertainty to the user.
"""


def quote_ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


class SkillReadEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = shutil.which("pwsh") or shutil.which("powershell")
        if not cls.shell:
            raise unittest.SkipTest("A local PowerShell parser is required")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-read-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "A skill's folder" / "SKILL.md"
        self.skill.parent.mkdir()
        self.skill.write_text(BODY, encoding="utf-8")
        self.unknown = self.root / "unregistered" / "SKILL.md"
        self.unknown.parent.mkdir()
        self.unknown.write_text(BODY.replace("Example skill", "Other skill"), encoding="utf-8")
        self.collector = SkillReadEvidenceCollector({"known-skill": self.skill})
        self.read = "Get-Content -LiteralPath " + quote_ps(str(self.skill))

    def collect(self, command=None, output=BODY, exit_code=0):
        result = self.collector.collect(self.read if command is None else command, output, exit_code)
        self.assertEqual(set(result), {"confirmed_reads", "unknown_reads_count", "classification"})
        # Public evidence must never contain command text, output, or filesystem paths.
        serialized = json.dumps(result)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("Read the project", serialized)
        return result

    def assert_confirmed(self, result):
        self.assertEqual(result, {"confirmed_reads": ["known-skill"], "unknown_reads_count": 0, "classification": "CONFIRMED"})

    def assert_unknown(self, result):
        self.assertEqual(result["confirmed_reads"], [])
        self.assertGreater(result["unknown_reads_count"], 0)
        self.assertEqual(result["classification"], "INCONCLUSIVE")

    def test_literal_quoted_path(self):
        self.assert_confirmed(self.collect())

    def test_real_native_get_content_output(self):
        # This fixed, local fixture script only reads its explicitly supplied file.
        reader = self.root / "fixture-reader.ps1"
        reader.write_text("param([string]$FixturePath)\nGet-Content -LiteralPath $FixturePath\n", encoding="utf-8")
        options = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        result = subprocess.run([self.shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(reader), str(self.skill)], capture_output=True, text=True, encoding="utf-8", timeout=15, check=False, **options)
        self.assertEqual(result.returncode, 0)
        self.assert_confirmed(self.collect(output=result.stdout))

    def test_aliases_and_literal_path_switches(self):
        for command in ["cat " + quote_ps(str(self.skill)), "type -Path " + quote_ps(str(self.skill)), self.read + " -Raw", self.read + " -Encoding utf8 -TotalCount 20 -ErrorAction Stop"]:
            with self.subTest(command=command):
                self.assert_confirmed(self.collect(command))

    def test_native_powershell_wrapper(self):
        for name in ["pwsh", "powershell.exe"]:
            with self.subTest(name=name):
                self.assert_confirmed(self.collect(name + " -NoLogo -NoProfile -NonInteractive -Command " + quote_ps(self.read)))

    def test_nested_wrapper(self):
        nested = "powershell -NoProfile -Command " + quote_ps(self.read)
        self.assert_confirmed(self.collect("pwsh -Command " + quote_ps(nested)))

    def test_native_display_quoted_executable_envelope(self):
        command = shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", "-Command", self.read])
        self.assertTrue(command.startswith("'"))
        self.assert_confirmed(self.collect(command))

    def test_native_display_preserves_embedded_quotes(self):
        path = str(self.skill).replace("\\", "/")
        script = 'Get-Content -LiteralPath "' + path + '"'
        command = shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", "-NoProfile", "-NonInteractive", "-Command", script])
        self.assert_confirmed(self.collect(command))

    def test_native_display_rejects_extra_arguments(self):
        for arguments in [
            ["-Command", self.read, ";", "Write-Output", BODY],
            ["-File", "anything.ps1"],
            ["-EncodedCommand", "Zm9v"],
            ["-ExecutionPolicy", "Bypass", "-Command", self.read],
        ]:
            with self.subTest(arguments=arguments):
                self.assert_unknown(self.collect(shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", *arguments])))

    def test_native_display_cannot_bypass_inner_rules(self):
        command = shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", "-Command", self.read + " | Out-Null; Write-Output " + quote_ps(BODY)])
        self.assert_unknown(self.collect(command))

    def test_native_display_only_at_event_outermost_level(self):
        inner = shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", "-Command", self.read])
        self.assert_unknown(self.collect("pwsh -Command " + quote_ps(inner)))

    def test_native_display_rejects_nul_suffix(self):
        command = shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", "-Command", self.read])
        self.assert_unknown(self.collect(command + "\x00 ; Write-Output 'trailing text'"))

    def test_native_display_preserves_multiline_and_backslashes(self):
        for executable in [r"C:\Program Files\PowerShell\7\pwsh.exe", r"C:\tools\pwsh.exe", "C:/tools/powershell.exe"]:
            with self.subTest(executable=executable):
                command = shlex.join([executable, "-Command", self.read + "\n"])
                self.assert_confirmed(self.collect(command))

    def test_native_display_preserves_quote_heavy_python_script(self):
        code = 'from pathlib import Path; p = Path("README.md"); print(p.read_bytes())'
        script = "python -c " + quote_ps(code)
        command = shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", "-Command", script])
        result = self.collect(command)
        self.assertEqual(result["confirmed_reads"], [])
        self.assertEqual(result["unknown_reads_count"], 0)

    def test_native_display_malformed_is_unknown(self):
        command = shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", "-Command", self.read])
        self.assert_unknown(self.collect(command + ' "unterminated'))

    def test_native_display_redaction_marker_is_unknown(self):
        for script in [self.read + " # [REDACTED_SECRET]", "Get-Content -LiteralPath '[REDACTED_SECRET]'", "Write-Output 'Bearer [REDACTED_SECRET]'"]:
            with self.subTest(script=script):
                command = shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", "-Command", script])
                self.assert_unknown(self.collect(command))

    def test_failed_read(self):
        result = self.collect(output="Get-Content: file not found", exit_code=1)
        self.assert_unknown(result)

    def test_failed_non_skill_read_is_not_unknown(self):
        result = self.collect("Get-Content README.md", output="File not found", exit_code=1)
        self.assertEqual(result["confirmed_reads"], [])
        self.assertEqual(result["unknown_reads_count"], 0)

    def test_standard_module_read_and_impostor_module(self):
        self.assert_confirmed(self.collect("Microsoft.PowerShell.Management\\" + self.read))
        self.assert_unknown(self.collect("OtherModule\\" + self.read))

    def test_echo_path_and_fake_command_are_not_reads(self):
        for command in ["echo " + quote_ps(str(self.skill)), "Write-Output " + quote_ps(self.read), "echo 'cat SKILL.md'", "Write-Host " + quote_ps(self.read)]:
            with self.subTest(command=command):
                result = self.collect(command)
                self.assertEqual(result["confirmed_reads"], [])
                self.assertEqual(result["unknown_reads_count"], 0)

    def test_comments_are_not_reads(self):
        result = self.collect("# " + self.read + "\nWrite-Output 'done'\n<# cat SKILL.md #>")
        self.assertEqual(result["confirmed_reads"], [])
        self.assertEqual(result["unknown_reads_count"], 0)

    def test_rg_and_listing_are_not_reads(self):
        for command in ["rg --files " + quote_ps(str(self.root)), "Get-ChildItem -LiteralPath " + quote_ps(str(self.skill.parent)), "ls " + quote_ps(str(self.skill.parent))]:
            with self.subTest(command=command):
                result = self.collect(command)
                self.assertEqual(result["confirmed_reads"], [])
                self.assertEqual(result["unknown_reads_count"], 0)

    def test_partial_content_search_on_skill_is_unknown(self):
        for command in ["rg 'Read the project' " + quote_ps(str(self.skill)), "Select-String -Pattern 'Read' -LiteralPath " + quote_ps(str(self.skill))]:
            with self.subTest(command=command):
                self.assert_unknown(self.collect(command))

    def test_dynamic_path_is_unknown(self):
        for command in ["Get-Content $path", 'Get-Content "$root/SKILL.md"', "Get-Content (Join-Path $root 'SKILL.md')", "& $reader " + quote_ps(str(self.skill))]:
            with self.subTest(command=command):
                self.assert_unknown(self.collect(command))

    def test_success_without_meaningful_body_is_unknown(self):
        for output in ["", str(self.skill), "# Example skill", "name: example\ndescription: This metadata description alone must not prove a content read.", "Read the project requirements carefully"]:
            with self.subTest(output=output):
                self.assert_unknown(self.collect(output=output))

    def test_unknown_skill_read_is_unknown(self):
        self.assert_unknown(self.collect("Get-Content -LiteralPath " + quote_ps(str(self.unknown))))

    def test_ordinary_literal_file_read_is_not_a_skill_read(self):
        for path in ["README.md", str(self.root / "AGENTS.md"), "C:\\project\\clamp.py"]:
            with self.subTest(path=path):
                result = self.collect("Get-Content -LiteralPath " + quote_ps(path))
                self.assertEqual(result["confirmed_reads"], [])
                self.assertEqual(result["unknown_reads_count"], 0)

    def test_relative_skill_path_is_unknown(self):
        self.assert_unknown(self.collect("Get-Content -LiteralPath 'skills/example/SKILL.md'"))

    def test_unsupported_read_syntax_is_unknown(self):
        for command in [self.read + " -Delimiter x", "Get-Content " + quote_ps(str(self.skill.parent / '*.md')), "cmd /c type " + quote_ps(str(self.skill)), "pwsh -File 'read-skill.ps1'", "pwsh -EncodedCommand Zm9v", "Get-Content -LiteralPath " + quote_ps(str(self.skill)) + ",'other.md'"]:
            with self.subTest(command=command):
                self.assert_unknown(self.collect(command))

    def test_dotnet_reader_is_unsupported_and_unknown(self):
        self.assert_unknown(self.collect("[System.IO.File]::ReadAllText(" + quote_ps(str(self.skill)) + ")"))

    def test_arbitrary_output_cannot_lend_body_evidence(self):
        for command in [self.read + " -TotalCount 1; Write-Output " + quote_ps(BODY), self.read + " | Out-Null; Write-Output " + quote_ps(BODY), self.read + "; Write-Host 'done'", "Write-Output " + quote_ps(BODY) + "; pwsh -Command " + quote_ps(self.read), self.read + "; Out-String"]:
            with self.subTest(command=command):
                self.assert_unknown(self.collect(command))

    def test_truncated_read_cannot_borrow_shared_body(self):
        second = self.root / "second" / "SKILL.md"
        second.parent.mkdir()
        second.write_text(BODY, encoding="utf-8")
        collector = SkillReadEvidenceCollector({"known-skill": self.skill, "second-skill": second})
        result = collector.collect(self.read + " -TotalCount 1; Get-Content -LiteralPath " + quote_ps(str(second)), BODY, 0)
        self.assertEqual(result["confirmed_reads"], ["second-skill"])
        self.assertEqual(result["unknown_reads_count"], 1)
        self.assertEqual(result["classification"], "INCONCLUSIVE")

    def test_out_string_transparent_formatter(self):
        self.assert_confirmed(self.collect(self.read + " | Out-String -Width 200"))

    def test_shared_body_batch_is_unknown(self):
        second = self.root / "second" / "SKILL.md"
        second.parent.mkdir()
        second.write_text(BODY, encoding="utf-8")
        collector = SkillReadEvidenceCollector({"known-skill": self.skill, "second-skill": second})
        result = collector.collect(self.read + "; Get-Content -LiteralPath " + quote_ps(str(second)), BODY, 0)
        self.assert_unknown(result)

    def test_unique_body_batch_is_confirmed(self):
        second = self.root / "second" / "SKILL.md"
        second.parent.mkdir()
        second_body = "# Other\n\n" + "Compare multiple independent sources before accepting an explanation, then record the precise assumptions and observable conditions required to reproduce the result."
        second.write_text(second_body, encoding="utf-8")
        collector = SkillReadEvidenceCollector({"known-skill": self.skill, "second-skill": second})
        result = collector.collect(self.read + "; Get-Content -LiteralPath " + quote_ps(str(second)), BODY + second_body, 0)
        self.assertEqual(result["confirmed_reads"], ["known-skill", "second-skill"])
        self.assertEqual(result["unknown_reads_count"], 0)

    def test_python_skill_and_dynamic_read_are_unknown(self):
        for code in ["from pathlib import Path; print(Path(" + repr(str(self.skill)) + ").read_text())", "from pathlib import Path; print(Path(path).read_text())", "print(open('SKILL.md').read())"]:
            with self.subTest(code=code):
                self.assert_unknown(self.collect("python -c " + quote_ps(code)))

    def test_python_literal_ordinary_read_is_not_a_skill_read(self):
        result = self.collect("python -c " + quote_ps("from pathlib import Path; print(Path('README.md').read_text())"))
        self.assertEqual(result["confirmed_reads"], [])
        self.assertEqual(result["unknown_reads_count"], 0)

    def test_python_unique_top_level_literal_bindings_are_not_skill_reads(self):
        for code in [
            "from pathlib import Path; p = Path('README.md'); print(p.read_bytes())",
            "from pathlib import Path; p = Path('note.html'); content = p.read_text(); print(content)",
            "p = 'README.md'; print(open(p).read())",
            "from pathlib import Path; p: Path = Path('README.md'); print(p.read_text())",
            "from pathlib import Path; p = Path('README.md'); data = p.read_bytes(); p.write_bytes(data)",
        ]:
            with self.subTest(code=code):
                result = self.collect("python -c " + quote_ps(code))
                self.assertEqual(result["confirmed_reads"], [])
                self.assertEqual(result["unknown_reads_count"], 0)

    def test_python_skill_or_dynamic_binding_remains_unknown(self):
        for code in [
            "from pathlib import Path; p = Path('SKILL.md'); print(p.read_bytes())",
            "p = 'SKILL.md'; print(open(p).read())",
            "from pathlib import Path; p = Path(user_input); print(p.read_bytes())",
            "print(p.read_bytes())",
            "from pathlib import Path; print(p.read_bytes()); p = Path('README.md')",
            "from pathlib import Path; p = Path('README.md'); q = p; print(q.read_bytes())",
        ]:
            with self.subTest(code=code):
                self.assert_unknown(self.collect("python -c " + quote_ps(code)))

    def test_python_reassignment_and_binding_writes_are_unknown(self):
        for code in [
            "from pathlib import Path; p = Path('README.md'); p = Path('SKILL.md'); print(p.read_bytes())",
            "from pathlib import Path; p = Path('README.md'); p = Path('note.html'); print(p.read_bytes())",
            "p = 'README.md'; p += '.bak'; print(open(p).read())",
            "from pathlib import Path; p, q = Path('README.md'), 1; print(p.read_bytes())",
            "from pathlib import Path; p = Path('README.md'); del p; print(p.read_bytes())",
            "from pathlib import Path; print((p := Path('README.md')).read_text()); print(p.read_bytes())",
        ]:
            with self.subTest(code=code):
                self.assert_unknown(self.collect("python -c " + quote_ps(code)))

    def test_python_control_flow_and_nested_scope_bindings_are_unknown(self):
        for code in [
            "from pathlib import Path\nif condition:\n p = Path('README.md')\nprint(p.read_bytes())",
            "from pathlib import Path\np = Path('README.md')\ndef f(p):\n return p.read_text()\nf(Path('SKILL.md'))",
            "from pathlib import Path\ndef f():\n p = Path('README.md')\n return p.read_text()\nf()",
            "from pathlib import Path\np = Path('README.md')\n[p.read_text() for p in [Path('SKILL.md')]]",
            "from pathlib import Path\np = Path('README.md')\nfor p in [Path('SKILL.md')]:\n print(p.read_text())",
            "from pathlib import Path\np = Path('README.md')\ntry:\n print('x')\nexcept Exception as p:\n print(p.read_text())",
        ]:
            with self.subTest(code=code):
                self.assert_unknown(self.collect("python -c " + quote_ps(code)))

    def test_python_mutated_path_constructor_or_dynamic_namespace_is_unknown(self):
        for code in [
            "from pathlib import Path; Path = OtherPath; p = Path('README.md'); print(p.read_bytes())",
            "from other_module import Path; p = Path('README.md'); print(p.read_bytes())",
            "from pathlib import Path; Path.read_bytes = reader; p = Path('README.md'); print(p.read_bytes())",
            "from pathlib import Path; Alias = Path; Alias.read_bytes = reader; p = Path('README.md'); print(p.read_bytes())",
            "import pathlib; from pathlib import Path; pathlib.Path.read_bytes = reader; p = Path('README.md'); print(p.read_bytes())",
            "from pathlib import Path; p = Path('README.md'); globals()['p'] = Path('SKILL.md'); print(p.read_bytes())",
            "p = 'README.md'; vars().update(p='SKILL.md'); print(open(p).read())",
            "v = vars; p = 'README.md'; v().update(p='SKILL.md'); print(open(p).read())",
        ]:
            with self.subTest(code=code):
                self.assert_unknown(self.collect("python -c " + quote_ps(code)))

    def test_python_bound_paths_cannot_escape_or_be_reinitialized(self):
        for code in [
            "from pathlib import Path; p = Path('README.md'); p.__init__('SKILL.md'); print(p.read_bytes())",
            "from pathlib import Path; from helper import mutate; p = Path('README.md'); mutate(p); print(p.read_bytes())",
            "from pathlib import Path; p = Path('README.md'); q = p; q.__init__('SKILL.md'); print(p.read_bytes())",
            "from pathlib import Path; p = Path('README.md'); p._parts.append('SKILL.md'); print(p.read_bytes())",
            "from pathlib import Path; p = Path('README.md'); f = p.read_bytes; print(f())",
            "from pathlib import Path; p = Path('README.md'); print(p.exists()); print(p.read_bytes())",
        ]:
            with self.subTest(code=code):
                self.assert_unknown(self.collect("python -c " + quote_ps(code)))

    def test_powershell_literal_ordinary_read_in_assignment_is_not_unknown(self):
        for command in ["$content = Get-Content -LiteralPath 'README.md'; $content", "$content = (Get-Content 'note.html'); Write-Output $content"]:
            with self.subTest(command=command):
                result = self.collect(command)
                self.assertEqual(result["confirmed_reads"], [])
                self.assertEqual(result["unknown_reads_count"], 0)

    def test_powershell_assignment_skill_or_dynamic_read_remains_unknown(self):
        for command in ["$content = Get-Content -LiteralPath 'SKILL.md'; $content", "$content = Get-Content $path; $content"]:
            with self.subTest(command=command):
                self.assert_unknown(self.collect(command))

    def test_parser_never_executes_event_text(self):
        marker = self.root / "must-not-exist.txt"
        command = "[System.IO.File]::WriteAllText(" + quote_ps(str(marker)) + ", 'unexpected'); " + self.read
        self.assert_unknown(self.collect(command))
        self.assertFalse(marker.exists())

    def test_parser_unavailable_is_inconclusive(self):
        self.collector._parser = None
        self.assert_unknown(self.collect())

    def test_parser_process_failure_is_inconclusive(self):
        with mock.patch("skill_read_evidence.subprocess.run", side_effect=OSError("unavailable")):
            self.assert_unknown(self.collect())

    def test_oversized_event_is_inconclusive(self):
        self.assert_unknown(self.collect(command="x" * 131073))

    def test_only_safe_known_labels_are_accepted(self):
        with self.assertRaises(ValueError) as caught:
            SkillReadEvidenceCollector({"unsafe/path": self.skill})
        self.assertNotIn(str(self.root), str(caught.exception))

    def test_literal_parameter_colon_syntax(self):
        self.assert_confirmed(self.collect("Get-Content -LiteralPath:" + quote_ps(str(self.skill)) + " -TotalCount:20"))

    def test_unexecuted_or_conditional_read_is_never_confirmed(self):
        for command in ["if ($false) { " + self.read + " }; Write-Output 'done'", "function F { " + self.read + " }; Write-Output 'done'", "$x = { " + self.read + " }; Write-Output 'done'", "Write-Output { " + self.read + " }"]:
            with self.subTest(command=command):
                self.assert_unknown(self.collect(command))

    def test_parse_error_is_unknown(self):
        self.assert_unknown(self.collect("Get-Content 'unterminated"))

    def test_redirection_is_unknown(self):
        self.assert_unknown(self.collect(self.read + " > $null"))

    def test_alias_redefinition_is_unknown(self):
        self.assert_unknown(self.collect("Set-Alias cat Write-Output; cat " + quote_ps(str(self.skill))))

    def test_known_and_unknown_reads_make_event_inconclusive(self):
        result = self.collect(self.read + "; Get-Content $path")
        self.assertEqual(result["confirmed_reads"], [])
        self.assertGreater(result["unknown_reads_count"], 0)
        self.assertEqual(result["classification"], "INCONCLUSIVE")

    def test_duplicate_known_reads_deduplicated(self):
        self.assert_confirmed(self.collect(self.read + "; " + self.read))

    def test_body_excerpt_with_whitespace_variations(self):
        excerpt = "Read the project requirements carefully before selecting the smallest useful implementation,\n and preserve unrelated changes throughout the work."
        self.assert_confirmed(self.collect(output=excerpt))

    def test_collect_completed_event_and_aggregate(self):
        event = {"command": self.read, "aggregated_output": BODY, "exit_code": 0}
        self.assert_confirmed(self.collector.collect_event(event))
        result = self.collector.summarize([event, {"command": "Get-Content $path", "aggregated_output": BODY, "exit_code": 0}])
        self.assertEqual(result["confirmed_reads"], ["known-skill"])
        self.assertEqual(result["unknown_reads_count"], 1)
        self.assertEqual(result["classification"], "INCONCLUSIVE")

    def test_invalid_event_is_unknown(self):
        for event in [{}, {"command": self.read, "aggregated_output": BODY, "exit_code": "0"}, {"command": self.read, "aggregated_output": [], "exit_code": 0}]:
            with self.subTest(event=event):
                self.assert_unknown(self.collector.collect_event(event))


if __name__ == "__main__":
    unittest.main()
