"""Local, dependency-free Codex metadata audit and explicit-file recovery.

Python 3.11+. No network calls or external commands. Audit never emits config
values, URLs, environment values, descriptions, or raw exception messages.
Snapshot copies explicitly named files, which may themselves contain secrets;
protect the backup directory. Filename filtering is not content classification.

Rollback validates all hashes before writing. It is not a multi-file transaction
and cannot defend against hostile concurrent filesystem changes: stop other
writers first. Individual restored files use same-directory atomic replacement.
The small frontmatter parser supports plain/quoted scalars and |/> descriptions,
not the complete YAML specification. Markdown references cover inline links.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import tomllib
from typing import Any


MAX_BYTES = 16 * 1024 * 1024
MAX_FILES = 4096
HASH = re.compile(r"[0-9a-f]{64}\Z")
DEVICES = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z", re.I)
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")


class AuditError(Exception):
    """A stable error code; never include underlying exception text."""


def _linked(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _unlinked(path: Path) -> None:
    for part in [*reversed(path.parents), path]:
        if _linked(part):
            raise AuditError("symlink_or_reparse_point")


def _root(path: Path) -> Path:
    result = Path(os.path.abspath(path))
    if any(_sensitive(part) for part in result.parts):
        raise AuditError("sensitive_path")
    _unlinked(result)
    if not result.is_dir():
        raise AuditError("root_not_directory")
    return result


def _sensitive(part: str) -> bool:
    name = part.casefold()
    return (
        name.startswith(".env")
        or any(term in name for term in ("auth", "secret", "credential", "session", "database"))
        or name in {"history", "history.jsonl", "logs", "log", "tokens", "token.json"}
        or bool(re.search(r"\.(?:db|sqlite|sqlite3)(?:[-.].*)?$", name))
    )


def _public_name(value: str) -> str:
    """Do not echo arbitrary TOML keys or YAML values as metadata labels."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", value) or re.search(
        r"secret|password|api[_-]?key|access[_-]?token|bearer|^sk-|^gh[pousr]_|^AKIA|^eyJ[A-Za-z0-9_]{15,}",
        value, re.I,
    ):
        return "[redacted]"
    return value


def _public_path(path: Path) -> str:
    parts = path.parts[1:] if path.anchor else path.parts
    safe_parts = [_public_name(part) for part in parts]
    return str(Path(path.anchor, *safe_parts))


def _relative(value: str, *, allow_sensitive_names: bool = False) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise AuditError("unsafe_relative_path")
    pieces = value.split("/")
    if PurePosixPath(value).is_absolute() or any(
        not part or part in {".", ".."} or part[-1:] in {".", " "}
        or any(ord(char) < 32 or char in '<>"|?*' for char in part)
        or DEVICES.fullmatch(part) for part in pieces
    ):
        raise AuditError("unsafe_relative_path")
    if not allow_sensitive_names and any(_sensitive(part) for part in pieces):
        raise AuditError("sensitive_path")
    return value


def _paths(values: list[str]) -> list[str]:
    if not values or len(values) > MAX_FILES:
        raise AuditError("invalid_file_count")
    result = [_relative(value) for value in values]
    if len({value.casefold() for value in result}) != len(result):
        raise AuditError("duplicate_path")
    return result


def _target(root: Path, relative: str) -> Path:
    target = root.joinpath(*relative.split("/"))
    _unlinked(target)
    if target.exists() and not target.is_file():
        raise AuditError("not_regular_file")
    # A non-directory ancestor must fail before snapshot creates a backup.
    for parent in target.parents:
        if parent == root:
            break
        if parent.exists() and not parent.is_dir():
            raise AuditError("parent_not_directory")
    return target


def _read(path: Path) -> bytes:
    _unlinked(path)
    if not path.is_file():
        raise AuditError("not_regular_file")
    if path.stat().st_nlink > 1:
        raise AuditError("hardlink_not_allowed")
    with path.open("rb") as source:
        data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise AuditError("file_too_large")
    return data


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _current(path: Path) -> str | None:
    return _digest(_read(path)) if path.exists() else None


