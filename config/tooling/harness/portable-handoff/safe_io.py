"""Frozen stdlib path/read helpers from the local task ledger.
Source alias: CODEX_HOME/harness/task_ledger.py
Source SHA256: 002fa5e80bd18ca0c28768ef6e0f00a71d194e0dbf8c9712dfe6de400d688984
Copied 2026-11-06 to keep the candidate portable; no global import or modification.
"""
import os
from pathlib import Path
import stat
class LedgerError(Exception):
    """Expected input, evidence or state validation failure."""


def require(condition, message):
    if not condition:
        raise LedgerError(message)


def text_field(value, label, *, empty=False):
    require(isinstance(value, str) and len(value) <= 4096, f"Invalid {label}")
    require(empty or bool(value.strip()), f"Empty {label}")
    require("\x00" not in value, f"NUL in {label}")
    return value


def secure_path(value, *, kind=None, must_exist=True):
    """Check every existing component, including Windows junctions/reparse points."""
    require(isinstance(value, (str, Path)), "Path must be text")
    raw = str(value)
    require(len(raw) <= 4096 and "\x00" not in raw, "Invalid path")
    path = Path(raw)
    require(path.is_absolute(), "Paths must be absolute")
    require(".." not in path.parts, "Parent traversal is not allowed")
    if os.name == "nt":
        require(not raw.startswith(("\\\\", "//")), "Network/device paths are not allowed")
        require(all(":" not in part for part in path.parts[1:]), "Alternate streams are not allowed")
    path = Path(os.path.abspath(path))
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode), f"Symbolic links are not allowed: {part}")
        require(not (getattr(info, "st_file_attributes", 0) & 0x400),
                f"Reparse points are not allowed: {part}")
        if stat.S_ISREG(info.st_mode):
            require(info.st_nlink == 1, f"Hard-linked files are not allowed: {part}")
    if must_exist:
        require(path.exists(), f"Path does not exist: {path}")
    if path.exists() and kind == "dir":
        require(path.is_dir(), f"Directory required: {path}")
    if path.exists() and kind == "file":
        require(stat.S_ISREG(path.stat().st_mode), f"Regular file required: {path}")
    return path


def within(path, root):
    return path == root or root in path.parents


def regular_read(path, limit):
    path = secure_path(path, kind="file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "Unsafe file")
        require(before.st_size <= limit, f"File exceeds size limit: {path}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        after = os.fstat(fd)
        require(len(data) <= limit, "File grew beyond size limit")
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "File changed while reading")
        secure_path(path, kind="file")
        final = path.stat()
        require((final.st_dev, final.st_ino) == (after.st_dev, after.st_ino), "File was replaced while reading")
        return data
    finally:
        os.close(fd)
