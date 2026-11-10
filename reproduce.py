"""Stage the curated portable Codex environment. Python 3.11+."""

from __future__ import annotations

import sys

if __name__ == "__main__":
    sys.dont_write_bytecode = True

import argparse
import ctypes
from dataclasses import dataclass
import errno
import hashlib
import json
import ntpath
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import tempfile
import unicodedata


PACKAGE = Path(__file__).resolve().parent / "environment"
ROOTS = ("codex-home", "project", "tooling")
PRIVATE_NAMES = {
    ".git", ".ssh", ".aws", ".gnupg", ".netrc", ".npmrc", "auth.json",
    "credentials", "history", "history.jsonl", "logs", "memories", "memories_v2",
    "oauth", "session_index.jsonl", "sessions", "archived_sessions", "shell_snapshots",
}
PATH_TOKEN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
PINNED_CODEX_SHA256 = "8cb0e69e99ff2a158c54815db82d0f2e524d8f301bc30184722cfd1ae5973574"
PINNED_NODE_SHA256 = "1c331340fa6cac5e4294725959070a143fa0507195a78ad77eed7943f719aac9"

LAUNCHER = r'''#!/usr/bin/env python3
"""Run Codex with this installation's Codex home."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess


def pinned_executable(root, group_path, executable_path, expected_digest, label):
    install = root / group_path
    if not os.path.lexists(install):
        return None
    binary = install / executable_path
    directory = root
    for name in binary.parent.relative_to(root).parts:
        directory = directory / name
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError(f"{label} has a redirected or invalid directory.")
    receipt = install / ".dependency-receipt.json"
    for path in (binary, receipt):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError(f"{label} executable or receipt is linked or invalid.")
    record = json.loads(receipt.read_bytes())
    files = record.get("files") if isinstance(record, dict) else None
    with binary.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if not isinstance(files, dict) or files.get(executable_path) != digest or digest != expected_digest:
        raise ValueError(f"{label} does not match its release checksum and dependency receipt.")
    return binary


def find_codex(root, explicit):
    if explicit:
        return shutil.which(explicit)
    if os.name == "nt":
        return pinned_executable(
            root, "codex-home/tools/codex-cli/0.157.1", "bin/codex.exe",
            "__PINNED_CODEX_SHA256__", "Pinned Codex CLI",
        ) or shutil.which("codex.exe")
    return shutil.which("codex")


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--project", type=Path, help="existing project (default: bundled project)")
parser.add_argument("--codex", help="Codex binary path or command name")
parser.add_argument("--allow-env-auth", action="store_true",
                    help="retain reader-supplied API-key environment variables")
parser.add_argument("--inherit-node-path", action="store_true",
                    help="use the caller's PATH without preferring the installed Node runtime")
parser.add_argument("args", nargs=argparse.REMAINDER, help="Codex arguments after --")
options = parser.parse_args()
root = Path(__file__).resolve().parent
project = (options.project or root / "project").resolve()
if not project.is_dir():
    parser.error("project must be an existing directory")
try:
    binary = find_codex(root, options.codex)
except (OSError, ValueError) as error:
    parser.error(f"Could not verify pinned Codex CLI. {error}")
if not binary or (os.name == "nt" and Path(binary).suffix.lower() != ".exe"):
    parser.error("Codex native binary not found. Pass --codex with its executable path.")
binary = str(Path(binary).resolve())
env = os.environ.copy()
env["CODEX_HOME"] = str(root / "codex-home")
if os.name == "nt" and not options.inherit_node_path:
    try:
        node = pinned_executable(
            root, "codex-home/tools/agent-kit/runtime/node-v24.22.2-win-x64", "node.exe",
            "__PINNED_NODE_SHA256__", "Pinned Node",
        )
    except (OSError, ValueError) as error:
        parser.error(f"Could not verify pinned Node. {error}")
    if node:
        inherited_path = env.get("PATH")
        env["PATH"] = os.pathsep.join(part for part in (str(node.parent), inherited_path) if part)
if not options.allow_env_auth:
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "CHATGPT_API_KEY", "CODEX_ACCESS_TOKEN"):
        env.pop(key, None)
args = options.args[1:] if options.args[:1] == ["--"] else options.args
raise SystemExit(subprocess.call(
    [binary, "--no-daemon", "-c", 'cli_auth_credentials_store="file"', *args],
    cwd=project, env=env,
))
'''.replace("__PINNED_CODEX_SHA256__", PINNED_CODEX_SHA256).replace(
    "__PINNED_NODE_SHA256__", PINNED_NODE_SHA256
).encode("utf-8")


