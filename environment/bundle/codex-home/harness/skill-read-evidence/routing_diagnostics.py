"""Metadata-only diagnostics layered over the unchanged conservative collector.

The parser sees command text as data. This adapter retains parse trees only for
the duration of one call, and exports counts, controlled feature names and
SHA-256 digests. It deliberately does not change classification or thresholds.
"""
from __future__ import annotations

import hashlib

from skill_read_evidence import (
    SkillReadEvidenceCollector, _MUTATING_NAMES, _READ_NAMES, _SHELL_NAMES,
    _canonical_path, _command_name,
)


class RoutingDiagnosticCollector(SkillReadEvidenceCollector):
    def _parse(self, command):
        parsed = super()._parse(command)
        if hasattr(self, "_diagnostic_units"):
            self._diagnostic_units.append(parsed)
        return parsed

    def collect_diagnostic(self, command, output, exit_code):
        """Return normal labels plus a fixed, text-free structural projection."""
        self._diagnostic_units = []
        try:
            labels = self.collect(command, output, exit_code)
            units = [self._features(unit) for unit in self._diagnostic_units]
        finally:
            # Parsed nodes contain arguments, so never retain them between calls.
            del self._diagnostic_units
        return {
            "labels": labels,
            "command_sha256": self._digest(command),
            "output_sha256": self._digest(output),
            "exit_zero": type(exit_code) is int and exit_code == 0,
            "parser_units": units,
        }

    @staticmethod
    def _digest(value):
        return hashlib.sha256(value.encode("utf-8")).hexdigest() if isinstance(value, str) else None

    def _features(self, parsed):
        if parsed is None:
            return {"parser_failure": True}
        if parsed.get("parse_error"):
            return {"parse_error": True}
        commands = parsed["commands"]
        reads = [item for item in commands if _command_name(item.get("name")) in _READ_NAMES]
        candidates = [item for item in reads if self._is_skill_candidate(self._read_spec(item.get("elements", [])))]
        hidden = parsed.get("hidden_read_commands")
        hidden_count = (sum(self._is_skill_candidate(self._read_spec(item.get("elements", []))) for item in hidden)
                        if isinstance(hidden, list) else int(parsed.get("hidden_read_count", 0)))
        python_count = sum(self._python_read_signals(item) for item in commands)
        partial_count = sum(self._partial_search_signals(item) for item in commands)
        unsupported = int(parsed.get("unsupported_read_count", 0))
        unknown = hidden_count + python_count + partial_count + unsupported
        wrappers = [item for item in commands if _command_name(item.get("name")) in _SHELL_NAMES]
        uncertain = bool(parsed.get("complex_statement_count")) or any(
            _command_name(item.get("name")) in _MUTATING_NAMES or item.get("dot_sourced") for item in commands)
        mixed_output = bool(candidates) and any(
            _command_name(item.get("name")) not in _READ_NAMES and not self._transparent_formatter(item)
            for item in commands)
        mixed_wrapper = bool(wrappers) and len(commands) != 1
        unresolved = bool(candidates) and (unknown > 0 or any(
            (spec := self._read_spec(item.get("elements", []))) is None
            or _canonical_path(spec[0]) not in self._known for item in reads))
        return {
            "command_count": len(commands),
            "direct_skill_candidates": len(candidates),
            "ordinary_literal_reads": len(reads) - len(candidates),
            "hidden_skill_candidates": hidden_count,
            "python_skill_or_dynamic_candidates": python_count,
            "partial_skill_search_candidates": partial_count,
            "unsupported_member_reads": unsupported,
            "uncertain_context": uncertain,
            "mixed_output": mixed_output,
            "mixed_wrapper": mixed_wrapper,
            "unresolved_source": unresolved,
            "blocked_by_context_gate": bool(
                (uncertain or mixed_output or mixed_wrapper or unresolved) and (candidates or wrappers or unknown)),
            "redirected_reads": sum(bool(item.get("redirected")) for item in reads),
            "wrapper_count": len(wrappers),
            "unsupported_wrappers": sum(self._wrapper_text(item.get("elements", [])) is None for item in wrappers),
            "dynamic_or_cmd_invocations": sum(_command_name(item.get("name")) in {"", "cmd", "cmd.exe"} for item in commands),
        }
