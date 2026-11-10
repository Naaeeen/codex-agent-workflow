"""Conservative evidence labels for completed Windows command execution events.

This diagnostic is intentionally not a PowerShell evaluator. It parses input
using the installed PowerShell AST parser and confirms only its documented
literal subset, additionally requiring a meaningful excerpt of a known file.
Public methods never return commands, output, or filesystem paths.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from collections import Counter
import ast
import json
import ntpath
from pathlib import Path
import re
import shutil
import shlex
import subprocess
from typing import TypedDict


class EvidenceLabels(TypedDict):
    confirmed_reads: list[str]
    unknown_reads_count: int
    classification: str


_READ_NAMES = {"get-content", "cat", "type", "gc", "microsoft.powershell.management\\get-content"}
_SHELL_NAMES = {"pwsh", "pwsh.exe", "powershell", "powershell.exe"}
_MUTATING_NAMES = {
    "set-alias", "sal", "new-alias", "nal", "set-item", "si", "new-item", "ni",
    "remove-item", "ri", "rm", "del", "erase", "clear-item", "cli",
    "set-variable", "sv", "new-variable", "nv", "remove-variable", "rv",
    "import-module", "ipmo", "remove-module", "rmo", "invoke-expression", "iex",
    "invoke-command", "icm",
}
_ENCODINGS = {
    "ascii", "bigendianunicode", "bigendianutf32", "oem", "unicode", "utf7",
    "utf8", "utf8bom", "utf8nobom", "utf32", "default", "string",
}
_PARSER_FILE = Path(__file__).with_name("parse_skill_commands.ps1")
_MAX_COMMAND_CHARS = 131_072
_MAX_OUTPUT_CHARS = 2_097_152
_MAX_WRAPPER_DEPTH = 4


def _labels(names: Iterable[str] = (), unknown: int = 0) -> EvidenceLabels:
    confirmed = sorted(set(names))
    return {
        "confirmed_reads": confirmed,
        "unknown_reads_count": unknown,
        "classification": "INCONCLUSIVE" if unknown else "CONFIRMED" if confirmed else "NO_CONFIRMED_READS",
    }


def _normalize_text(value: str) -> str:
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    return " ".join(value.split())


def _body_anchors(content: str) -> tuple[str, ...]:
    """Use prose excerpts, excluding metadata, headings, and fenced code.

    Every anchor has at least 12 words and 80 characters, so displaying only a
    skill name, pathname, heading, or frontmatter cannot satisfy the check.
    """
    lines = content.lstrip("\ufeff").splitlines()
    if lines and lines[0].strip() == "---":
        closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if closing is not None:
            lines = lines[closing + 1:]
        else:
            return ()
    paragraphs: list[str] = []
    current: list[str] = []
    fence: str | None = None
    for line in lines + [""]:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            fence = None if fence == marker else marker if fence is None else fence
            stripped = ""
        if fence is not None or stripped.startswith("#") or stripped in {"---", "***", "___"}:
            stripped = ""
        if stripped:
            current.append(stripped)
        elif current:
            paragraphs.append(_normalize_text(" ".join(current)))
            current = []
    anchors: list[str] = []
    for paragraph in paragraphs:
        words = list(re.finditer(r"\S+", paragraph))
        for start in range(max(0, len(words) - 11)):
            end = start + 11
            while end < len(words) and words[end].end() - words[start].start() < 80:
                end += 1
            if end >= len(words):
                continue
            anchor = paragraph[words[start].start():words[end].end()]
            # Pure paths, tables of names, or punctuation are not substantive prose.
            if len(re.findall(r"\b[^\W\d_]{2,}\b", anchor, flags=re.UNICODE)) >= 12:
                anchors.append(anchor)
            if len(anchors) >= 4096:
                return tuple(anchors)
    return tuple(anchors)


def _canonical_path(value: str) -> str | None:
    # Event input has no cwd, so relative paths and provider/wildcard syntax are
    # deliberately unresolved. PureWindowsPath behavior is needed even in tests.
    if not ntpath.isabs(value) or not ntpath.splitdrive(value)[0]:
        return None
    if any(character in value for character in "*?[]") or "::" in value:
        return None
    return ntpath.normcase(ntpath.normpath(value))


def _command_name(value: object) -> str:
    if not isinstance(value, str):
        return ""
    lowered = value.lower()
    basename = ntpath.basename(lowered)
    # Native shell paths may be absolute, but an arbitrary module-qualified
    # Get-Content must never be mistaken for the standard cmdlet.
    return basename if basename in _SHELL_NAMES | {"cmd", "cmd.exe"} else lowered


def _literal(element: object) -> str | None:
    if isinstance(element, dict) and element.get("kind") == "literal" and isinstance(element.get("value"), str):
        return element["value"]
    return None


def _flatten_elements(elements: list[dict]) -> list[dict]:
    flattened = []
    for element in elements:
        flattened.append(element)
        if element.get("kind") == "parameter" and element.get("argument") is not None:
            flattened.append(element["argument"])
    return flattened


def _native_arguments(elements: list[dict]) -> list[str | None]:
    return ["-" + str(token.get("name", "")) if token.get("kind") == "parameter" else _literal(token)
            for token in _flatten_elements(elements[1:])]


def _native_display_script(command: str) -> tuple[bool, str | None]:
    """Decode the pinned Codex shlex_join display contract, as data only.

    Codex serializes the original argv with Rust shlex::try_join; this field is
    not a Windows CreateProcess command line. Only a validated absolute native
    PowerShell argv envelope may supply a script to the existing AST parser.
    """
    try:
        arguments = shlex.split(command, comments=False, posix=True)
    except ValueError:
        return True, None
    if not arguments or _canonical_path(arguments[0]) is None or ntpath.basename(arguments[0]).lower() not in _SHELL_NAMES:
        return False, None
    index = 1
    while index < len(arguments):
        switch = arguments[index].lower()
        if switch in {"-nologo", "-noprofile", "-noninteractive"}:
            index += 1
            continue
        if switch == "-command" and index == len(arguments) - 2:
            return True, arguments[index + 1]
        return True, None
    return True, None


class SkillReadEvidenceCollector:
    """Collect known-only evidence; construct once before consuming events.

    ``known_skills`` must be trusted configuration, with safe display labels and
    absolute local files. No command or event can add paths to that allowlist.
    File bodies are snapshotted at construction; rebuild if skill files change.
    """

    def __init__(self, known_skills: Mapping[str, str | Path], *, parser_executable: str | None = None):
        self._known: dict[str, list[tuple[str, tuple[str, ...], list[str]]]] = {}
        for name, path in known_skills.items():
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", name):
                raise ValueError("Known-skill labels must be short safe identifiers")
            canonical = _canonical_path(str(path))
            if canonical is None:
                raise ValueError("Known-skill configuration requires absolute literal local paths")
            try:
                content = Path(path).read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError):
                raise ValueError("A configured skill could not be read as UTF-8") from None
            self._known.setdefault(canonical, []).append((name, _body_anchors(content), content.splitlines()))
        self._parser = parser_executable or shutil.which("pwsh") or shutil.which("powershell")

    def _parse(self, command: str) -> dict | None:
        if not self._parser:
            return None
        options: dict = {}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            options["startupinfo"] = startupinfo
        try:
            # The sole executed script is our fixed parser. Event data is stdin,
            # never a command argument, scriptblock invocation, or expression.
            result = subprocess.run(
                [self._parser, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(_PARSER_FILE)],
                input=json.dumps({"command": command}), capture_output=True,
                text=True, encoding="utf-8", timeout=15, check=False, **options,
            )
            if result.returncode != 0:
                return None
            parsed = json.loads(result.stdout.lstrip("\ufeff"))
            if not isinstance(parsed, dict) or not isinstance(parsed.get("commands"), list):
                return None
            return parsed
        except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
            return None

    @staticmethod
    def _read_spec(elements: list[dict]) -> tuple[str, int | None, int | None] | None:
        tokens = _flatten_elements(elements[1:])
        path = None
        total_count = None
        tail_count = None
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token.get("kind") == "parameter":
                name = str(token.get("name", "")).lower()
                if name == "raw":
                    index += 1
                    continue
                if name not in {"literalpath", "path", "encoding", "totalcount", "head", "first", "tail", "erroraction", "ea"}:
                    return None
                index += 1
                if index >= len(tokens):
                    return None
                value = _literal(tokens[index])
                if value is None:
                    return None
                if name in {"literalpath", "path"}:
                    if path is not None:
                        return None
                    path = value
                elif name == "encoding" and value.lower() not in _ENCODINGS:
                    return None
                elif name in {"totalcount", "head", "first", "tail"} and (not value.isdecimal() or int(value) < 1):
                    return None
                elif name in {"totalcount", "head", "first"}:
                    if total_count is not None or tail_count is not None:
                        return None
                    total_count = int(value)
                elif name == "tail":
                    if total_count is not None or tail_count is not None:
                        return None
                    tail_count = int(value)
                elif name in {"erroraction", "ea"} and value.lower() not in {"stop", "continue", "silentlycontinue", "ignore"}:
                    return None
            else:
                value = _literal(token)
                if value is None or path is not None:
                    return None
                path = value
            index += 1
        return (path, total_count, tail_count) if path else None

    def _is_skill_candidate(self, spec: tuple[str, int | None, int | None] | None) -> bool:
        if spec is None:
            return True
        path = spec[0]
        return _canonical_path(path) in self._known or ntpath.basename(path).lower() == "skill.md" or any(
            character in path for character in "*?[]"
        )

    @staticmethod
    def _transparent_formatter(item: dict) -> bool:
        if _command_name(item.get("name")) != "out-string" or item.get("redirected"):
            return False
        if item.get("pipeline_length", 0) < 2 or item.get("pipeline_index") != item.get("pipeline_length") - 1:
            return False
        tokens = _flatten_elements(item.get("elements", [])[1:])
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token.get("kind") != "parameter":
                return False
            name = str(token.get("name", "")).lower()
            if name == "stream":
                index += 1
                continue
            if name != "width" or index + 1 >= len(tokens):
                return False
            value = _literal(tokens[index + 1])
            if value is None or not value.isdecimal() or int(value) < 1:
                return False
            index += 2
        return True

    @staticmethod
    def _python_read_signals(item: dict) -> int:
        """Safely inspect Python -c calls for skill/dynamic read attempts only."""
        basename = ntpath.basename(_command_name(item.get("name")))
        if not re.fullmatch(r"(?:python(?:\d+(?:\.\d+)*)?|py)(?:\.exe)?", basename):
            return 0
        arguments = _native_arguments(item.get("elements", []))
        if "-c" not in arguments:
            return 0
        index = arguments.index("-c")
        if index + 1 >= len(arguments) or arguments[index + 1] is None:
            return 1
        try:
            tree = ast.parse(arguments[index + 1])
        except (SyntaxError, ValueError, RecursionError):
            return 1

        nodes = list(ast.walk(tree))
        writes = Counter(node.id for node in nodes if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)))
        for node in nodes:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    writes[alias.asname or (alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name)] += 1

        boundaries = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.TryStar,
                      ast.With, ast.AsyncWith, ast.FunctionDef, ast.AsyncFunctionDef,
                      ast.ClassDef, ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
                      ast.GeneratorExp, ast.Match)
        dynamic_names = {"exec", "eval", "globals", "locals", "vars", "getattr", "setattr", "delattr"}
        dynamic_namespace = any((isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in dynamic_names)
                                or (isinstance(node, ast.Attribute) and node.attr in dynamic_names)
                                for node in nodes)
        bindings_allowed = not dynamic_namespace and not any(isinstance(node, boundaries) for node in nodes)

        def root_name(node: ast.AST) -> str | None:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, (ast.Attribute, ast.Subscript)):
                return root_name(node.value)
            return None

        mutated_objects = {root_name(node) for node in nodes
                           if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del))}
        # Attribute/subscript writes can mutate an imported constructor through
        # an alias. Do not attempt alias analysis in this bounded recognizer.
        bindings_allowed = bindings_allowed and not mutated_objects
        path_types = {"Path", "PurePath", "PosixPath", "WindowsPath"}
        class_imports: dict[str, int] = {}
        module_imports: dict[str, int] = {}
        for index, statement in enumerate(tree.body):
            if isinstance(statement, ast.ImportFrom) and statement.module == "pathlib" and statement.level == 0:
                for alias in statement.names:
                    if alias.name in path_types:
                        class_imports[alias.asname or alias.name] = index
            elif isinstance(statement, ast.Import):
                for alias in statement.names:
                    if alias.name == "pathlib":
                        module_imports[alias.asname or alias.name] = index

        def safe_constructor(node: ast.AST, index: int) -> bool:
            if dynamic_namespace or mutated_objects:
                return False
            if isinstance(node, ast.Name):
                return (node.id in class_imports and class_imports[node.id] < index
                        and writes[node.id] == 1 and node.id not in mutated_objects)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                name = node.value.id
                return (node.attr in path_types and name in module_imports and module_imports[name] < index
                        and writes[name] == 1 and name not in mutated_objects)
            return False

        bindings: dict[str, tuple[int, str, str]] = {}

        def literal_path(node: ast.AST | None, index: int, allow_bindings: bool = True) -> str | None:
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return node.value
            if isinstance(node, ast.Name) and allow_bindings and bindings_allowed:
                binding = bindings.get(node.id)
                if binding is not None and binding[0] < index:
                    return binding[1]
            if isinstance(node, ast.Call) and safe_constructor(node.func, index) and len(node.args) == 1 and not node.keywords:
                return literal_path(node.args[0], index, allow_bindings=False)
            return None

        if bindings_allowed:
            for index, statement in enumerate(tree.body):
                target = value = None
                if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                    target, value = statement.targets[0], statement.value
                elif isinstance(statement, ast.AnnAssign):
                    target, value = statement.target, statement.value
                if isinstance(target, ast.Name) and writes[target.id] == 1 and target.id not in mutated_objects:
                    path = literal_path(value, index, allow_bindings=False)
                    if path is not None:
                        bindings[target.id] = (index, path, "path" if isinstance(value, ast.Call) else "string")

        # Prove that the object cannot escape or be reinitialized through an
        # alias. These direct Path I/O methods retain the object's path.
        # This deliberately does not interpret arbitrary helper methods.
        parents = {id(child): parent for parent in nodes for child in ast.iter_child_nodes(parent)}
        invalid_bindings: set[str] = set()
        for node in nodes:
            if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load) or node.id not in bindings:
                continue
            parent = parents.get(id(node))
            receiver_call = parents.get(id(parent)) if parent is not None else None
            direct_read = (bindings[node.id][2] == "path" and isinstance(parent, ast.Attribute)
                           and parent.value is node and parent.attr in {"read_text", "read_bytes", "open", "write_text", "write_bytes"}
                           and isinstance(receiver_call, ast.Call) and receiver_call.func is parent)
            open_argument = (isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name)
                             and parent.func.id == "open" and not writes["open"]
                             and parent.args and parent.args[0] is node)
            if not direct_read and not open_argument:
                invalid_bindings.add(node.id)
        for name in invalid_bindings:
            del bindings[name]

        def straight_nodes(node: ast.AST):
            if isinstance(node, boundaries):
                return
            yield node
            for child in ast.iter_child_nodes(node):
                yield from straight_nodes(child)

        call_indices = {id(node): index for index, statement in enumerate(tree.body)
                        if isinstance(statement, (ast.Expr, ast.Assign, ast.AnnAssign))
                        for node in straight_nodes(statement) if isinstance(node, ast.Call)}

        # Extracting a reader method from an invalid binding is itself an
        # unresolved read signal, even if its later invocation uses an alias.
        signals = sum(isinstance(node, ast.Attribute) and node.attr in {"read_text", "read_bytes", "open"}
                      and root_name(node.value) in invalid_bindings
                      and not (isinstance(parents.get(id(node)), ast.Call) and parents[id(node)].func is node)
                      for node in nodes)
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call):
                continue
            path = None
            candidate = False
            index = call_indices.get(id(call))
            if isinstance(call.func, ast.Name) and call.func.id == "open":
                candidate = True
                if index is not None and not writes["open"] and not dynamic_namespace and not mutated_objects:
                    path = literal_path(call.args[0], index) if call.args else None
            elif isinstance(call.func, ast.Attribute) and call.func.attr in {"read_text", "read_bytes", "open"}:
                candidate = True
                if index is not None:
                    path = literal_path(call.func.value, index)
                    if call.func.attr == "open" and path is None and call.args:
                        path = literal_path(call.args[0], index)
            if candidate and (path is None or ntpath.basename(path).lower() == "skill.md" or any(c in path for c in "*?[]")):
                signals += 1
        return signals

    def _partial_search_signals(self, item: dict) -> int:
        name = ntpath.basename(_command_name(item.get("name")))
        if name not in {"rg", "rg.exe", "select-string", "sls"}:
            return 0
        arguments = _native_arguments(item.get("elements", []))
        if name in {"rg", "rg.exe"} and "--files" in arguments:
            return 0
        return int(any(value is None or ntpath.basename(value).lower() == "skill.md"
                       or _canonical_path(value) in self._known for value in arguments))

    @staticmethod
    def _selected_text(lines: list[str], spec: tuple[str, int | None, int | None]) -> str:
        if spec[1] is not None:
            lines = lines[:spec[1]]
        elif spec[2] is not None:
            lines = lines[-spec[2]:]
        return _normalize_text("\n".join(lines))

    @staticmethod
    def _wrapper_text(elements: list[dict]) -> str | None:
        tokens = _flatten_elements(elements[1:])
        for index, token in enumerate(tokens):
            value = _literal(token)
            if token.get("kind") == "parameter":
                value = "-" + str(token.get("name", ""))
            if value is None:
                return None
            switch = value.lower()
            if switch in {"-nologo", "-noprofile", "-noninteractive"}:
                continue
            if switch in {"-command", "-c"}:
                if index != len(tokens) - 2:
                    return None
                return _literal(tokens[index + 1])
            # File/encoded command/implicit command and option abbreviations are
            # intentionally not interpreted by this bounded diagnostic.
            return None
        return None

    def _collect_parsed(self, command: str, output: str, depth: int) -> EvidenceLabels:
        if depth > _MAX_WRAPPER_DEPTH:
            return _labels(unknown=1)
        if depth == 0:
            is_native_envelope, native_script = _native_display_script(command)
            if is_native_envelope:
                return self._collect_parsed(native_script, output, depth + 1) if native_script is not None else _labels(unknown=1)
        parsed = self._parse(command)
        if parsed is None or parsed.get("parse_error"):
            return _labels(unknown=1)
        names: set[str] = set()
        hidden_commands = parsed.get("hidden_read_commands")
        hidden_count = (sum(self._is_skill_candidate(self._read_spec(item.get("elements", []))) for item in hidden_commands)
                        if isinstance(hidden_commands, list) else int(parsed.get("hidden_read_count", 0)))
        unknown = hidden_count + int(parsed.get("unsupported_read_count", 0))
        commands = parsed["commands"]
        read_commands = [item for item in commands if _command_name(item.get("name")) in _READ_NAMES]
        candidates = [item for item in read_commands if self._is_skill_candidate(self._read_spec(item.get("elements", [])))]
        unknown += sum(self._python_read_signals(item) for item in commands)
        unknown += sum(self._partial_search_signals(item) for item in commands)
        wrappers = [item for item in commands if _command_name(item.get("name")) in _SHELL_NAMES]
        # Definitions/assignments and explicit environment mutation can change
        # command meaning. Do not confirm apparent reads in those scripts.
        uncertain_context = bool(parsed.get("complex_statement_count")) or any(
            _command_name(item.get("name")) in _MUTATING_NAMES or item.get("dot_sourced")
            for item in commands
        )
        # Aggregated output cannot attribute body text across arbitrary commands
        # or sinks. A later Write-Output must not lend evidence to a failed,
        # truncated, or suppressed read earlier in the same event.
        mixed_output = bool(candidates) and any(
            _command_name(item.get("name")) not in _READ_NAMES and not self._transparent_formatter(item)
            for item in commands
        )
        # Wrappers use the event's aggregate output too, so any sibling command
        # can contaminate their evidence. Keep the wrapper case deliberately
        # narrower than the direct pure-read batch case.
        mixed_wrapper = bool(wrappers) and len(commands) != 1
        unresolved_source = bool(candidates) and (unknown > 0 or any(
            (spec := self._read_spec(item.get("elements", []))) is None
            or _canonical_path(spec[0]) not in self._known for item in read_commands
        ))
        if (uncertain_context or mixed_output or mixed_wrapper or unresolved_source) and (candidates or wrappers or unknown):
            return _labels(unknown=max(1, unknown + len(candidates)))
        visible_by_path: dict[str, list[str]] = {}
        for item in read_commands:
            spec = self._read_spec(item.get("elements", []))
            if spec is None:
                continue
            path = _canonical_path(spec[0])
            for _, _, lines in self._known.get(path, ()):
                visible_by_path.setdefault(path, []).append(self._selected_text(lines, spec))
        for item in commands:
            name = _command_name(item.get("name"))
            elements = item.get("elements", [])
            if not isinstance(elements, list):
                unknown += 1
                continue
            if name in _READ_NAMES:
                if item.get("redirected"):
                    unknown += 1
                    continue
                spec = self._read_spec(elements)
                literal_path = spec[0] if spec else None
                path = _canonical_path(literal_path) if literal_path else None
                entries = self._known.get(path, ()) if path else ()
                if not entries:
                    # Ordinary source/document reads are not skill candidates.
                    # Relative, wildcard, and provider paths to SKILL.md still
                    # cannot be attributed safely, and must remain unknown.
                    if literal_path and ntpath.basename(literal_path).lower() != "skill.md" and not any(
                        character in literal_path for character in "*?[]"
                    ):
                        continue
                    unknown += 1
                    continue
                matched = []
                for label, anchors, lines in entries:
                    visible = self._selected_text(lines, spec)
                    if any(anchor in visible and anchor in output and not any(
                        anchor in other_visible
                        for other_path, texts in visible_by_path.items() if other_path != path
                        for other_visible in texts
                    ) for anchor in anchors):
                        matched.append(label)
                if matched:
                    names.update(matched)
                else:
                    unknown += 1
            elif name in _SHELL_NAMES:
                nested_text = self._wrapper_text(elements)
                if nested_text is None or item.get("redirected") or uncertain_context:
                    unknown += 1
                    continue
                nested_result = self._collect_parsed(nested_text, output, depth + 1)
                names.update(nested_result["confirmed_reads"])
                unknown += nested_result["unknown_reads_count"]
            elif name in {"cmd", "cmd.exe"} or not name:
                # Unknown dynamic invocations and cmd wrappers might perform a
                # read, but their text/output never proves a known-file read.
                unknown += 1
            elif ntpath.basename(name) in _READ_NAMES:
                unknown += 1
        return _labels(names, unknown)

    def collect(self, command: str, aggregated_output: str, exit_code: int) -> EvidenceLabels:
        """Classify one completed ``command_execution`` event.

        A nonzero exit cannot confirm any read; identifiable or unresolved skill
        attempts remain unknown. A zero exit additionally needs supported syntax
        and meaningful body evidence.
        """
        if not isinstance(command, str) or not isinstance(aggregated_output, str) or type(exit_code) is not int:
            return _labels(unknown=1)
        # Pinned codex-secrets sanitization happens after display formatting.
        # Do not infer the missing argv/script text or classify it as clean.
        if "\x00" in command or "[redacted_secret]" in command.lower():
            return _labels(unknown=1)
        if len(command) > _MAX_COMMAND_CHARS or len(aggregated_output) > _MAX_OUTPUT_CHARS:
            return _labels(unknown=1)
        if exit_code != 0:
            return self._collect_parsed(command, "", 0)
        return self._collect_parsed(command, _normalize_text(aggregated_output), 0)

    def collect_event(self, event: Mapping) -> EvidenceLabels:
        if not isinstance(event, Mapping):
            return _labels(unknown=1)
        return self.collect(event.get("command"), event.get("aggregated_output"), event.get("exit_code"))

    def summarize(self, events: Iterable[Mapping]) -> EvidenceLabels:
        names: set[str] = set()
        unknown = 0
        for event in events:
            result = self.collect_event(event)
            names.update(result["confirmed_reads"])
            unknown += result["unknown_reads_count"]
        return _labels(names, unknown)