def _json_load(path: Path) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AuditError("duplicate_json_key")
            result[key] = value
        return result
    try:
        return json.loads(_read(path), object_pairs_hook=unique)
    except (UnicodeError, ValueError):
        raise AuditError("invalid_json") from None


def _hash_map(value: Any) -> dict[str, str | None]:
    if not isinstance(value, dict):
        raise AuditError("invalid_hash_manifest")
    _paths(list(value))
    if any(item is not None and (not isinstance(item, str) or not HASH.fullmatch(item)) for item in value.values()):
        raise AuditError("invalid_hash_manifest")
    return value


def _backup_location(path: Path, root: Path) -> Path:
    backup = Path(os.path.abspath(path))
    if any(_sensitive(part) for part in backup.parts):
        raise AuditError("sensitive_path")
    _unlinked(backup)
    if backup == root or backup.is_relative_to(root) or root.is_relative_to(backup):
        raise AuditError("backup_overlaps_root")
    return backup


def _write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as output:
        os.chmod(path, 0o600)
        output.write(data)


def snapshot(root: Path, backup_dir: Path, paths: list[str]) -> dict[str, Any]:
    root = _root(root)
    relatives = _paths(paths)
    backup = _backup_location(backup_dir, root)
    if backup.exists() and (not backup.is_dir() or any(backup.iterdir())):
        raise AuditError("backup_not_empty")
    contents: dict[str, bytes | None] = {}
    modes: dict[str, int] = {}
    for relative in relatives:
        source = _target(root, relative)
        contents[relative] = _read(source) if source.exists() else None
        if source.exists():
            modes[relative] = stat.S_IMODE(source.stat().st_mode)
    manifest = {"version": 1, "files": {key: _digest(data) if data is not None else None for key, data in contents.items()}, "modes": modes}
    backup.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(backup, 0o700)
    for relative, data in contents.items():
        if data is not None:
            target = _target(backup / "files", relative)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            _write_new(target, data)
    # A manifest appears only after every original byte has been copied.
    _write_new(backup / "manifest.json", (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    return manifest


def rollback(backup_dir: Path, root: Path, expected_current: dict[str, str | None]) -> dict[str, Any]:
    root = _root(root)
    backup = _backup_location(backup_dir, root)
    if not backup.is_dir():
        raise AuditError("backup_not_directory")
    manifest = _json_load(backup / "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("version") != 1 or set(manifest) != {"version", "files", "modes"}:
        raise AuditError("invalid_backup_manifest")
    originals = _hash_map(manifest["files"])
    expected = _hash_map(expected_current)
    if set(originals) != set(expected):
        raise AuditError("expected_paths_mismatch")
    modes = manifest["modes"]
    if not isinstance(modes, dict) or set(modes) != {key for key, value in originals.items() if value is not None} or any(type(value) is not int or not 0 <= value <= 0o777 for value in modes.values()):
        raise AuditError("invalid_backup_modes")
    contents: dict[str, bytes | None] = {}
    targets: dict[str, Path] = {}
    # Preflight EVERY target and backup before any directory or file mutation.
    for relative, original_hash in originals.items():
        target = _target(root, relative)
        targets[relative] = target
        if _current(target) != expected[relative]:
            raise AuditError("current_file_drift")
        if original_hash is None:
            contents[relative] = None
        else:
            data = _read(_target(backup / "files", relative))
            if _digest(data) != original_hash:
                raise AuditError("backup_hash_mismatch")
            contents[relative] = data
    staged: dict[str, Path] = {}
    try:
        for relative, data in contents.items():
            if data is not None:
                target = targets[relative]
                target.parent.mkdir(parents=True, exist_ok=True)
                descriptor, name = tempfile.mkstemp(prefix=".env-audit-", suffix=".tmp", dir=target.parent)
                staged[relative] = Path(name)
                with os.fdopen(descriptor, "wb") as output:
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(name, modes[relative])
        # Recheck all targets after staging, still before any replacement/deletion.
        for relative, target in targets.items():
            _unlinked(target)
            if _current(target) != expected[relative]:
                raise AuditError("current_file_drift")
        for relative, data in contents.items():
            if data is None:
                if expected[relative] is not None:
                    targets[relative].unlink()
            else:
                os.replace(staged[relative], targets[relative])
        return {"restored": list(originals), "backup_preserved": True}
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def _frontmatter(text: str) -> tuple[dict[str, str], bool]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, False
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        return {}, False
    result: dict[str, str] = {}
    field: str | None = None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() and field:
            result[field] += "\n" + line.strip()
            continue
        match = re.fullmatch(r"([A-Za-z_][\w-]*):\s*(.*)", line)
        if not match or match[1] in result:
            return {}, False
        key, value = match.groups()
        if value[:1] in {"'", '"'}:
            if len(value) < 2 or value[-1] != value[0]:
                return {}, False
            value = value[1:-1]
        result[key] = "" if value in {"|", ">", "|-", ">-"} else value
        field = key
    return result, bool(result.get("name") and result.get("description", "").strip())


def _walk_skills(root: Path, issues: list[dict[str, Any]]) -> list[Path]:
    root = Path(os.path.abspath(root))
    if any(_sensitive(part) for part in root.parts):
        issues.append({"code": "sensitive_root_skipped"})
        return []
    try:
        _unlinked(root)
    except AuditError:
        issues.append({"code": "symlink_skipped", "path": _public_path(root)})
        return []
    if not root.is_dir():
        return []
    result: list[Path] = []
    stack = [root]
    visited = 0
    while stack:
        directory = stack.pop()
        for entry in sorted(directory.iterdir(), key=lambda value: value.name.casefold()):
            visited += 1
            if visited > 100000:
                raise AuditError("skill_scan_limit")
            if _linked(entry):
                issues.append({"code": "symlink_skipped", "path": _public_path(entry)})
            elif _sensitive(entry.name):
                continue
            elif entry.is_dir():
                stack.append(entry)
            elif entry.name == "SKILL.md" and entry.is_file():
                result.append(entry)
    return result


def audit(codex_home: Path, agent_skills: Path) -> dict[str, Any]:
    home = _root(codex_home)
    issues: list[dict[str, Any]] = []
    config_report: dict[str, Any] = {"exists": False, "valid": False, "top_level_keys": [], "mcp_servers": []}
    roles: list[dict[str, Any]] = []
    config_file = _target(home, "config.toml")
    if config_file.exists():
        config_report["exists"] = True
        try:
            config = tomllib.loads(_read(config_file).decode("utf-8"))
            config_report["valid"] = True
            config_report["top_level_keys"] = sorted(_public_name(key) for key in config)
            servers = config.get("mcp_servers", {})
            if isinstance(servers, dict):
                for name, server in sorted(servers.items()):
                    if not isinstance(server, dict):
                        continue
                    args = server.get("args", [])
                    strings = [server.get("command", "")] + (args if isinstance(args, list) else [])
                    transport = "http" if isinstance(server.get("url"), str) else "stdio" if isinstance(server.get("command"), str) else "unknown"
                    config_report["mcp_servers"].append({"name": _public_name(name), "enabled": server.get("enabled", True) if isinstance(server.get("enabled", True), bool) else None, "transport": transport, "floating_latest": any(isinstance(value, str) and "@latest" in value for value in strings)})
            agents = config.get("agents", {})
            if isinstance(agents, dict):
                for name, role in sorted(agents.items()):
                    if isinstance(role, dict) and "config_file" in role:
                        exists = False
                        status = "unsafe_path"
                        try:
                            value = role["config_file"]
                            if not isinstance(value, str):
                                raise AuditError("unsafe_role_path")
                            configured = Path(value)
                            if configured.is_absolute():
                                normalized = Path(os.path.abspath(configured))
                                if not normalized.is_relative_to(home):
                                    status = "outside_scope"
                                    raise AuditError("outside_role_scope")
                                relative = _relative(normalized.relative_to(home).as_posix())
                            else:
                                relative = _relative(value)
                            exists = _target(home, relative).is_file()
                            status = "present" if exists else "missing"
                        except (AuditError, TypeError):
                            pass
                        roles.append({"name": _public_name(name), "config_file_exists": exists, "status": status})
        except (tomllib.TOMLDecodeError, UnicodeError, AuditError):
            issues.append({"code": "invalid_config"})
    skills: list[dict[str, Any]] = []
    skill_names: list[str] = []
    seen_paths: set[Path] = set()
    for root in [home / "skills", agent_skills]:
        for path in _walk_skills(root, issues):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            try:
                raw = _read(path)
                content = raw.decode("utf-8-sig")
            except (UnicodeError, AuditError):
                issues.append({"code": "unreadable_skill", "path": _public_path(path)})
                continue
            metadata, valid = _frontmatter(content)
            if metadata.get("name"):
                skill_names.append(metadata["name"])
            skills.append({"name": _public_name(metadata["name"]) if metadata.get("name") else None, "path": _public_path(path), "bytes": len(raw), "description_length": len(metadata.get("description", ""))})
            if not valid:
                issues.append({"code": "bad_frontmatter", "path": _public_path(path)})
            fence: tuple[str, int] | None = None
            for number, line in enumerate(content.splitlines(), start=1):
                marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
                if marker:
                    token = marker[1]
                    if fence is None:
                        fence = (token[0], len(token))
                    elif token[0] == fence[0] and len(token) >= fence[1] and not line[marker.end():].strip():
                        fence = None
                    continue
                if fence is not None:
                    continue
                line = re.sub(r"(`+).*?\1", "", line)
                for match in LINK.finditer(line):
                    value = match[1].strip()
                    if value.startswith("<") and ">" in value:
                        value = value[1:value.index(">")]
                    else:
                        value = value.split(' "', 1)[0].split(" '", 1)[0]
                    if not value or value.startswith("#") or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", value) or value.startswith("//"):
                        continue
                    value = value.split("#", 1)[0]
                    try:
                        # Existence-only checks do not read or back up document contents.
                        reference = _target(path.parent, _relative(value, allow_sensitive_names=True))
                        if not reference.is_file():
                            issues.append({"code": "missing_reference", "severity": "warning", "path": _public_path(path), "line": number})
                    except AuditError:
                        issues.append({"code": "unsafe_reference", "severity": "warning", "path": _public_path(path), "line": number})
    duplicates = sorted(_public_name(name) for name, count in Counter(skill_names).items() if count > 1)
    return {"config": config_report, "roles": roles, "skills": sorted(skills, key=lambda item: item["path"]), "duplicate_skill_names": duplicates, "issues": issues}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    audit_parser = commands.add_parser("audit")
    audit_parser.add_argument("--codex-home", type=Path, required=True)
    audit_parser.add_argument("--agent-skills", type=Path, required=True)
    snapshot_parser = commands.add_parser("snapshot")
    snapshot_parser.add_argument("--root", type=Path, required=True)
    snapshot_parser.add_argument("--backup-dir", type=Path, required=True)
    snapshot_parser.add_argument("--paths", nargs="+", required=True)
    rollback_parser = commands.add_parser("rollback")
    rollback_parser.add_argument("--root", type=Path, required=True)
    rollback_parser.add_argument("--backup-dir", type=Path, required=True)
    rollback_parser.add_argument("--expected-current", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "audit":
            result = audit(args.codex_home, args.agent_skills)
        elif args.command == "snapshot":
            result = snapshot(args.root, args.backup_dir, args.paths)
        else:
            if any(_sensitive(part) for part in args.expected_current.parts):
                raise AuditError("sensitive_path")
            result = rollback(args.backup_dir, args.root, _json_load(args.expected_current))
    except AuditError as error:
        print(json.dumps({"error": str(error)}))
        return 2
    except (OSError, ValueError, TypeError):
        print(json.dumps({"error": "filesystem_or_input_error"}))
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
