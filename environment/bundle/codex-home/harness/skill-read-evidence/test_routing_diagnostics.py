"""Controlled counterexamples for the isolated-read observation protocol."""
from pathlib import Path
import json
import shlex
import tempfile
import unittest

from routing_diagnostics import RoutingDiagnosticCollector
from test_skill_read_evidence import BODY, quote_ps


class RoutingDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="routing-protocol-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.skill = self.root / "SKILL.md"
        self.skill.write_text(BODY, encoding="utf-8")
        self.collector = RoutingDiagnosticCollector({"known-skill": self.skill})
        self.read = "Get-Content -LiteralPath " + quote_ps(str(self.skill))

    def diagnostic(self, command, output=BODY, exit_code=0):
        result = self.collector.collect_diagnostic(command, output, exit_code)
        # No input string, body, command argument or path leaks into the result.
        serialized = json.dumps(result)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("Read the project requirements", serialized)
        self.assertNotIn("Get-Content", serialized)
        self.assertFalse(hasattr(self.collector, "_diagnostic_units"))
        self.assertEqual(len(result["command_sha256"]), 64)
        return result

    def test_isolated_literal_read_remains_confirmed(self):
        result = self.diagnostic(self.read)
        self.assertEqual(result["labels"]["classification"], "CONFIRMED")
        self.assertEqual(result["parser_units"][0]["direct_skill_candidates"], 1)
        self.assertFalse(result["parser_units"][0]["blocked_by_context_gate"])

    def test_mixed_arbitrary_output_remains_unknown(self):
        result = self.diagnostic(self.read + "; Write-Output 'controlled fixture output'")
        self.assertEqual(result["labels"]["classification"], "INCONCLUSIVE")
        self.assertTrue(result["parser_units"][0]["mixed_output"])
        self.assertTrue(result["parser_units"][0]["blocked_by_context_gate"])

    def test_mixed_ordinary_file_remains_unknown(self):
        result = self.diagnostic(self.read + "; Get-Content -LiteralPath 'README.md'")
        self.assertEqual(result["labels"]["classification"], "INCONCLUSIVE")
        self.assertTrue(result["parser_units"][0]["unresolved_source"])
        self.assertEqual(result["parser_units"][0]["ordinary_literal_reads"], 1)

    def test_two_skills_plus_ordinary_source_reproduce_two_unknown_candidates(self):
        second = self.root / "other" / "SKILL.md"
        second.parent.mkdir()
        second.write_text(BODY.replace("project requirements", "exercise specifications"), encoding="utf-8")
        self.collector = RoutingDiagnosticCollector({"known-skill": self.skill, "second-skill": second})
        command = self.read + "; Get-Content -LiteralPath " + quote_ps(str(second)) + "; Get-Content 'README.md'"
        result = self.diagnostic(command)
        self.assertEqual(result["labels"]["unknown_reads_count"], 2)
        self.assertEqual(result["labels"]["confirmed_reads"], [])
        self.assertEqual(result["parser_units"][0]["direct_skill_candidates"], 2)
        self.assertTrue(result["parser_units"][0]["unresolved_source"])

    def test_separate_events_remove_aggregate_ambiguity(self):
        ordinary = self.diagnostic("Get-Content -LiteralPath 'README.md'", "ordinary file body")
        skill = self.diagnostic(self.read)
        self.assertEqual(ordinary["labels"]["classification"], "NO_CONFIRMED_READS")
        self.assertEqual(skill["labels"]["classification"], "CONFIRMED")

    def test_fabricated_excerpt_cannot_rescue_mixed_suppressed_read(self):
        result = self.diagnostic(self.read + " | Out-Null; Write-Output " + quote_ps(BODY))
        self.assertEqual(result["labels"]["classification"], "INCONCLUSIVE")
        self.assertEqual(result["labels"]["confirmed_reads"], [])

    def test_protocol_does_not_rescue_missing_excerpt(self):
        result = self.diagnostic(self.read, "# Heading only")
        self.assertEqual(result["labels"]["classification"], "INCONCLUSIVE")
        self.assertFalse(result["parser_units"][0]["blocked_by_context_gate"])

    def test_protocol_does_not_rescue_failed_read(self):
        result = self.diagnostic(self.read, BODY, 1)
        self.assertEqual(result["labels"]["classification"], "INCONCLUSIVE")
        self.assertFalse(result["exit_zero"])

    def test_protocol_does_not_rescue_unknown_dynamic_path(self):
        result = self.diagnostic("Get-Content -LiteralPath $path")
        self.assertEqual(result["labels"]["classification"], "INCONCLUSIVE")
        self.assertTrue(result["parser_units"][0]["unresolved_source"])

    def test_native_shlex_boundary_retains_only_structural_projection(self):
        command = shlex.join([r"C:\Program Files\PowerShell\7\pwsh.exe", "-NoProfile", "-Command", self.read])
        result = self.diagnostic(command)
        self.assertEqual(result["labels"]["classification"], "CONFIRMED")
        self.assertEqual(len(result["parser_units"]), 1)

    def test_nested_wrapper_and_python_are_structural_only(self):
        command = "pwsh -Command " + quote_ps("python -c " + quote_ps("open(target).read()"))
        result = self.diagnostic(command)
        self.assertEqual(result["labels"]["classification"], "INCONCLUSIVE")
        self.assertEqual(len(result["parser_units"]), 2)
        self.assertEqual(result["parser_units"][1]["python_skill_or_dynamic_candidates"], 1)

    def test_redacted_input_retains_unknown_without_parser_data(self):
        result = self.diagnostic("Get-Content '[REDACTED_SECRET]'")
        self.assertEqual(result["labels"]["classification"], "INCONCLUSIVE")
        self.assertEqual(result["parser_units"], [])


if __name__ == "__main__":
    unittest.main()