class ReproduceError(ValueError):
    """An unsafe or invalid install request."""


@dataclass(frozen=True)
class Payload:
    target: tuple[str, ...]
    data: bytes
    executable: bool = False


def reserved_windows_name(part: str) -> bool:
    if hasattr(ntpath, "isreserved"):
        return ntpath.isreserved(part)
    return PureWindowsPath(part).is_reserved()


def safe_parts(value: str, *, exclude_private: bool = True) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise ReproduceError("manifest paths must be strings")
    parts = tuple(value.split("/"))
    for part in parts:
        if (
            not part or part in {".", ".."} or part.endswith((".", " "))
            or re.search(r'[<>:"\\|?*\x00-\x1f\x7f]', part)
            or reserved_windows_name(part)
        ):
            raise ReproduceError(f"nonportable manifest path: {value!r}")
        name = part.casefold()
        if exclude_private and (
            name in PRIVATE_NAMES or name == ".env"
            or (name.startswith(".env.") and name not in {".env.example", ".env.sample"})
            or name.endswith((".pem", ".pfx", ".p12", ".sqlite", ".sqlite3"))
        ):
            raise ReproduceError(f"private-state path excluded: {value!r}")
    return parts


def is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def directory(path: Path) -> None:
    for item in (*reversed(path.parents), path):
        info = item.lstat()
        if is_link(info) or not stat.S_ISDIR(info.st_mode):
            raise ReproduceError(f"expected a real directory: {item}")


def read_regular(path: Path) -> bytes:
    directory(path.parent)
    info = path.lstat()
    if is_link(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ReproduceError(f"expected an unlinked regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not os.path.samestat(info, opened) or opened.st_nlink != 1:
            raise ReproduceError(f"file changed during validation: {path}")
        return stream.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReproduceError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def render_paths(data: bytes, destination: Path) -> bytes:
    # This common safe subset works inside both TOML and PowerShell quoted paths.
    root = destination.as_posix()
    text = data.decode("utf-8")
    if not PATH_TOKEN.search(text):
        raise ReproduceError("path template contains no path tokens")
    drive = len(root) >= 3 and root[0].isalpha() and root[1:3] == ":/"
    for char in root[2 if drive else 0:]:
        if not (char.isalnum() or char in "/._- ()" or unicodedata.category(char).startswith("M")):
            raise ReproduceError("choose a destination with portable path characters for rendering")
    values = {
        "ENV_ROOT": root,
        "CODEX_HOME": f"{root}/codex-home",
        "TOOLS_ROOT": f"{root}/codex-home/tools",
    }

    def replace(match: re.Match) -> str:
        token = match.group(1)
        if token not in values:
            raise ReproduceError(f"unknown template token: {token}")
        return values[token]

    return PATH_TOKEN.sub(replace, text).encode("utf-8")


def manifest_payload(package: Path, destination: Path) -> tuple[str, list[Payload]]:
    manifest = read_regular(package / "manifest.json")
    document = json.loads(manifest, object_pairs_hook=json_object)
    if (
        not isinstance(document, dict) or document.keys() != {"schema_version", "files"}
        or type(document["schema_version"]) is not int or document["schema_version"] != 1
        or not isinstance(document["files"], list) or not document["files"]
    ):
        raise ReproduceError("expected a non-empty schema version 1 manifest")

    entries = []
    targets: dict[str, tuple[tuple[str, ...], bool]] = {}
    required = {"source", "target", "sha256", "executable"}
    for row in document["files"]:
        if not isinstance(row, dict) or not required <= row.keys() <= required | {"render"}:
            raise ReproduceError("invalid file entry fields")
        source = safe_parts(row["source"])
        target = safe_parts(row["target"])
        digest = row["sha256"]
        executable = row["executable"]
        if len(source) < 2 or source[0] != "bundle" or len(target) < 2 or target[0] not in ROOTS:
            raise ReproduceError("source or target is outside its approved root")
        if (
            not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)
            or not isinstance(executable, bool)
            or ("render" in row and row["render"] != "paths")
        ):
            raise ReproduceError("invalid sha256, executable, or render field")
        for depth in range(1, len(target) + 1):
            prefix = target[:depth]
            key = unicodedata.normalize("NFC", "/".join(prefix)).casefold()
            is_file = depth == len(target)
            if key in targets and (is_file or targets[key] != (prefix, False)):
                raise ReproduceError(f"duplicate or conflicting target: {row['target']!r}")
            targets[key] = prefix, is_file
        entries.append((source, target, digest, executable, row.get("render")))

    payload = [Payload(("launch.py",), LAUNCHER)]
    for source, target, digest, executable, render in entries:
        data = read_regular(package.joinpath(*source))
        if sha256(data) != digest:
            raise ReproduceError(f"source checksum mismatch: {'/'.join(source)}")
        if render == "paths":
            data = render_paths(data, destination)
        payload.append(Payload(target, data, executable))
    return sha256(manifest), payload


def receipt(manifest_hash: str, payload: list[Payload]) -> bytes:
    data = {
        "schema_version": 1,
        "manifest_sha256": manifest_hash,
        "files": [
            {"target": "/".join(item.target), "sha256": sha256(item.data), "executable": item.executable}
            for item in payload
        ],
    }
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def rename_new(stage: Path, destination: Path) -> None:
    """Publish a complete tree atomically, refusing even an existing empty directory."""
    if os.name == "nt":
        # On Windows os.rename does not replace an existing destination.
        stage.rename(destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        rename = libc.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        result = rename(-100, os.fsencode(stage), -100, os.fsencode(destination), 1)
    elif sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        rename = libc.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        result = rename(os.fsencode(stage), os.fsencode(destination), 4)
    else:
        raise ReproduceError("atomic no-replace directory rename unavailable on this platform")
    if result:
        error = ctypes.get_errno() or errno.EIO
        raise OSError(error, os.strerror(error), destination)


def destination_path(destination: Path, package: Path = PACKAGE) -> Path:
    destination = Path(os.path.abspath(destination))
    package_root = package.resolve().parent
    source = next(
        (path for path in (package_root, *package_root.parents) if os.path.lexists(path / ".git")),
        package_root,
    )
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ReproduceError("Choose an installation directory outside the source checkout.")
    if destination.drive.startswith("\\\\"):
        raise ReproduceError("choose a local destination directory")
    active_homes = [Path.home() / ".codex", Path.home() / ".agents"]
    if os.environ.get("CODEX_HOME"):
        active_homes.append(Path(os.path.abspath(os.environ["CODEX_HOME"])))
    if any(destination.is_relative_to(home) for home in active_homes):
        raise ReproduceError("destination must be outside active Codex home directories")
    return destination


def operate(destination: Path, mode: str = "plan", package: Path = PACKAGE) -> list[Payload]:
    destination = destination_path(destination, package)
    directory(destination.parent)
    if mode == "verify":
        directory(destination)
    elif os.path.lexists(destination):
        raise ReproduceError(f"destination already exists: {destination}")

    manifest_hash, payload = manifest_payload(package, destination)
    payload.append(Payload(("reproduction-receipt.json",), receipt(manifest_hash, payload)))
    if mode == "verify":
        installed_receipt = destination / "reproduction-receipt.json"
        try:
            actual_receipt = read_regular(installed_receipt)
        except FileNotFoundError as error:
            raise ReproduceError("Existing destination has no configuration installation receipt.") from error
        if actual_receipt != payload[-1].data:
            raise ReproduceError("Existing configuration receipt differs from this source package.")
        for root in ROOTS:
            directory(destination / root)
        for item in payload[:-1]:
            path = destination.joinpath(*item.target)
            if read_regular(path) != item.data:
                raise ReproduceError(f"installed file differs: {'/'.join(item.target)}")
            if os.name != "nt" and bool(path.stat().st_mode & stat.S_IXUSR) != item.executable:
                raise ReproduceError(f"installed file mode differs: {'/'.join(item.target)}")
    elif mode == "apply":
        with tempfile.TemporaryDirectory(prefix=".codex-stage-", dir=destination.parent) as name:
            stage = Path(name)
            for root in ROOTS:
                (stage / root).mkdir()
            for item in payload:
                path = stage.joinpath(*item.target)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as stream:
                    stream.write(item.data)
                if os.name != "nt":
                    path.chmod(0o700 if item.executable else 0o600)
            directory(destination.parent)
            rename_new(stage, destination)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="new directory under an existing local parent")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="stage and publish the new directory")
    group.add_argument("--verify", action="store_true", help="check installed managed files offline")
    args = parser.parse_args()
    mode = "apply" if args.apply else "verify" if args.verify else "plan"
    try:
        payload = operate(args.destination, mode)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")
    print(f"{mode}: {len(payload)} managed files at {args.destination.absolute()}")
    if mode == "plan":
        for item in payload:
            print("/".join(item.target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
